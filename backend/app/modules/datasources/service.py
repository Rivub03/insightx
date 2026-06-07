# app/modules/datasources/service.py
#
# PURPOSE:
#   Business logic layer. No HTTP awareness — no Request or Response objects here.
#   Called by the router; calls the encryptor, connection tester, and the DB.
#
# DB ACCESS PATTERN:
#   Uses SQLAlchemy 2.0 async API (select(), insert(), etc.).
#   The AsyncSession is injected by FastAPI's dependency injection system
#   via get_db() in router.py — not imported directly here.

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.datasource import Datasource
from app.modules.datasources.credential_encryptor import encrypt
from app.modules.datasources.connection_tester import test_connection
from app.modules.datasources.schemas import DatasourcePayload


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

async def test_datasource_connection(payload: DatasourcePayload) -> dict:
    """
    Tests a connection WITHOUT saving anything.
    Called by the /test endpoint with plaintext credentials from the form.

    Args:
        payload: Validated DatasourcePayload (credentials in plaintext)

    Returns:
        Connection test result from connection_tester.test_connection()
    """
    # Convert the Pydantic model to a plain dict for the driver layer.
    # model_dump() is the Pydantic v2 equivalent of .dict() / spreading the object.
    config = payload.model_dump()

    # Flatten the TLS sub-model to a plain dict (it's already nested correctly)
    return await test_connection(config)


async def create_datasource(
    payload:   DatasourcePayload,
    tenant_id: str,
    user_id:   str,
    db:        AsyncSession,
) -> dict:
    """
    Creates and persists a new datasource record.

    Credentials are encrypted before the DB write — the plaintext credentials
    object never touches the database row.

    Args:
        payload:   Validated DatasourcePayload
        tenant_id: From the authenticated session (never from the request body)
        user_id:   For audit trail (created_by)
        db:        Injected AsyncSession from get_db()

    Returns:
        Safe datasource dict (sensitive fields masked)

    Raises:
        ValueError: If a datasource with this name already exists for the tenant
    """
    # Check for duplicate name within the tenant.
    # The DB also enforces this via a UNIQUE constraint, but checking here gives
    # a friendlier error message than a generic IntegrityError.
    existing = await db.execute(
        select(Datasource).where(
            Datasource.tenant_id == tenant_id,
            Datasource.name      == payload.name,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError(f"A data source named '{payload.name}' already exists for this tenant.")

    # Encrypt credentials — this is the only place encryption happens
    encrypted_creds = encrypt(payload.credentials)

    tls = payload.tls

    datasource = Datasource(
        id                    = uuid.uuid4(),
        name                  = payload.name,
        tenant_id             = tenant_id,
        engine                = payload.engine.value,
        host                  = payload.host,
        port                  = payload.port,
        database_name         = payload.database,
        oracle_connection_type= payload.oracle_connection_type.value if payload.oracle_connection_type else None,
        auth_method           = payload.auth_method.value,
        encrypted_credentials = encrypted_creds,
        tls_enabled           = tls.enabled            if tls else False,
        tls_verify_server_cert= tls.verify_server_cert if tls else True,
        tls_mode              = tls.mode               if tls else None,
        tls_ca_cert_path      = tls.ca_cert_path       if tls else None,
        tls_client_cert_path  = tls.client_cert_path   if tls else None,
        tls_client_key_path   = tls.client_key_path    if tls else None,
        created_by            = user_id,
    )

    db.add(datasource)
    await db.flush()    # Writes to DB within the transaction but before commit
                        # The session in get_db() commits after the route handler returns

    return _mask_sensitive_fields(datasource)


async def list_datasources(tenant_id: str, db: AsyncSession) -> list[dict]:
    """
    Returns all datasources for a given tenant.
    Credentials and cert paths are always stripped from the response.

    Args:
        tenant_id: From the authenticated session
        db:        Injected AsyncSession

    Returns:
        List of safe datasource dicts
    """
    result = await db.execute(
        select(Datasource)
        .where(Datasource.tenant_id == tenant_id)
        .order_by(Datasource.created_at.desc())
    )
    datasources = result.scalars().all()
    return [_mask_sensitive_fields(ds) for ds in datasources]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _mask_sensitive_fields(datasource: Datasource) -> dict:
    """
    Strips all sensitive fields before any API response.

    Fields removed:
        encrypted_credentials  — AES-256-GCM blob; never useful to the client
        tls_*_cert_path        — Server-side filesystem paths; not useful to client

    Fields added (boolean indicators):
        has_credentials  — True if credentials are stored (without revealing them)
        has_ca_cert      — True if a CA cert file is configured
        has_client_cert  — True if a client cert file is configured

    Args:
        datasource: Raw ORM model instance

    Returns:
        Safe dict suitable for the DatasourceResponse Pydantic model
    """
    return {
        "id":                     str(datasource.id),
        "name":                   datasource.name,
        "tenant_id":              datasource.tenant_id,
        "engine":                 datasource.engine,
        "host":                   datasource.host,
        "port":                   datasource.port,
        "database_name":          datasource.database_name,
        "oracle_connection_type": datasource.oracle_connection_type,
        "auth_method":            datasource.auth_method,
        "tls_enabled":            datasource.tls_enabled,
        "tls_mode":               datasource.tls_mode,
        "created_at":             datasource.created_at.isoformat() if datasource.created_at else None,
        "updated_at":             datasource.updated_at.isoformat() if datasource.updated_at else None,
        "created_by":             datasource.created_by,
        "last_tested_at":         datasource.last_tested_at.isoformat() if datasource.last_tested_at else None,
        "last_test_status":       datasource.last_test_status,
        # Presence indicators — never the actual values
        "has_credentials":        bool(datasource.encrypted_credentials),
        "has_ca_cert":            bool(datasource.tls_ca_cert_path),
        "has_client_cert":        bool(datasource.tls_client_cert_path),
    }