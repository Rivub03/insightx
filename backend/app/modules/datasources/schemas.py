# app/modules/datasources/schemas.py
#
# PURPOSE:
#   Pydantic v2 models for all datasource request and response shapes.
#   These replace the Joi validation schemas from the Node.js version.
#
# WHY PYDANTIC OVER JOI:
#   - Validation errors are automatically turned into HTTP 422 by FastAPI
#     with per-field error details — no manual error shaping needed.
#   - model_validator(mode='after') gives clean cross-field validation
#     (replaces Joi's .when() conditional schemas).
#   - FastAPI auto-generates OpenAPI docs from these models (/docs endpoint).

from typing import Any, Optional
from enum import Enum
from pydantic import BaseModel, Field, model_validator
from app.config.engines_config import ENGINES


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EngineType(str, Enum):
    postgresql = "postgresql"
    mssql      = "mssql"
    oracle     = "oracle"


class AuthMethod(str, Enum):
    password = "password"
    ldap     = "ldap"
    wallet   = "wallet"
    kerberos = "kerberos"
    windows  = "windows"
    azure_ad = "azure_ad"


class OracleConnectionType(str, Enum):
    sid          = "sid"
    service_name = "service_name"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class TLSConfig(BaseModel):
    """
    TLS/SSL configuration block.
    File paths below are server-side paths returned by POST /datasources/upload.
    They are NEVER sent back to the client in response bodies.
    """
    enabled:            bool = False
    verify_server_cert: bool = True   # Default on — secure by default

    # Engine-aware mode:
    #   PostgreSQL: 'require' | 'verify-ca' | 'verify-full'
    #   MSSQL:      'encrypt'
    #   Oracle:     'ssl'
    mode: Optional[str] = None

    # Server-side file paths (stored in DB; never returned to client)
    ca_cert_path:     Optional[str] = None
    client_cert_path: Optional[str] = None
    client_key_path:  Optional[str] = None


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class DatasourcePayload(BaseModel):
    """
    Input model for both POST /datasources and POST /datasources/test.
    The test endpoint uses the same shape — it just does not persist anything.

    Cross-field rules enforced by model_validator:
      1. oracle_connection_type is required when engine='oracle', forbidden otherwise
      2. auth_method must be valid for the selected engine
      3. credentials dict must contain the fields required by the auth_method
    """

    name:     str = Field(min_length=1, max_length=100, description="Human-readable connection name")
    engine:   EngineType
    host:     str = Field(min_length=1)
    port:     int = Field(ge=1, le=65535)
    database: str = Field(min_length=1, description="DB name, SID, or Service Name depending on engine")

    # Oracle-specific — required when engine='oracle', must not appear for others
    oracle_connection_type: Optional[OracleConnectionType] = None

    auth_method:  AuthMethod
    credentials:  dict[str, Any]     # Shape is validated by _validate_credentials_shape()
    tls:          Optional[TLSConfig] = None

    @model_validator(mode="after")
    def validate_engine_and_auth(self) -> "DatasourcePayload":
        """
        Runs after all individual field validators.
        Enforces the three cross-field rules described in the docstring above.
        Any ValueError raised here becomes an HTTP 422 with a clear message.
        """
        # --- Rule 1: oracle_connection_type ---
        if self.engine == EngineType.oracle:
            if self.oracle_connection_type is None:
                raise ValueError(
                    "oracle_connection_type ('sid' or 'service_name') is required when engine is 'oracle'"
                )
        else:
            if self.oracle_connection_type is not None:
                raise ValueError(
                    "oracle_connection_type must not be set for non-Oracle engines"
                )

        # --- Rule 2: auth_method compatibility ---
        valid_methods = ENGINES[self.engine.value]["supported_auth_methods"]
        if self.auth_method.value not in valid_methods:
            raise ValueError(
                f"'{self.auth_method.value}' is not supported for '{self.engine.value}'. "
                f"Valid methods: {valid_methods}"
            )

        # --- Rule 3: credentials shape ---
        self._validate_credentials_shape()
        return self

    def _validate_credentials_shape(self) -> None:
        """
        Validates that the credentials dict has the required keys for the
        chosen auth_method. These checks mirror the Joi schemas from the
        Node.js version.
        """
        creds  = self.credentials
        method = self.auth_method.value

        if method in ("password", "ldap"):
            if not creds.get("username"):
                raise ValueError(f"credentials.username is required for '{method}' auth")
            if not creds.get("password"):
                raise ValueError(f"credentials.password is required for '{method}' auth")

        elif method == "wallet":
            if not creds.get("wallet_location"):
                raise ValueError(
                    "credentials.wallet_location (server-side path from /upload) is required for 'wallet' auth"
                )

        elif method == "kerberos":
            if not creds.get("principal"):
                raise ValueError("credentials.principal is required for 'kerberos' auth")
            if not creds.get("keytab_path"):
                raise ValueError(
                    "credentials.keytab_path (server-side path from /upload) is required for 'kerberos' auth"
                )

        elif method == "azure_ad":
            if not creds.get("access_token"):
                raise ValueError(
                    "credentials.access_token (obtained via MSAL.js PKCE flow) is required for 'azure_ad' auth"
                )
        # 'windows' auth — domain, username, password are all optional


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class TestConnectionResponse(BaseModel):
    """
    Response from POST /datasources/test.
    Always returned with HTTP 200 — a failed DB connection is NOT an HTTP error.
    """
    success:    bool
    latency_ms: int
    # Only populated on failure:
    category: Optional[str] = None  # AUTH_FAILED | HOST_UNREACHABLE | TLS_HANDSHAKE_FAILED | etc.
    message:  Optional[str] = None


class DatasourceResponse(BaseModel):
    """
    Safe datasource record for API responses.
    Sensitive fields are stripped; boolean indicators show presence without revealing values.
    """
    id:                     str
    name:                   str
    tenant_id:              str
    engine:                 str
    host:                   str
    port:                   int
    database_name:          str
    oracle_connection_type: Optional[str] = None
    auth_method:            str
    tls_enabled:            bool
    tls_mode:               Optional[str] = None
    created_at:             str
    updated_at:             str
    created_by:             Optional[str] = None
    last_tested_at:         Optional[str] = None
    last_test_status:       Optional[str] = None
    # Boolean presence flags — never the actual values
    has_credentials: bool = False
    has_ca_cert:     bool = False
    has_client_cert: bool = False


class DatasourceListResponse(BaseModel):
    data:  list[DatasourceResponse]
    count: int


class FileUploadResponse(BaseModel):
    """Response from POST /datasources/upload."""
    path:     str   # Server-side absolute path — embed this in the datasource payload
    filename: str
    type:     str   # 'ca_cert' | 'client_cert' | 'client_key' | 'wallet' | 'keytab'