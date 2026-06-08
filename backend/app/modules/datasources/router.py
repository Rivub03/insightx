# app/modules/datasources/router.py
#
# PURPOSE:
#   FastAPI APIRouter — combines what was separate controller + routes files
#   in the Node.js version. In FastAPI, the route handler IS the controller.
#
# FILE UPLOAD HANDLING:
#   FastAPI's UploadFile + python-multipart replaces multer entirely.
#   No separate middleware file is needed.
#
# AUTHENTICATION DEPENDENCY:
#   get_current_user is a placeholder that returns a dict with
#   `tenant_id` and `id`. Replace with your real auth implementation
#   in M10 (Authentication & Authorization). The placeholder raises HTTP 401
#   if the X-User-Id and X-Tenant-Id headers are missing.
#
# NOTE ON /test RESPONSE CODE:
#   The /test endpoint always returns HTTP 200 — even when the DB connection fails.
#   A failed DB connection is NOT an HTTP error; it is a valid, expected result.
#   HTTP 5xx would confuse error-handling middleware and make the frontend's job harder.

import os
import time
from pathlib import Path
from typing import Annotated

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.modules.datasources import service
from app.modules.datasources.schemas import (
    DatasourceListResponse,
    DatasourcePayload,
    DatasourceResponse,
    FileUploadResponse,
    TestConnectionResponse,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# Allowed file extensions for secure uploads
# ---------------------------------------------------------------------------

_ALLOWED_EXTENSIONS = {
    ".pem", ".crt", ".cer", ".key",  # TLS certificates and private keys
    ".p12", ".sso",                  # Oracle Wallet formats
    ".keytab", ".kt",                # Kerberos keytab files
}

_ALLOWED_UPLOAD_TYPES = {
    "ca_cert", "client_cert", "client_key", "wallet", "keytab"
}

# Ensure the secure upload directory exists when the router module is loaded
_upload_dir = Path(settings.secure_files_dir)
_upload_dir.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Auth dependency (placeholder — replace in M10)
# ---------------------------------------------------------------------------

async def get_current_user(
    # These headers are placeholders. Replace with real JWT/session extraction.
    # In M10, this dependency will decode a JWT and return the user principal.
) -> dict:
    """
    Placeholder auth dependency.
    Returns a mock user dict for development. Replace with real auth in M10.

    In a real implementation, this would:
      1. Extract the JWT from the Authorization header
      2. Validate and decode it
      3. Return the user's id and tenant_id
    """
    # TODO: Replace with real auth in M10
    # Returning a hardcoded dev user until M10 is implemented
    return {
        "id":        "dev-user-001",
        "tenant_id": "dev-tenant-001",
    }


# Type alias for the injected user dict — cleaner route signatures
CurrentUser = Annotated[dict, Depends(get_current_user)]
DB          = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/test",
    response_model=TestConnectionResponse,
    summary="Test a database connection without saving",
    description=(
        "Validates connection parameters by attempting a live connection. "
        "Non-destructive — only SELECT 1 is executed. "
        "Always returns HTTP 200; success/failure is encoded in the response body."
    ),
)
async def test_connection(
    payload:      DatasourcePayload,
    current_user: CurrentUser,
) -> TestConnectionResponse:
    """
    Tests a datasource connection WITHOUT persisting anything.

    This is the endpoint called by the frontend's "Test Connection" button.
    Pydantic validates the request body automatically — if validation fails,
    FastAPI returns HTTP 422 with per-field error details before this function
    is even called.
    """
    # No db session needed — this is entirely non-destructive
    result = await service.test_datasource_connection(payload)

    # Always HTTP 200 — the result dict has success/failure info in the body
    return TestConnectionResponse(**result)


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    summary="Upload a TLS cert, Oracle Wallet, or Kerberos keytab",
    description=(
        "Stores the file on the server filesystem outside the webroot. "
        "Returns the server-side path to embed in the datasource payload. "
        "Accepted types: ca_cert, client_cert, client_key, wallet, keytab."
    ),
)
async def upload_secure_file(
    current_user: CurrentUser,
    file: UploadFile = File(..., description="The file to upload"),
    type: str        = Form(..., description="One of: ca_cert | client_cert | client_key | wallet | keytab"),
) -> FileUploadResponse:
    """
    Handles secure file uploads for TLS certs, Oracle Wallets, and Kerberos keytabs.
    Files are stored outside the webroot to prevent direct HTTP access.
    """
    # Validate upload type
    if type not in _ALLOWED_UPLOAD_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid upload type '{type}'. Must be one of: {sorted(_ALLOWED_UPLOAD_TYPES)}",
        )

    # Validate file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is missing")

    ext = Path(file.filename).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{ext}' is not permitted. Allowed: {sorted(_ALLOWED_EXTENSIONS)}",
        )

    # Check file size BEFORE writing to disk
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    contents  = await file.read()
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.max_upload_size_mb} MB",
        )

    # Generate a non-predictable filename:
    # format: tenantId-timestamp-randomHex.ext
    import secrets
    tenant_id    = current_user["tenant_id"]
    random_hex   = secrets.token_hex(4)
    ts           = int(time.time() * 1000)
    safe_filename = f"{tenant_id}-{ts}-{random_hex}{ext}"
    dest_path    = _upload_dir / safe_filename

    # Write the file asynchronously
    async with aiofiles.open(dest_path, "wb") as out:
        await out.write(contents)

    return FileUploadResponse(
        path     = str(dest_path),
        filename = safe_filename,
        type     = type,
    )


@router.post(
    "/",
    response_model=DatasourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create and save a new datasource",
)
async def create_datasource(
    payload:      DatasourcePayload,
    current_user: CurrentUser,
    db:           DB,
) -> DatasourceResponse:
    """
    Creates a new datasource record with encrypted credentials.
    The frontend should only call this after a successful /test call.
    (We do not enforce "must have tested" on the backend — that is a UI concern.)
    """
    try:
        result = await service.create_datasource(
            payload   = payload,
            tenant_id = current_user["tenant_id"],
            user_id   = current_user["id"],
            db        = db,
        )
        return DatasourceResponse(**result)

    except ValueError as exc:
        # service.create_datasource raises ValueError for duplicate names
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )


@router.get(
    "/",
    response_model=DatasourceListResponse,
    summary="List all datasources for the current tenant",
)
async def list_datasources(
    current_user: CurrentUser,
    db:           DB,
) -> DatasourceListResponse:
    """
    Returns all datasources registered under the authenticated tenant.
    Credentials and cert paths are never included in the response.
    """
    sources = await service.list_datasources(
        tenant_id = current_user["tenant_id"],
        db        = db,
    )
    return DatasourceListResponse(
        data  = [DatasourceResponse(**s) for s in sources],
        count = len(sources),
    )