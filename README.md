# Project Directory Structure:

```
backend/
├── requirements.txt
└── app/
    ├── main.py
    ├── core/
    │   └── config.py                        # Pydantic Settings (replaces dotenv in Node)
    ├── db/
    │   ├── base.py                           # SQLAlchemy declarative base
    │   ├── session.py                        # Async session factory + get_db dependency
    │   └── models/
    │       └── datasource.py                 # SQLAlchemy ORM model
    ├── config/
    │   └── engines_config.py                 # Engine definitions (replaces engines.config.js)
    └── modules/
        └── datasources/
            ├── __init__.py
            ├── router.py                     # APIRouter — routes + handlers (replaces routes + controller)
            ├── schemas.py                    # Pydantic models (replaces Joi validators)
            ├── service.py                    # Business logic (unchanged concept)
            ├── connection_tester.py          # Dispatches to drivers; classifies errors
            ├── credential_encryptor.py       # AES-256-GCM (replaces Node crypto module)
            └── drivers/
                ├── __init__.py
                ├── postgres_driver.py        # Wraps asyncpg (replaces pg)
                ├── mssql_driver.py           # Wraps pyodbc (replaces mssql)
                └── oracle_driver.py          # Wraps python-oracledb (replaces oracledb)

frontend/
└── src/
    └── features/
        └── data-sources/
            ├── constants/
            │   └── engines.js         # Engine metadata — single source of truth for FE
            ├── api/
            │   └── datasource.api.js  # All fetch() calls to the backend
            ├── hooks/
            │   ├── useDataSourceForm.js   # All wizard form state in one place
            │   └── useConnectionTest.js   # Test flow state (idle/testing/success/failed)
            ├── components/
            │   ├── EngineSelector.jsx
            │   ├── ConnectionDetailsForm.jsx
            │   ├── AuthConfigForm.jsx
            │   ├── TLSConfigForm.jsx
            │   └── TestConnectionPanel.jsx
            └── pages/
                ├── AddDataSourcePage.jsx  # Wizard container — orchestrates all steps
                └── DataSourceListPage.jsx

database/
└── migrations/
    └── 001_create_datasources.sql
```

# M1: Data Source Onboarding

> **Module:** M1 — Data Source Onboarding  
> **Feature:** [107125](https://dev.azure.com/erainfotechbd/ERA%20InfoTech%20Limited/_workitems/edit/107125)  
> **Stack:** FastAPI (Python 3.11) · React 18 · PostgreSQL (metadata) · asyncpg · pyodbc · python-oracledb

---

## Table of Contents

1. [Project Overview](https://claude.ai/chat/f46df232-ea36-44c4-933c-0296ce7147b2#1-project-overview)
2. [Design Patterns](https://claude.ai/chat/f46df232-ea36-44c4-933c-0296ce7147b2#2-design-patterns)
3. [Module Reference](https://claude.ai/chat/f46df232-ea36-44c4-933c-0296ce7147b2#3-module-reference)
   - [Backend Modules](https://claude.ai/chat/f46df232-ea36-44c4-933c-0296ce7147b2#31-backend-modules)
   - [Frontend Modules](https://claude.ai/chat/f46df232-ea36-44c4-933c-0296ce7147b2#32-frontend-modules)
4. [System Architecture](https://claude.ai/chat/f46df232-ea36-44c4-933c-0296ce7147b2#4-system-architecture)
5. [Prerequisites](https://claude.ai/chat/f46df232-ea36-44c4-933c-0296ce7147b2#5-prerequisites)
6. [Running the Application](https://claude.ai/chat/f46df232-ea36-44c4-933c-0296ce7147b2#6-running-the-application)
   - [Backend](https://claude.ai/chat/f46df232-ea36-44c4-933c-0296ce7147b2#61-backend)
   - [Frontend](https://claude.ai/chat/f46df232-ea36-44c4-933c-0296ce7147b2#62-frontend)
   - [Frontend Proxy Setup](https://claude.ai/chat/f46df232-ea36-44c4-933c-0296ce7147b2#63-frontend-proxy-setup-critical)
7. [Environment Variables](https://claude.ai/chat/f46df232-ea36-44c4-933c-0296ce7147b2#7-environment-variables)
8. [Testing Database Connections](https://claude.ai/chat/f46df232-ea36-44c4-933c-0296ce7147b2#8-testing-database-connections)

---

## 1. Project Overview

M1 is the foundational module of InsightX. Every downstream capability — NL-to-SQL, Data Dictionary, Insights — depends on a registered, live database connection. This module provides:

- A **5-step wizard UI** for registering Oracle, PostgreSQL, and MS SQL Server connections
- **Engine-specific authentication**: username/password, Oracle Wallet, Kerberos, Windows Auth, Azure AD
- **TLS/SSL configuration** with cert upload and mutual TLS support
- **Test-before-save**: live connection testing with classified error feedback before any record is persisted
- **Encrypted credential storage**: AES-256-GCM, credentials never stored in plaintext
- **Multi-tenant isolation**: all records are scoped to a `tenant_id`

---

## 2. Design Patterns

This module does **not** use a single design pattern. It deliberately combines several well-established patterns, each chosen for a specific reason. What follows is an honest description of each one.

---

### 2.1 Application Factory Pattern

**Where:** `app/main.py` → `create_app()`

**What it is:** Instead of creating the FastAPI application at module level (`app = FastAPI()`), the application is created inside a function (`create_app()`) that configures and returns it. The module-level `app` variable then calls that function.

```python
# Without factory — hard to test, hard to configure per-environment
app = FastAPI()

# With factory — clean, testable, environment-aware
def create_app() -> FastAPI:
    app = FastAPI(...)
    app.add_middleware(...)
    app.include_router(...)
    return app

app = create_app()
```

**Why we used it:** It allows test suites to call `create_app()` with a different configuration (e.g., a test database URL, mock auth) without affecting the real application instance. It also keeps the startup sequence explicit and readable — middleware is registered in one place, routers are mounted in one place.

---

### 2.2 Strategy Pattern

**Where:** `app/modules/datasources/connection_tester.py` → `driver_map`

**What it is:** The Strategy pattern defines a family of algorithms, encapsulates each one in its own module, and makes them interchangeable. The caller selects the right algorithm at runtime without changing its own code.

```python
# The three "strategies" — each driver implements the same interface
driver_map = {
    "postgresql": test_postgres_connection,
    "mssql":      test_mssql_connection,
    "oracle":     test_oracle_connection,
}

# Runtime selection — connection_tester never imports a driver directly
driver_fn = driver_map.get(config["engine"])
result = await driver_fn(config)
```

**Why we used it:** Adding a fourth database engine (e.g., MySQL) requires writing one new driver file and adding one line to `driver_map`. The tester, service, and router are completely unaffected. This is the correct answer to the open/closed principle: open for extension, closed for modification.

---

### 2.3 Adapter Pattern

**Where:** `app/modules/datasources/drivers/*.py`

**What it is:** Each driver module wraps a completely different third-party library (`asyncpg`, `pyodbc`, `python-oracledb`) and adapts it to a single, consistent output shape. The rest of the system never calls these libraries directly and never needs to know which one is in use.

```
asyncpg      ──┐
               │ all return: {"success": bool, "latency_ms": int, "raw_error"?: Exception}
pyodbc       ──┤
               │
python-oracledb─┘
```

**Why we used it:** Without this pattern, `connection_tester.py` would need `if engine == "postgresql"` ... `elif engine == "mssql"` ... in multiple places, and adding a new engine would mean editing the tester. The adapters isolate all library-specific code in one file per engine.

---

### 2.4 Dependency Injection

**Where:** `app/modules/datasources/router.py` — FastAPI's `Depends()` system

**What it is:** Instead of creating dependencies (database session, current user) inside the route handler, they are declared as function parameters and injected by the framework at request time.

```python
@router.post("/")
async def create_datasource(
    payload:      DatasourcePayload,   # injected: parsed + validated by Pydantic
    current_user: CurrentUser,         # injected: from get_current_user()
    db:           DB,                  # injected: AsyncSession from get_db()
):
    ...
```

**Why we used it:** Route handlers become independently testable — you can pass mock dependencies without starting a real server or database. It also enforces separation of concerns: the route handler knows nothing about how a session is created or how auth works.

---

### 2.5 Layered (N-Tier) Architecture

**Where:** The overall backend structure

**What it is:** The system is divided into strict horizontal layers. Each layer only communicates with the layer directly below it. No layer skips a level.

```
┌─────────────────────────────────────────┐  ← Layer 1: Presentation
│  router.py   (HTTP, request/response)   │
├─────────────────────────────────────────┤  ← Layer 2: Business Logic
│  service.py  (rules, orchestration)     │
├─────────────────────────────────────────┤  ← Layer 3: Infrastructure
│  connection_tester.py                   │
│  credential_encryptor.py                │
│  drivers/  (pg, mssql, oracle)          │
├─────────────────────────────────────────┤  ← Layer 4: Data
│  db/models/datasource.py                │
│  db/session.py                          │
└─────────────────────────────────────────┘
```

**Why we used it:** It prevents "god functions" that do HTTP parsing, business logic, database writes, and encryption all in one place. Bugs are easier to isolate — a wrong HTTP status code is a router problem; a wrong encryption format is an encryptor problem.

---

### 2.6 Wizard Pattern (Frontend)

**Where:** `src/features/data-sources/pages/AddDataSourcePage.jsx`

**What it is:** A multi-step linear form where each step's available options depend on selections made in previous steps. Navigation is sequential, and the final step aggregates all prior state.

```
Step 0: Engine → Step 1: Connection → Step 2: Auth → Step 3: TLS → Step 4: Test & Save
          ↓               ↓                ↓
     Sets port       Sets DB label    Filters auth methods
     default         based on type    by engine
```

**Why we used it:** The auth method options for Oracle are entirely different from those for MSSQL. The TLS labels differ by engine. A single flat form would be confusing and would require showing and hiding many fields. The wizard makes each decision's consequences immediately visible.

---

### 2.7 Custom Hook Pattern (Frontend)

**Where:** `src/features/data-sources/hooks/`

**What it is:** React logic — specifically state and side effects — that is reused across components is extracted into custom `use*` functions.

| Hook                | Responsibility                                                                                                  |
| ------------------- | --------------------------------------------------------------------------------------------------------------- |
| `useDataSourceForm` | All 4 wizard steps' form state in one place. `buildPayload()` assembles the final API body.                     |
| `useConnectionTest` | The test state machine: `idle → testing → success / failed`. Exposes `canSave` as the save button's gatekeeper. |

**Why we used it:** Without these hooks, `AddDataSourcePage.jsx` would need to manage ~20 state variables and contain all the test logic inline. The hooks let the page component be a thin orchestrator that just wires everything together.

---

## 3. Module Reference

### 3.1 Backend Modules

```
backend/
├── requirements.txt
└── app/
    ├── main.py
    ├── core/
    │   └── config.py
    ├── db/
    │   ├── base.py
    │   ├── session.py
    │   └── models/
    │       └── datasource.py
    ├── config/
    │   └── engines_config.py
    └── modules/
        └── datasources/
            ├── router.py
            ├── schemas.py
            ├── service.py
            ├── connection_tester.py
            ├── credential_encryptor.py
            └── drivers/
                ├── postgres_driver.py
                ├── mssql_driver.py
                └── oracle_driver.py
```

---

#### `app/main.py`

**Role:** Application factory.  
Creates the FastAPI instance, registers CORS middleware, and mounts the datasources router at `/api/v1/datasources`. The `create_app()` function is the factory; the module-level `app` variable is what `uvicorn` points at.

**Code:**
```python
# app/main.py
#
# PURPOSE:
#   FastAPI application factory. Creates the app instance, registers
#   middleware, and mounts all routers. This is the entry point for uvicorn.
#
# USAGE:
#   Development:  uvicorn app.main:app --reload --port 8000
#   Production:   uvicorn app.main:app --workers 4 --port 8000

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.modules.datasources.router import router as datasources_router
from app.db.session import engine
from app.db.base import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager — runs code on app startup and shutdown.
    Creates all database tables on startup (if they don't exist).
    """
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()


def create_app() -> FastAPI:
    """
    Application factory function.
    Keeps app creation separate from the module-level `app` variable,
    which makes testing cleaner (you can call create_app() with different configs).
    """
    app = FastAPI(
        title="InsightX API",
        version="1.0.0",
        description="InsightX Agentic Reporting Platform — M1: Data Source Onboarding",
        lifespan=lifespan,
        # FastAPI auto-generates /docs (Swagger UI) and /redoc from route definitions
    )

    # CORS — allow the React dev server to reach the API
    # Adjust allow_origins for staging/production deployments
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,  # Required for cookie-based sessions
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount the datasources router under the /api/v1/datasources prefix
    app.include_router(
        datasources_router,
        prefix="/api/v1/datasources",
        tags=["Data Sources"],
    )

    return app


# Module-level app instance — uvicorn points at this
app = create_app()
```

---

#### `app/core/config.py`

**Role:** Settings management.  
Uses `pydantic-settings` to load environment variables (and `.env` files) with type validation. The `settings` singleton is the single place any module reads configuration — no module calls `os.getenv()` directly. If a required variable is missing, the app fails at startup with a clear error.

**Key variables:** `DATABASE_URL`, `CREDENTIAL_ENCRYPTION_KEY`, `SECURE_FILES_DIR`.

**Code:**
```Python
# app/core/config.py
#
# PURPOSE:
#   Application settings loaded from environment variables via pydantic-settings.
#   pydantic-settings validates types, supports .env files, and raises clear errors
#   at startup if required variables are missing — much better than bare os.getenv().
#
# REQUIRED .env variables:
#   DATABASE_URL              postgresql+asyncpg://user:pass@host:port/insightx_meta
#   CREDENTIAL_ENCRYPTION_KEY 64-character hex string
#
# GENERATE THE ENCRYPTION KEY:
#   python -c "import secrets; print(secrets.token_hex(32))"
#
# OPTIONAL .env variables:
#   SECURE_FILES_DIR          /var/insightx/secure-uploads  (default)
#   MAX_UPLOAD_SIZE_MB        5                              (default)

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- InsightX metadata DB ---
    # For production: postgresql+asyncpg://user:password@host:port/database_name
    # For development without PostgreSQL: sqlite+aiosqlite:///./insightx_dev.db
    database_url: str = "sqlite+aiosqlite:///./insightx_dev.db"

    # --- AES-256-GCM credential encryption key ---
    # 64 hex characters = 32 bytes = 256 bits
    # Store this in a secrets manager (AWS Secrets Manager, Azure Key Vault) in production
    credential_encryption_key: str

    # --- Secure file storage ---
    # Directory for TLS certs, Oracle Wallets, and Kerberos keytabs
    # Must be outside the webroot and writable by the app process
    # In Docker, mount this as a persistent volume — NOT ephemeral container storage
    secure_files_dir: str = "./secure-uploads"

    # Max file size for cert/wallet/keytab uploads (MB)
    max_upload_size_mb: int = 5

    # Pydantic-settings v2 config — replaces the inner Config class
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    lru_cache ensures the .env file is only parsed once per process lifecycle.
    """
    return Settings()


# Module-level convenience alias — import `settings` directly in other modules
settings = get_settings()
```

---

#### `app/db/base.py`

**Role:** SQLAlchemy declarative base.  
Contains only `class Base(DeclarativeBase)`. Kept separate to prevent circular imports when models reference each other (a common SQLAlchemy pain point).

**Code:**
```Python
# app/db/base.py
#
# PURPOSE:
#   Declares the SQLAlchemy ORM base class.
#   All ORM models (datasource.py and any future models) inherit from Base.
#   Kept in its own file to avoid circular imports when models import from each other.

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    SQLAlchemy 2.0 declarative base.
    Using the class-based style (not the legacy declarative_base() function).
    """
    pass
```

---

#### `app/db/session.py`

**Role:** Async database session factory.  
Creates the `async_engine` pointed at the InsightX metadata PostgreSQL database. The `get_db()` async generator is a FastAPI dependency — it yields an `AsyncSession` per request, commits on success, and rolls back on exception. Route handlers never manage sessions manually.

**Code:**
```Python
# app/db/session.py
#
# PURPOSE:
#   Creates the async SQLAlchemy engine and session factory.
#   Exposes `get_db` — a FastAPI dependency that yields an AsyncSession
#   and handles commit/rollback automatically.
#
# HOW IT WORKS IN A ROUTE:
#   @router.get("/")
#   async def handler(db: AsyncSession = Depends(get_db)):
#       result = await db.execute(select(Datasource))
#       ...
#   FastAPI injects `db`, and `get_db` closes/rolls back the session
#   when the request completes — no manual session management needed.

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from app.core.config import settings


# The async engine manages the connection pool to the InsightX metadata DB
# pool_pre_ping=True: tests connections before use — handles stale connections
#   gracefully after network interruptions or DB restarts
# For SQLite (development), we disable pooling since SQLite doesn't support concurrent writes
is_sqlite = "sqlite" in settings.database_url.lower()
engine_kwargs = {
    "echo": False,           # Set True in development to log all SQL statements
    "pool_pre_ping": True,
}

if is_sqlite:
    # SQLite async setup
    engine_kwargs.update({
        "pool_size": 1,
        "max_overflow": 0,
        "connect_args": {"check_same_thread": False},
    })
else:
    # PostgreSQL setup
    engine_kwargs.update({
        "pool_size": 10,         # Persistent connections in the pool
        "max_overflow": 20,      # Temporary connections allowed above pool_size under load
    })

engine = create_async_engine(settings.database_url, **engine_kwargs)

# Session factory — instantiated once, called many times
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Avoids "DetachedInstanceError" when reading after commit
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a database session per request.

    - Commits automatically on successful request completion
    - Rolls back automatically if an exception is raised
    - Always closes the session (via async context manager)

    Inject this into any route handler:
        db: AsyncSession = Depends(get_db)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

---

#### `app/db/models/datasource.py`

**Role:** SQLAlchemy ORM model.  
Defines the `datasources` table structure with all constraints (unique name per tenant, valid oracle*connection_type values, valid last_test_status values). Sensitive columns (`encrypted_credentials`, `tls*\*\_cert_path`) exist in the model but are always stripped before any API response by `service.py`'s `\_mask_sensitive_fields()`.

**Code:**
```Python
# app/db/models/datasource.py
#
# PURPOSE:
#   SQLAlchemy ORM model for the datasources table.
#   Maps directly to the schema defined in database/migrations/001_create_datasources.sql.
#   Uses SQLAlchemy 2.0 Mapped/mapped_column syntax (type-annotated, IDE-friendly).
#
# SENSITIVE FIELDS — never returned via API:
#   encrypted_credentials:  AES-256-GCM ciphertext
#   tls_*_cert_path:        Server-side filesystem paths to cert files

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Index,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Datasource(Base):
    __tablename__ = "datasources"

    # Table-level constraints — mirror the SQL migration exactly
    __table_args__ = (
        # Two sources in the same tenant cannot share a name
        UniqueConstraint("tenant_id", "name", name="uq_datasource_name_per_tenant"),
        CheckConstraint(
            "oracle_connection_type IN ('sid', 'service_name')",
            name="chk_oracle_connection_type",
        ),
        CheckConstraint(
            "last_test_status IN ('success', 'failed')",
            name="chk_last_test_status",
        ),
        # Almost every query filters by tenant_id — index this
        Index("idx_datasources_tenant", "tenant_id"),
    )

    # --- Primary key ---
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="UUID primary key — avoids sequential ID enumeration",
    )

    # --- Identity ---
    name:      Mapped[str] = mapped_column(String(100), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # --- Engine ---
    # One of: 'postgresql', 'mssql', 'oracle'
    engine: Mapped[str] = mapped_column(String(20), nullable=False)

    # --- Connection details (not sensitive) ---
    host:          Mapped[str] = mapped_column(String(255), nullable=False)
    port:          Mapped[int] = mapped_column(Integer,     nullable=False)
    database_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Oracle-only: 'sid' or 'service_name'; NULL for PostgreSQL and MSSQL
    oracle_connection_type: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )

    # --- Authentication ---
    auth_method: Mapped[str] = mapped_column(String(20), nullable=False)

    # AES-256-GCM encrypted JSON string: "iv_hex:tag_hex:ciphertext_hex"
    # NEVER returned via the API — not even to the owning tenant
    encrypted_credentials: Mapped[str] = mapped_column(Text, nullable=False)

    # --- TLS (paths are server-side references — not cert content) ---
    tls_enabled:            Mapped[bool]         = mapped_column(Boolean,     nullable=False, default=False)
    tls_verify_server_cert: Mapped[bool]         = mapped_column(Boolean,     nullable=False, default=True)
    tls_mode:               Mapped[Optional[str]] = mapped_column(String(20),  nullable=True)
    tls_ca_cert_path:       Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tls_client_cert_path:   Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tls_client_key_path:    Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # --- Audit ---
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )
    created_by:       Mapped[Optional[str]]      = mapped_column(String(100), nullable=True)
    last_tested_at:   Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_test_status: Mapped[Optional[str]]      = mapped_column(String(20),  nullable=True)
```

---

#### `app/config/engines_config.py`

**Role:** Single source of truth for engine metadata (backend copy).  
A plain Python dict that defines, per engine: default port, supported auth methods, valid TLS modes, and whether a connection type toggle is needed. Both the validator (`schemas.py`) and the frontend (`engines.js`) reference equivalent copies of this data. **Keep the two in sync.**

**Code:**
```Python
# app/config/engines_config.py
#
# PURPOSE:
#   Central engine capability configuration registry.
#   Specifies auth methods allowed for each database engine on the backend.

ENGINES = {
    "postgresql": {
        "supported_auth_methods": ["password", "ldap"],
    },
    "oracle": {
        "supported_auth_methods": ["password", "wallet", "kerberos"],
    },
    "mssql": {
        "supported_auth_methods": ["password", "windows", "azure_ad"],
    },
}
```

---

#### `app/modules/datasources/schemas.py`

**Role:** Request and response validation (Pydantic v2, replaces Joi).  
Defines `DatasourcePayload` with a `model_validator` that enforces three cross-field rules: oracle_connection_type is required iff engine is oracle; auth_method must be valid for the engine; credentials dict must contain the required keys for the auth method. FastAPI turns any `ValueError` raised here into an HTTP 422 with per-field details automatically.

**Key models:** `DatasourcePayload` (input), `TestConnectionResponse`, `DatasourceResponse`, `DatasourceListResponse`, `FileUploadResponse`.


**Code:**
```Python
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

from typing import Any, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field, model_validator, ConfigDict
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

# ============================================================================
# Credential Models
# ============================================================================

class PasswordCredentials(BaseModel):
    username: str
    password: str


class LDAPCredentials(BaseModel):
    username: str
    password: str


class WalletCredentials(BaseModel):
    wallet_location: str


class KerberosCredentials(BaseModel):
    principal: str
    keytab_path: str


class AzureADCredentials(BaseModel):
    access_token: str


class WindowsCredentials(BaseModel):
    domain: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


CredentialType = Union[
    PasswordCredentials,
    LDAPCredentials,
    WalletCredentials,
    KerberosCredentials,
    AzureADCredentials,
    WindowsCredentials,
]


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

    @model_validator(mode="after")
    def validate_tls(self):

        if self.enabled and not self.mode:
            raise ValueError(
                "TLS mode is required when TLS is enabled"
            )

        return self


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class DatasourcePayload(BaseModel):
    """
    Input model for both POST /datasources and POST /datasources/test.
    The test endpoint uses the same shape — it just does not persist anything.

    Cross-field rules enforced by model_validator (validation rules):
      1. oracle_connection_type is required when engine='oracle', forbidden otherwise
      2. auth_method must be valid for the selected engine
      3. credentials dict must contain the fields required by the auth_method
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Finance Oracle",
                "engine": "oracle",
                "host": "oracle.company.com",
                "port": 1521,
                "database": "ORCL",
                "oracle_connection_type": "service_name",
                "auth_method": "password",
                "credentials": {
                    "username": "analytics_user",
                    "password": "secret"
                },
                "tls": {
                    "enabled": True,
                    "mode": "ssl",
                    "verify_server_cert": True
                }
            }
        }
    )


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
```
---

#### `app/modules/datasources/credential_encryptor.py`

**Role:** AES-256-GCM encryption/decryption for credential dicts.  
Credentials are JSON-serialised and encrypted before any DB write. The stored format is `iv_hex:tag_hex:ciphertext_hex` (a single TEXT column). GCM mode includes an authentication tag — if the stored value is tampered with, `decrypt()` raises `InvalidTag` rather than silently returning garbage. The key is read from `CREDENTIAL_ENCRYPTION_KEY` at call time, not at import time.

**Code:**
```Python
# app/modules/datasources/credential_encryptor.py
#
# PURPOSE:
#   Encrypts credential dicts before writing to the DB and decrypts them
#   when a live connection is needed. Nothing else in the system accesses
#   raw credentials — all reads/writes go through this module.
#
# ALGORITHM: AES-256-GCM (Authenticated Encryption)
#   GCM mode produces a 16-byte authentication tag alongside the ciphertext.
#   If the stored string is tampered with or the wrong key is used, the
#   AESGCM.decrypt() call raises InvalidTag — this is intentional.
#
# LIBRARY: `cryptography` (pip install cryptography)
#   Uses AESGCM from cryptography.hazmat.primitives.ciphers.aead.
#   This is strictly better than AES-CBC for this use case because it
#   detects tampering (CBC does not).
#
# STORAGE FORMAT: "iv_hex:tag_hex:ciphertext_hex"
#   Three components, colon-delimited, all hex-encoded.
#   Stored as a single TEXT column in the datasources table.
#
# GENERATE A KEY:
#   python -c "import secrets; print(secrets.token_hex(32))"
#   Add to .env:  CREDENTIAL_ENCRYPTION_KEY=<64-char hex string>

import json
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.core.config import settings

# AES-256-GCM constants
_IV_BYTES  = 12  # 96-bit nonce — NIST recommended length for GCM
_TAG_BYTES = 16  # 128-bit authentication tag — maximum GCM security


def _get_key() -> bytes:
    """
    Validates and returns the encryption key from settings.
    Called at runtime (not at import time) so startup can proceed even if
    the key is not yet set — the first actual encrypt/decrypt call will fail
    loudly with a clear message.

    Returns:
        32-byte (256-bit) key as bytes

    Raises:
        ValueError: If the key is missing or not exactly 64 hex characters
    """
    hex_key = settings.credential_encryption_key

    if not hex_key or len(hex_key) != 64:
        raise ValueError(
            "CREDENTIAL_ENCRYPTION_KEY must be a 64-character hex string. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )

    try:
        return bytes.fromhex(hex_key)
    except ValueError:
        raise ValueError("CREDENTIAL_ENCRYPTION_KEY contains invalid hex characters")


def encrypt(credentials: dict) -> str:
    """
    Encrypts a credentials dict to a single storable string.

    The dict is JSON-serialised first, allowing any credential shape
    (password auth, wallet path, kerberos principal, etc.) to be stored
    in one TEXT column without needing separate encrypted columns per auth type.

    A fresh random IV is generated for every call.
    NEVER reuse an IV with the same key in GCM mode — doing so catastrophically
    breaks security guarantees.

    Args:
        credentials: Plain dict e.g. {"username": "sa", "password": "secret"}

    Returns:
        Encrypted string: "iv_hex:tag_hex:ciphertext_hex"
    """
    key = _get_key()
    iv  = os.urandom(_IV_BYTES)      # Fresh random nonce — never reuse

    aesgcm    = AESGCM(key)
    plaintext = json.dumps(credentials).encode("utf-8")

    # AESGCM.encrypt() returns ciphertext + tag concatenated (tag is the last 16 bytes)
    ciphertext_and_tag = aesgcm.encrypt(iv, plaintext, None)

    ciphertext = ciphertext_and_tag[:-_TAG_BYTES]
    tag        = ciphertext_and_tag[-_TAG_BYTES:]

    return ":".join([iv.hex(), tag.hex(), ciphertext.hex()])


def decrypt(encrypted_string: str) -> dict:
    """
    Decrypts a stored encrypted credentials string back to the original dict.

    Raises cryptography.exceptions.InvalidTag if the string has been tampered
    with or the wrong encryption key is configured. Do not catch this silently —
    let it propagate as a 500 so the operator knows something is wrong.

    Args:
        encrypted_string: "iv_hex:tag_hex:ciphertext_hex" from the database

    Returns:
        The original credentials dict

    Raises:
        ValueError:                            Malformed string format
        cryptography.exceptions.InvalidTag:    Tampered data or wrong key
    """
    parts = encrypted_string.split(":")

    if len(parts) != 3:
        raise ValueError(
            "Malformed encrypted credential — expected format 'iv_hex:tag_hex:ciphertext_hex'"
        )

    try:
        iv         = bytes.fromhex(parts[0])
        tag        = bytes.fromhex(parts[1])
        ciphertext = bytes.fromhex(parts[2])
    except ValueError as exc:
        raise ValueError(f"Encrypted credential contains invalid hex data: {exc}") from exc

    key    = _get_key()
    aesgcm = AESGCM(key)

    # Re-assemble: AESGCM.decrypt() expects ciphertext + tag concatenated
    plaintext = aesgcm.decrypt(iv, ciphertext + tag, None)

    return json.loads(plaintext.decode("utf-8"))
```
---

#### `app/modules/datasources/connection_tester.py`

**Role:** Connection test dispatcher and error classifier.  
Uses a `driver_map` dict (Strategy pattern) to call the right driver at runtime. Wraps the driver call in `asyncio.wait_for()` with a 10-second hard timeout. After the driver returns, `_classify_error()` translates raw driver exceptions into one of six category strings (`AUTH_FAILED`, `HOST_UNREACHABLE`, `TLS_HANDSHAKE_FAILED`, `TIMEOUT`, `UNSUPPORTED_CONFIG`, `UNKNOWN`) that the frontend displays distinctly.

**Code:**
```Python
# app/modules/datasources/connection_tester.py
#
# PURPOSE:
#   Single entry point for all connection tests. Responsibilities:
#     1. Dispatch to the correct driver based on config["engine"]
#     2. Enforce a 10-second hard outer timeout (asyncio.wait_for)
#     3. Classify raw driver exceptions into user-friendly category strings
#
# WHY CLASSIFY HERE (not in the drivers)?
#   Different engines raise different exception types and message strings
#   for the same underlying problem. For example, "wrong password" is:
#     asyncpg.InvalidPasswordError in PostgreSQL
#     "[28000] Login failed" in pyodbc MSSQL
#     "ORA-01017" in python-oracledb Oracle
#   Centralising classification here means the frontend always receives
#   the same small set of category strings regardless of engine.
#
# ERROR CATEGORIES:
#   AUTH_FAILED           Wrong username, password, or token
#   HOST_UNREACHABLE      Cannot reach host (firewall, DNS, port closed)
#   TLS_HANDSHAKE_FAILED  SSL/TLS negotiation failed
#   TIMEOUT               No response within 10 seconds
#   UNSUPPORTED_CONFIG    Feature not supported in current mode (e.g. Kerberos in Thin Mode)
#   UNKNOWN               Unclassified error

import asyncio
from app.modules.datasources.drivers.postgres_driver import test_postgres_connection
from app.modules.datasources.drivers.mssql_driver    import test_mssql_connection
from app.modules.datasources.drivers.oracle_driver   import test_oracle_connection

# Hard outer timeout — safety net if the driver's own timeout doesn't fire
_TIMEOUT_SECONDS = 10


def _classify_error(engine: str, error: Exception) -> dict:
    """
    Maps a raw driver exception to a user-friendly error category + message.

    Uses string matching on the error message because different drivers use
    different exception types for the same logical error. String matching is
    more portable across driver versions than isinstance checks.

    Args:
        engine: 'postgresql' | 'mssql' | 'oracle'
        error:  The exception raised by the driver

    Returns:
        {"category": str, "message": str}
    """
    msg = str(error).lower()

    # --- Authentication failures ---
    if any(pattern in msg for pattern in [
        "password authentication failed",     # asyncpg / psycopg2
        "invalid password",                   # asyncpg InvalidPasswordError
        "login failed",                       # pyodbc MSSQL
        "invalid username/password",          # python-oracledb
        "ora-01017",                          # Oracle: invalid username/password
        "ora-01005",                          # Oracle: null password given
        "28000",                              # SQLSTATE: invalid authorization spec
        "authentication failed",
        "access denied",
        "invalid token",                      # Azure AD token errors
    ]):
        return {
            "category": "AUTH_FAILED",
            "message":  "Authentication failed. Check your username, password, or token.",
        }

    # --- Host unreachable / connection refused ---
    if any(pattern in msg for pattern in [
        "connection refused",
        "could not connect to server",        # asyncpg
        "no such host",
        "name or service not known",          # DNS failure
        "tns:no listener",                    # Oracle: nothing listening on port
        "ora-12541",                          # Oracle: no listener
        "server is not found or not accessible",  # MSSQL ODBC
        "network-related or instance-specific",   # MSSQL generic network error
        "could not be resolved",
        "nodename nor servname provided",     # macOS DNS failure
        "getaddrinfo failed",
        "[08001]",                            # SQLSTATE: client unable to connect
    ]):
        return {
            "category": "HOST_UNREACHABLE",
            "message":  "Cannot reach the host. Check the hostname, port, and that the database is running.",
        }

    # --- TLS / SSL failures ---
    if any(pattern in msg for pattern in [
        "ssl",
        "tls",
        "certificate",
        "handshake",
        "ora-29024",                          # Oracle: certificate validation failure
        "certificate verify failed",
        "ssl handshake failed",
        "ssl routines",
        "[08001] ssl",
    ]):
        return {
            "category": "TLS_HANDSHAKE_FAILED",
            "message":  "TLS/SSL handshake failed. Check your certificates, SSL mode, and whether the server requires TLS.",
        }

    # --- Timeout ---
    if any(pattern in msg for pattern in [
        "timeout",
        "timed out",
        "ora-12170",                          # Oracle: connect timeout
        "connection timed out",
    ]):
        return {
            "category": "TIMEOUT",
            "message":  "Connection timed out after 10 seconds. The host may be slow or unreachable.",
        }

    # --- Unsupported configuration ---
    if any(pattern in msg for pattern in [
        "not supported in thin mode",         # python-oracledb Kerberos in Thin Mode
        "kerberos",
        "thick mode required",
        "no microsoft odbc driver",           # raised by _get_odbc_driver()
    ]):
        return {
            "category": "UNSUPPORTED_CONFIG",
            "message":  "This configuration requires additional server-side setup (e.g., Kerberos requires Oracle Thick Mode, or the Microsoft ODBC Driver is not installed).",
        }

    # --- Fallback ---
    return {
        "category": "UNKNOWN",
        "message":  f"Connection failed: {str(error)}",
    }


async def test_connection(config: dict) -> dict:
    """
    Tests a database connection using the appropriate driver.
    This is the ONLY function the service layer calls — it never imports drivers directly.

    The test is entirely non-destructive:
      - Only a trivial query (SELECT 1 / SELECT 1 FROM DUAL) is executed.
      - No schema introspection, no data read, no data written.

    Args:
        config: Full datasource config dict (engine, host, port, db, credentials, tls)
                Credentials must be in plaintext (not encrypted) — this is called
                from the /test endpoint which receives plaintext from the form.

    Returns:
        {
            "success":    bool,
            "latency_ms": int,
            "category":   str  (only on failure),
            "message":    str  (only on failure)
        }
    """
    driver_map = {
        "postgresql": test_postgres_connection,
        "mssql":      test_mssql_connection,
        "oracle":     test_oracle_connection,
    }

    driver_fn = driver_map.get(config.get("engine"))

    if driver_fn is None:
        return {
            "success":    False,
            "latency_ms": 0,
            "category":   "UNSUPPORTED_ENGINE",
            "message":    f"Engine '{config.get('engine')}' is not supported.",
        }

    try:
        # asyncio.wait_for enforces the hard timeout.
        # If the driver's own timeout fires first (which it should), the driver
        # returns {"success": False, "raw_error": ...} and we classify it below.
        # If the outer timeout fires first, asyncio.TimeoutError is raised and
        # caught here.
        result = await asyncio.wait_for(
            driver_fn(config),
            timeout=_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        return {
            "success":    False,
            "latency_ms": _TIMEOUT_SECONDS * 1000,
            "category":   "TIMEOUT",
            "message":    "Connection attempt timed out after 10 seconds.",
        }

    if result["success"]:
        return {"success": True, "latency_ms": result["latency_ms"]}

    # Classify the raw error into a user-friendly category
    raw_error  = result.get("raw_error") or Exception("Unknown error")
    classified = _classify_error(config.get("engine", ""), raw_error)

    return {
        "success":    False,
        "latency_ms": result["latency_ms"],
        **classified,
    }
```
---

#### `app/modules/datasources/drivers/postgres_driver.py`

**Role:** Adapter for `asyncpg` (PostgreSQL).  
Builds an `ssl.SSLContext` from the TLS config (loading CA cert and optional client cert/key from file paths), connects with `asyncpg.connect()`, runs `SELECT 1`, and returns the normalised result dict. Fully async — no executor wrapper needed.

**Code:**
```Python
# app/modules/datasources/drivers/postgres_driver.py
#
# PURPOSE:
#   Wraps asyncpg to test a PostgreSQL connection.
#   Fully async — no executor wrapper needed.
#
# LIBRARY: asyncpg (pip install asyncpg)
#
# TLS NOTES:
#   asyncpg's `ssl` parameter accepts:
#     False / None            → no TLS
#     True                    → require TLS, verify server cert using system CA store
#     ssl.SSLContext          → custom context (custom CA, client cert, skip verification)
#
#   We build a custom SSLContext when TLS is enabled so we can:
#     - Load a custom CA cert (cafile= reads directly from the file path)
#     - Load client cert + key for mutual TLS
#     - Optionally disable server cert verification for self-signed certs
#
# TIMEOUT:
#   asyncpg's connect() accepts `timeout` in seconds.
#   The outer asyncio.wait_for() in connection_tester.py provides an
#   additional safety net in case the driver's own timeout misfires.

import ssl
import time
from typing import Optional
import asyncpg


def _build_ssl_context(tls: dict) -> Optional[ssl.SSLContext]:
    """
    Builds an ssl.SSLContext from the TLS config dict.
    Returns None if TLS is disabled.

    Args:
        tls: TLS config dict from the datasource payload

    Returns:
        ssl.SSLContext or None
    """
    if not tls or not tls.get("enabled"):
        return None

    if tls.get("verify_server_cert", True):
        # Verify the server certificate.
        # create_default_context() sets verify_mode=CERT_REQUIRED and check_hostname=True by default.
        if tls.get("ca_cert_path"):
            # Use the custom CA certificate file to verify the server
            ctx = ssl.create_default_context(cafile=tls["ca_cert_path"])
        else:
            # Use the system's default CA store
            ctx = ssl.create_default_context()
    else:
        # User has opted to skip server cert verification (e.g., self-signed cert in dev)
        # This should show a visible warning in the UI (handled on the frontend)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode    = ssl.CERT_NONE

    # Mutual TLS — load client certificate and private key
    if tls.get("client_cert_path") and tls.get("client_key_path"):
        ctx.load_cert_chain(
            certfile=tls["client_cert_path"],
            keyfile=tls["client_key_path"],
        )

    return ctx


async def test_postgres_connection(config: dict) -> dict:
    """
    Tests a PostgreSQL connection by establishing a connection and
    running a trivial query. Non-destructive — no data is read or written.

    Args:
        config: Normalised connection config dict with keys:
            host, port, database, credentials {username, password},
            auth_method, tls (optional)

    Returns:
        {
            "success": bool,
            "latency_ms": int,
            "raw_error": Exception  # only on failure
        }
    """
    host        = config["host"]
    port        = int(config["port"])
    database    = config["database"]
    credentials = config["credentials"]
    tls         = config.get("tls") or {}

    ssl_context = _build_ssl_context(tls)

    start = int(time.time() * 1000)
    conn  = None

    try:
        conn = await asyncpg.connect(
            host     = host,
            port     = port,
            database = database,
            user     = credentials["username"],
            password = credentials["password"],
            ssl      = ssl_context,
            timeout  = 10.0,  # seconds — asyncpg's own connect timeout
        )

        # SELECT 1 is the cheapest possible query to confirm the connection is live.
        # asyncpg.connect() does not guarantee a fully authenticated session
        # on all server versions without an actual query.
        await conn.fetchval("SELECT 1")

        return {"success": True, "latency_ms": int(time.time() * 1000) - start}

    except Exception as exc:
        return {
            "success":    False,
            "latency_ms": int(time.time() * 1000) - start,
            "raw_error":  exc,
        }

    finally:
        # Always release the connection — asyncpg connections are not pooled here
        if conn:
            try:
                await conn.close()
            except Exception:
                pass  # Ignore cleanup errors — the test result is already determined
```
---

#### `app/modules/datasources/drivers/mssql_driver.py`

**Role:** Adapter for `pyodbc` (MS SQL Server).  
`pyodbc` is synchronous, so the actual connection logic runs in `asyncio.to_thread()` to avoid blocking FastAPI's event loop. Handles three auth methods: password (SQL Auth), Windows NTLM, and Azure AD (token encoded as UTF-16-LE struct via `SQL_COPT_SS_ACCESS_TOKEN`). Detects the installed ODBC driver version automatically via `pyodbc.drivers()`.

> **System requirement:** Microsoft ODBC Driver 17 or 18 for SQL Server must be installed on the backend host OS. See [Microsoft's installation guide](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server).

**Code:**
```Python
# app/modules/datasources/drivers/mssql_driver.py
#
# PURPOSE:
#   Wraps pyodbc to test an MS SQL Server connection.
#   pyodbc is synchronous — wrapped in asyncio.to_thread() so it does not
#   block FastAPI's async event loop.
#
# LIBRARY: pyodbc (pip install pyodbc)
#
# SYSTEM REQUIREMENT:
#   Microsoft ODBC Driver for SQL Server must be installed on the host OS.
#   Download from:
#     https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
#   On Ubuntu/Debian:
#     curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
#     apt-get install msodbcsql18
#
# WINDOWS AUTH NOTE:
#   NTLM Windows Authentication (Trusted_Connection=yes) only works when the
#   Python process runs on a Windows host joined to the same Active Directory domain,
#   OR on Linux with proper Kerberos/krb5 configuration (complex). If the server
#   is Linux-based, flag Windows Auth as requiring additional setup.
#
# AZURE AD TOKEN AUTH:
#   Uses SQL_COPT_SS_ACCESS_TOKEN — the official Microsoft method for passing a
#   pre-acquired OAuth2 token to pyodbc. The token must be encoded as UTF-16-LE
#   and wrapped in a struct. This is not obvious from pyodbc's docs — see:
#     https://docs.microsoft.com/en-us/sql/connect/odbc/using-azure-active-directory
#
# TLS NOTE:
#   MSSQL TLS is controlled by two connection string parameters:
#     Encrypt=yes|no
#     TrustServerCertificate=yes|no
#   Custom CA certs with MSSQL ODBC are managed at the OS level (certificate store),
#   not via a file path in the connection string. For prod deployments, install
#   the CA cert into the system's trusted store.

import asyncio
import struct
import time
from typing import Optional
import pyodbc


def _get_odbc_driver() -> str:
    """
    Returns the first available Microsoft ODBC Driver for SQL Server.
    Checks in order of preference (newest first).

    Raises:
        RuntimeError: If no Microsoft ODBC driver is found
    """
    available = pyodbc.drivers()
    for preferred in [
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server",
        "ODBC Driver 13 for SQL Server",
    ]:
        if preferred in available:
            return preferred

    raise RuntimeError(
        "No Microsoft ODBC Driver for SQL Server found on this host. "
        "Install from: https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server"
    )


def _sync_test_mssql(config: dict) -> dict:
    """
    Synchronous MSSQL connection test.
    Called via asyncio.to_thread() — must NOT use async/await.

    This is a separate function (not a nested lambda) because
    asyncio.to_thread() requires a plain callable.
    """
    start       = int(time.time() * 1000)
    host        = config["host"]
    port        = int(config["port"])
    database    = config["database"]
    auth_method = config["auth_method"]
    credentials = config["credentials"]
    tls         = config.get("tls") or {}

    try:
        driver = _get_odbc_driver()
    except RuntimeError as exc:
        return {
            "success":    False,
            "latency_ms": 0,
            "raw_error":  exc,
        }

    # Build base connection string parts
    # `Connection Timeout=10` is in seconds
    conn_parts = [
        f"DRIVER={{{driver}}}",
        f"SERVER={host},{port}",
        f"DATABASE={database}",
        "Connection Timeout=10",
    ]

    # TLS / Encryption
    if tls.get("enabled"):
        conn_parts.append("Encrypt=yes")
        # TrustServerCertificate=yes means we do NOT verify the server cert
        # (inverse of our verify_server_cert flag)
        trust = "no" if tls.get("verify_server_cert", True) else "yes"
        conn_parts.append(f"TrustServerCertificate={trust}")
    else:
        conn_parts.append("Encrypt=no")

    # Auth-method-specific additions
    if auth_method == "password":
        conn_parts.append(f"UID={credentials['username']}")
        conn_parts.append(f"PWD={credentials['password']}")

    elif auth_method == "windows":
        # NTLM / Windows Integrated Auth
        conn_parts.append("Trusted_Connection=yes")
        # Optional: explicit domain\username override
        if credentials.get("domain") and credentials.get("username"):
            conn_parts.append(f"UID={credentials['domain']}\\{credentials['username']}")
            if credentials.get("password"):
                conn_parts.append(f"PWD={credentials['password']}")

    elif auth_method == "azure_ad":
        # Azure AD token auth is handled via attrs_before — not in the conn string.
        # The conn string still needs Encrypt=yes for Azure AD to work.
        if not tls.get("enabled"):
            # Azure AD requires encryption — force it on
            conn_parts.append("Encrypt=yes")
            conn_parts.append("TrustServerCertificate=no")

    conn_str = ";".join(conn_parts)
    conn     = None

    try:
        if auth_method == "azure_ad":
            # Azure AD access token must be encoded as UTF-16-LE and packed in a struct.
            # SQL_COPT_SS_ACCESS_TOKEN = 1256 is a pyodbc connection attribute constant.
            # Reference: https://docs.microsoft.com/en-us/sql/connect/odbc/using-azure-active-directory
            SQL_COPT_SS_ACCESS_TOKEN = 1256
            token         = credentials["access_token"].encode("utf-16-le")
            token_struct  = struct.pack(f"<I{len(token)}s", len(token), token)
            conn = pyodbc.connect(conn_str, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct})
        else:
            conn = pyodbc.connect(conn_str)

        cursor = conn.cursor()
        cursor.execute("SELECT 1 AS connected")
        cursor.fetchone()
        cursor.close()

        return {"success": True, "latency_ms": int(time.time() * 1000) - start}

    except Exception as exc:
        return {
            "success":    False,
            "latency_ms": int(time.time() * 1000) - start,
            "raw_error":  exc,
        }

    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


async def test_mssql_connection(config: dict) -> dict:
    """
    Async wrapper for the synchronous pyodbc test.
    asyncio.to_thread() runs the sync function in a thread pool executor,
    preventing it from blocking the FastAPI event loop.

    Args:
        config: Normalised connection config dict

    Returns:
        {"success": bool, "latency_ms": int, "raw_error"?: Exception}
    """
    # asyncio.to_thread is available in Python 3.9+
    # It's equivalent to loop.run_in_executor(None, fn, *args) but cleaner
    return await asyncio.to_thread(_sync_test_mssql, config)
```
---

#### `app/modules/datasources/drivers/oracle_driver.py`

**Role:** Adapter for `python-oracledb` (Oracle 12c+).  
Runs in **Thin Mode** by default (no Oracle Client libraries needed). Builds the DSN/connect string in three formats: Easy Connect (service name), SID legacy format, or TCPS (Oracle SSL). Supports password auth and Oracle Wallet in Thin Mode. Kerberos requires Thick Mode — the driver will return a classifiable `UNSUPPORTED_CONFIG` error if attempted in Thin Mode.

> **Note on Kerberos + Thick Mode:** Call `oracledb.init_oracle_client(lib_dir=...)` in `main.py` before any connections are made if Thick Mode is needed.

**Code:**
```Python
# app/modules/datasources/drivers/oracle_driver.py
#
# PURPOSE:
#   Wraps python-oracledb to test Oracle 12c+ connections.
#   Uses the async API (oracledb.connect_async) available in Thin Mode.
#
# LIBRARY: python-oracledb (pip install python-oracledb)
#   python-oracledb is the successor to cx_Oracle.
#
# THIN vs THICK MODE:
#   Thin Mode (default in v1.0+):
#     - No Oracle Client libraries required — works out of the box.
#     - Supports: password auth, Oracle Wallet (for SSL + password replacement),
#                 basic SSL/TCPS, async API.
#     - Does NOT support: Kerberos (requires Thick Mode + krb5 system libraries).
#
#   Thick Mode:
#     - Call oracledb.init_oracle_client(lib_dir="/path/to/instantclient")
#       BEFORE any connections. This is a one-time call per process.
#     - Required for: Kerberos, DRCP, advanced Oracle features.
#     - NOT called here — if Kerberos is needed, it must be initialised at
#       app startup (in main.py) before any requests are handled.
#
# CONNECT STRING FORMATS:
#   Service Name (12c+ recommended): "host:port/service_name"
#   SID (legacy):  "(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=h)(PORT=p))(CONNECT_DATA=(SID=s)))"
#   TCPS/SSL:      "(DESCRIPTION=(ADDRESS=(PROTOCOL=TCPS)(HOST=h)(PORT=p))...)"
#
# TIMEOUT:
#   tcp_connect_timeout is in SECONDS (not milliseconds).

import time
import oracledb


def _build_connect_string(config: dict) -> str:
    """
    Builds the Oracle DSN/connect string based on connection type and TLS config.

    Args:
        config: Datasource config dict

    Returns:
        Oracle connect string (Easy Connect, SID, or TCPS format)
    """
    host                   = config["host"]
    port                   = int(config["port"])
    database               = config["database"]   # SID or Service Name
    oracle_connection_type = config.get("oracle_connection_type", "service_name")
    tls                    = config.get("tls") or {}

    if tls.get("enabled"):
        # TCPS (Oracle SSL) — must use PROTOCOL=TCPS in the address
        # SSL_SERVER_DN_MATCH controls server certificate verification
        dn_match = "YES" if tls.get("verify_server_cert", True) else "NO"
        return (
            f"(DESCRIPTION="
            f"(ADDRESS=(PROTOCOL=TCPS)(HOST={host})(PORT={port}))"
            f"(CONNECT_DATA=(SERVICE_NAME={database}))"
            f"(SECURITY=(SSL_SERVER_DN_MATCH={dn_match}))"
            f")"
        )

    if oracle_connection_type == "sid":
        # Legacy SID format — still required for some older Oracle 11g/12c setups
        return (
            f"(DESCRIPTION="
            f"(ADDRESS=(PROTOCOL=TCP)(HOST={host})(PORT={port}))"
            f"(CONNECT_DATA=(SID={database}))"
            f")"
        )

    # Service Name format — recommended for Oracle 12c+
    # Easy Connect string: host:port/service_name
    return f"{host}:{port}/{database}"


async def test_oracle_connection(config: dict) -> dict:
    """
    Tests an Oracle database connection using python-oracledb's async API.
    Non-destructive — only a SELECT 1 FROM DUAL query is executed.

    Args:
        config: Normalised connection config dict with keys:
            host, port, database, oracle_connection_type,
            auth_method, credentials, tls (optional)

    Returns:
        {"success": bool, "latency_ms": int, "raw_error"?: Exception}
    """
    auth_method  = config["auth_method"]
    credentials  = config["credentials"]
    tls          = config.get("tls") or {}
    connect_string = _build_connect_string(config)

    start      = int(time.time() * 1000)
    connection = None

    try:
        if auth_method == "password":
            connection = await oracledb.connect_async(
                user              = credentials["username"],
                password          = credentials["password"],
                dsn               = connect_string,
                tcp_connect_timeout = 10,  # seconds
            )

        elif auth_method == "wallet":
            # Oracle Wallet: wallet_location is the server-side directory path
            # containing cwallet.sso (auto-login) or ewallet.p12 (password-protected).
            # wallet_password is only needed for ewallet.p12.
            connection = await oracledb.connect_async(
                dsn                 = connect_string,
                wallet_location     = credentials["wallet_location"],
                wallet_password     = credentials.get("wallet_password"),
                # Some wallet configurations also require an explicit username
                user                = credentials.get("username") or None,
                tcp_connect_timeout = 10,
            )

        elif auth_method == "kerberos":
            # Kerberos requires Thick Mode. In Thin Mode, python-oracledb will
            # raise an error containing "not supported in thin mode" — which
            # connection_tester.py classifies as UNSUPPORTED_CONFIG.
            # To enable Kerberos:
            #   1. Call oracledb.init_oracle_client(lib_dir=...) in main.py at startup
            #   2. Ensure krb5 system libraries are installed on the host
            #   3. Ensure `kinit` has a valid TGT for the principal
            connection = await oracledb.connect_async(
                user                = f"/{credentials['principal']}",
                dsn                 = connect_string,
                externalauth        = True,
                tcp_connect_timeout = 10,
            )

        else:
            raise ValueError(f"Unsupported Oracle auth method: {auth_method}")

        # DUAL is Oracle's built-in single-row, single-column table —
        # the canonical Oracle equivalent of PostgreSQL's `SELECT 1`
        cursor = connection.cursor()
        try:
            await cursor.execute("SELECT 1 FROM DUAL")
            await cursor.fetchone()
        finally:
            cursor.close()

        return {"success": True, "latency_ms": int(time.time() * 1000) - start}

    except Exception as exc:
        return {
            "success":    False,
            "latency_ms": int(time.time() * 1000) - start,
            "raw_error":  exc,
        }

    finally:
        if connection:
            try:
                await connection.close()
            except Exception:
                pass  # Ignore cleanup errors
```
---

#### `app/modules/datasources/service.py`

**Role:** Business logic layer.  
Three public functions: `test_datasource_connection()` (delegates to tester, no DB writes), `create_datasource()` (encrypts credentials, writes to DB, checks for duplicate names), `list_datasources()` (tenant-scoped query, credentials always stripped). The `_mask_sensitive_fields()` private function is the gatekeeper — it is the only path from a DB record to an API response, and it always removes `encrypted_credentials` and cert paths.

**Code:**
```Python
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
```
---

#### `app/modules/datasources/router.py`

**Role:** HTTP layer — FastAPI APIRouter with four endpoints.  
Handles request parsing, calls the service layer, and shapes responses. Also contains the secure file upload handler (using FastAPI's `UploadFile` — no separate middleware needed). The `get_current_user` dependency is a placeholder that should be replaced in M10.

| Method | Path      | Description                                              |
| ------ | --------- | -------------------------------------------------------- |
| `POST` | `/test`   | Test connection without saving. Always HTTP 200.         |
| `POST` | `/upload` | Upload TLS cert, Oracle Wallet, or Kerberos keytab.      |
| `POST` | `/`       | Create and save a datasource with encrypted credentials. |
| `GET`  | `/`       | List all datasources for the current tenant.             |
**Code:**
```Python
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
```
---

### 3.2 Frontend Modules

```
frontend/src/features/data-sources/
├── constants/engines.js
├── api/datasource.api.js
├── hooks/
│   ├── useDataSourceForm.js
│   └── useConnectionTest.js
├── components/
│   ├── EngineSelector.jsx
│   ├── ConnectionDetailsForm.jsx
│   ├── AuthConfigForm.jsx
│   ├── TLSConfigForm.jsx
│   └── TestConnectionPanel.jsx
└── pages/
    ├── AddDataSourcePage.jsx
    └── DataSourceListPage.jsx
```

---

#### `constants/engines.js`

Frontend mirror of `engines_config.py`. Drives engine card rendering, port auto-fill, auth method tab filtering, and TLS label/mode options. **This file and the backend config must stay in sync.** Adding a new engine requires updating both files.

**Code:**
```javascript

// src/features/data-sources/constants/engines.js
//
// PURPOSE:
//   Metadata and capabilities configuration for each supported database engine.
//   Used by the frontend to render appropriate form fields, set default ports,
//   and show valid authentication methods.

export const ENGINES = {
  postgresql: {
    label: "PostgreSQL",
    defaultPort: 5432,
    hasConnectionTypeToggle: false,
    authMethods: [
      { value: "password", label: "Username & Password" },
      { value: "ldap", label: "LDAP" }
    ],
    tls: {
      defaultMode: "require",
      modes: [
        { value: "disable", label: "Disable" },
        { value: "allow", label: "Allow" },
        { value: "prefer", label: "Prefer" },
        { value: "require", label: "Require" },
        { value: "verify-ca", label: "Verify CA" },
        { value: "verify-full", label: "Verify Full" }
      ]
    }
  },
  oracle: {
    label: "Oracle 12c+",
    defaultPort: 1521,
    hasConnectionTypeToggle: true,
    authMethods: [
      { value: "password", label: "Username & Password" },
      { value: "wallet", label: "Oracle Wallet" },
      { value: "kerberos", label: "Kerberos" }
    ],
    tls: {
      defaultMode: "ssl",
      modes: [
        { value: "ssl", label: "SSL (TCPS)" }
      ]
    }
  },
  mssql: {
    label: "MS SQL Server",
    defaultPort: 1433,
    hasConnectionTypeToggle: false,
    authMethods: [
      { value: "password", label: "Username & Password" },
      { value: "windows", label: "Windows Authentication" },
      { value: "azure_ad", label: "Azure Active Directory" }
    ],
    tls: {
      defaultMode: "encrypt",
      modes: [
        { value: "encrypt", label: "Encrypt (SSL/TLS)" }
      ]
    }
  }
};
```
---
#### `api/datasource.api.js`

All `fetch()` calls to the backend in one place. Components never call `fetch()` directly. Handles file uploads via `FormData` (no `Content-Type` header — the browser sets the multipart boundary automatically).

**Code:**
```javascript

// src/features/data-sources/api/datasource.api.js
//
// PURPOSE:
//   All fetch() calls to the datasource backend API, in one place.
//   Components and hooks import from here — never call fetch() directly.

const BASE = "/api/v1/datasources";

/**
 * Uploads a single secure file (TLS cert, Oracle Wallet, Kerberos keytab).
 * Returns the server-side path to embed in the datasource payload.
 *
 * @param {File}   file - The File object from a file input
 * @param {string} type - 'ca_cert' | 'client_cert' | 'client_key' | 'wallet' | 'keytab'
 * @returns {Promise<{ path: string, filename: string }>}
 */
export async function uploadSecureFile(file, type) {
  const form = new FormData();
  form.append("file", file);
  form.append("type", type);

  const res = await fetch(`${BASE}/upload`, {
    method: "POST",
    credentials: "include", // send session cookie
    body: form,
    // Don't set Content-Type — the browser sets it automatically with boundary for multipart
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "File upload failed");
  }

  return res.json();
}

/**
 * Tests a database connection.
 * Does NOT save anything — purely a validation call.
 *
 * @param {Object} payload - Full datasource config with plaintext credentials
 * @returns {Promise<{ success: boolean, latencyMs: number, category?: string, message?: string }>}
 */
export async function testDatasourceConnection(payload) {
  const res = await fetch(`${BASE}/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Test request failed");
  }

  return res.json();
}

/**
 * Creates and saves a new datasource.
 * Call only after a successful test.
 *
 * @param {Object} payload - Full datasource config
 * @returns {Promise<Object>} The saved datasource record (credentials masked)
 */
export async function createDatasource(payload) {
  const res = await fetch(BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Failed to create data source");
  }

  return res.json();
}

/**
 * Fetches all datasources for the current tenant.
 *
 * @returns {Promise<Array>}
 */
export async function listDatasources() {
  const res = await fetch(BASE, {
    method: "GET",
    credentials: "include",
  });

  if (!res.ok) throw new Error("Failed to fetch data sources");

  const { data } = await res.json();
  return data;
}
```
---
#### `hooks/useDataSourceForm.js`

Central form state for all 5 wizard steps. `selectEngine()` resets all downstream state when the engine changes. `setAuthMethod()` resets only credentials, preserving connection fields (per US 107148 acceptance criteria). `buildPayload()` assembles the complete JSON body for the API.

**Code:**
```javascript

// src/features/data-sources/hooks/useDataSourceForm.js
//
// PURPOSE:
//   Manages all wizard form state in a single hook.
//   The wizard page (AddDataSourcePage) uses this to read state
//   and pass the right props down to each step component.
//
// STATE SLICES:
//   engine     → which DB type was selected (step 0)
//   connection → host, port, database, name (step 1)
//   auth       → method + credentials (step 2)
//   tls        → enabled, mode, certs (step 3)
//
// KEY DESIGN DECISIONS:
//   1. selectEngine() resets ALL downstream state — changing the engine
//      invalidates auth method choices and TLS labels.
//   2. setAuthMethod() resets ONLY credentials — preserves connection fields.
//      This matches the acceptance criteria in US 107148.
//   3. buildPayload() produces the exact shape the backend expects.

import { useState, useCallback } from "react";
import { ENGINES } from "../constants/engines";

export function useDataSourceForm() {
  const [engine, setEngine] = useState(null);
  const [connection, setConnection] = useState(initialConnection());
  const [auth, setAuth] = useState(initialAuth());
  const [tls, setTls] = useState(initialTls());

  /**
   * Selects an engine and resets all other state to engine-appropriate defaults.
   * Called when the user clicks an engine card in step 0.
   */
  const selectEngine = useCallback((engineKey) => {
    const cfg = ENGINES[engineKey];
    if (!cfg) return;

    setEngine(engineKey);

    // Pre-fill default port — common UX pattern that saves the user a step
    setConnection({
      ...initialConnection(),
      port: cfg.defaultPort,
      oracleConnectionType: cfg.hasConnectionTypeToggle
        ? "service_name"
        : undefined,
    });

    // Default to the first auth method for this engine
    setAuth({
      method: cfg.authMethods[0]?.value || "",
      credentials: {},
    });

    // TLS off by default; pre-load the engine's default mode
    setTls({
      ...initialTls(),
      mode: cfg.tls.defaultMode || "",
    });
  }, []);

  /** Updates a single connection field (host, port, name, database, oracleConnectionType) */
  const updateConnection = useCallback((field, value) => {
    setConnection((prev) => ({ ...prev, [field]: value }));
  }, []);

  /**
   * Switches auth method and clears only the credential fields.
   * Connection fields are intentionally preserved.
   */
  const setAuthMethod = useCallback((method) => {
    setAuth({ method, credentials: {} });
  }, []);

  /** Updates a single credential field */
  const updateCredential = useCallback((field, value) => {
    setAuth((prev) => ({
      ...prev,
      credentials: { ...prev.credentials, [field]: value },
    }));
  }, []);

  /** Toggles TLS on/off; clears file-related fields when disabled */
  const toggleTls = useCallback((enabled) => {
    setTls((prev) => ({
      ...prev,
      enabled,
      ...(enabled ? {} : { caCert: null, clientCert: null, clientKey: null }),
    }));
  }, []);

  /** Updates a single TLS field */
  const updateTls = useCallback((field, value) => {
    setTls((prev) => ({ ...prev, [field]: value }));
  }, []);

  /**
   * Builds the complete payload for the /test or POST / API call.
   * File objects (certs, wallets) are not included here —
   * AddDataSourcePage.jsx uploads them first and substitutes path strings.
   */
  const buildPayload = useCallback(
    () => ({
      engine,
      name: connection.name,
      host: connection.host,
      port: connection.port,
      database: connection.database,
      oracle_connection_type: connection.oracleConnectionType,
      auth_method: auth.method,
      credentials: auth.credentials,
      tls: {
        enabled: tls.enabled,
        verify_server_cert: tls.verifyServerCert,
        mode: tls.mode,
        ca_cert_path: tls.caCertPath, // populated after upload
        client_cert_path: tls.clientCertPath,
        client_key_path: tls.clientKeyPath,
      },
    }),
    [engine, connection, auth, tls],
  );

  return {
    // State (read-only from consumer's perspective)
    engine,
    connection,
    auth,
    tls,
    // Actions
    selectEngine,
    updateConnection,
    setAuthMethod,
    updateCredential,
    toggleTls,
    updateTls,
    buildPayload,
  };
}

// --- Default state factories ---
// Functions (not constants) so each call gets a fresh object (no shared reference issues)

function initialConnection() {
  return {
    name: "",
    host: "",
    port: "",
    database: "",
    oracleConnectionType: "service_name",
  };
}

function initialAuth() {
  return { method: "", credentials: {} };
}

function initialTls() {
  return {
    enabled: false,
    verifyServerCert: true,
    mode: "",
    caCert: null,
    clientCert: null,
    clientKey: null,
    caCertPath: null,
    clientCertPath: null,
    clientKeyPath: null,
  };
}
```
---
#### `hooks/useConnectionTest.js`

State machine for the test flow: `idle → testing → success | failed`. `resetTest()` is called inside every `onChange` handler in the wizard so that editing any field after a successful test re-disables the Save button.

**Code:**
```javascript

// src/features/data-sources/hooks/useConnectionTest.js
//
// PURPOSE:
//   Manages the state machine for the "Test Connection" flow.
//   Four states: idle → testing → success | failed
//
// IMPORTANT: resetTest() must be called whenever a form field changes AFTER a test.
//   This re-disables the Save button — the user must re-test after any edit.
//   The wizard calls resetTest() inside every onChange handler.

import { useState, useCallback } from "react";
import { testDatasourceConnection } from "../api/datasource.api";

export function useConnectionTest() {
  // 'idle' | 'testing' | 'success' | 'failed'
  const [status, setStatus] = useState("idle");
  // null, or { success, latencyMs, category?, message? }
  const [result, setResult] = useState(null);

  /**
   * Executes the connection test.
   * The payload should be the output of useDataSourceForm's buildPayload(),
   * with any file objects already replaced by server-side paths.
   *
   * @param {Object} payload - Complete datasource config (no File objects)
   */
  const runTest = useCallback(async (payload) => {
    setStatus("testing");
    setResult(null);

    try {
      const data = await testDatasourceConnection(payload);
      setResult(data);
      setStatus(data.success ? "success" : "failed");
    } catch (networkErr) {
      // This path is hit when the InsightX server itself is unreachable,
      // not when the target database is unreachable.
      setResult({
        success: false,
        category: "NETWORK_ERROR",
        message: "Could not reach the InsightX server. Check your network.",
      });
      setStatus("failed");
    }
  }, []);

  /**
   * Resets the test state back to idle.
   * Call this whenever a form field changes after a test has run.
   * This forces re-testing before saving.
   */
  const resetTest = useCallback(() => {
    setStatus("idle");
    setResult(null);
  }, []);

  return {
    status,
    result,
    isTesting: status === "testing",
    isSuccess: status === "success",
    isFailed: status === "failed",
    // canSave is the gatekeeper — Save button only works after a successful test
    canSave: status === "success",
    runTest,
    resetTest,
  };
}
```
---
#### `components/EngineSelector.jsx`

Step 0. Clickable cards, one per engine. Calls `selectEngine()` on click.

**Code:**
```javascript

import React from "react";
import { ENGINES } from "../constants/engines";

function EngineSelector({ selected, onSelect }) {
  const engines = [
    { key: "postgresql", icon: "🐘" },
    { key: "oracle", icon: "🦴" },
    { key: "mssql", icon: "⚙️" },
  ];

  return (
    <div className="engine-selector">
      <h2>Select Database Engine</h2>
      <p style={{ color: "var(--color-text-muted)", marginBottom: "var(--space-lg)" }}>
        Choose the type of database you want to connect to.
      </p>
      <div className="engine-grid">
        {engines.map(({ key, icon }) => {
          const config = ENGINES[key];
          return (
            <button
              key={key}
              className={`engine-card ${selected === key ? "engine-card--selected" : ""}`}
              onClick={() => onSelect(key)}
              type="button"
            >
              <div className="engine-card__icon">{icon}</div>
              <div className="engine-card__label">{config.label}</div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default EngineSelector;
```
---
#### `components/ConnectionDetailsForm.jsx`

Step 1. Host, port, database name, connection name. Port auto-fills from `engines.js`. Shows Oracle SID/Service Name toggle when engine is Oracle.

**Code:**
```javascript

import React from "react";
import { ENGINES } from "../constants/engines";

function ConnectionDetailsForm({ engine, values, onChange }) {
  const config = ENGINES[engine] || {};

  return (
    <div>
      <h2>Connection Details</h2>
      <p style={{ color: "var(--color-text-muted)", marginBottom: "var(--space-lg)" }}>
        Enter the connection information for your {config.label} database.
      </p>

      <form>
        {/* Connection Name */}
        <div className="form-field">
          <label htmlFor="name">Connection Name</label>
          <input
            id="name"
            type="text"
            placeholder="e.g., Production Warehouse"
            value={values.name || ""}
            onChange={(e) => onChange("name", e.target.value)}
          />
          <div className="field-hint">A friendly name for this connection</div>
        </div>

        {/* Host */}
        <div className="form-field">
          <label htmlFor="host">Host</label>
          <input
            id="host"
            type="text"
            placeholder="e.g., db.example.com or 192.168.1.100"
            value={values.host || ""}
            onChange={(e) => onChange("host", e.target.value)}
          />
          <div className="field-hint">Hostname or IP address</div>
        </div>

        {/* Port */}
        <div className="form-field">
          <label htmlFor="port">Port</label>
          <input
            id="port"
            type="number"
            placeholder={`Default: ${config.defaultPort || 5432}`}
            value={values.port || ""}
            onChange={(e) => onChange("port", parseInt(e.target.value, 10) || "")}
          />
          <div className="field-hint">
            Default: {config.defaultPort || "see your DB documentation"}
          </div>
        </div>

        {/* Database / Service Name */}
        <div className="form-field">
          <label htmlFor="database">
            {engine === "oracle" ? "Service Name / SID" : "Database Name"}
          </label>
          <input
            id="database"
            type="text"
            placeholder={engine === "oracle" ? "e.g., ORCL or FREE" : "e.g., postgres"}
            value={values.database || ""}
            onChange={(e) => onChange("database", e.target.value)}
          />
        </div>

        {/* Oracle Connection Type Toggle (SID vs Service Name) */}
        {config.hasConnectionTypeToggle && (
          <div className="form-field">
            <label>Connection Type</label>
            <div className="radio-group">
              <label className="radio-label">
                <input
                  type="radio"
                  name="connectionType"
                  value="service_name"
                  checked={values.oracleConnectionType === "service_name"}
                  onChange={(e) => onChange("oracleConnectionType", e.target.value)}
                />
                Service Name
              </label>
              <label className="radio-label">
                <input
                  type="radio"
                  name="connectionType"
                  value="sid"
                  checked={values.oracleConnectionType === "sid"}
                  onChange={(e) => onChange("oracleConnectionType", e.target.value)}
                />
                SID
              </label>
            </div>
          </div>
        )}
      </form>
    </div>
  );
}

export default ConnectionDetailsForm;
```
---
#### `components/AuthConfigForm.jsx`

Step 2. Auth method tabs (filtered by engine) + the corresponding credential sub-form. Switching the tab calls `setAuthMethod()`, which resets only credential fields. Sub-forms: `PasswordForm`, `OracleWalletForm`, `KerberosForm`, `WindowsAuthForm`, `AzureADForm`.

**Code:**
```javascript

import React from "react";
import { ENGINES } from "../constants/engines";

function AuthConfigForm({
  engine,
  method,
  credentials,
  onMethodChange,
  onCredentialChange,
}) {
  const config = ENGINES[engine] || {};
  const authMethods = config.authMethods || [];

  return (
    <div className="auth-form">
      <h2>Authentication</h2>
      <p style={{ color: "var(--color-text-muted)", marginBottom: "var(--space-lg)" }}>
        Choose an authentication method and provide the necessary credentials.
      </p>

      {/* Auth method tabs */}
      <div className="auth-method-tabs">
        {authMethods.map((m) => (
          <button
            key={m.value}
            type="button"
            className={`auth-tab ${method === m.value ? "auth-tab--active" : ""}`}
            onClick={() => onMethodChange(m.value)}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Credential forms per auth method */}
      <div className="auth-credentials">
        {method === "password" && (
          <PasswordForm
            engine={engine}
            credentials={credentials}
            onCredentialChange={onCredentialChange}
          />
        )}
        {method === "wallet" && (
          <WalletForm
            credentials={credentials}
            onCredentialChange={onCredentialChange}
          />
        )}
        {method === "kerberos" && (
          <KerberosForm
            credentials={credentials}
            onCredentialChange={onCredentialChange}
          />
        )}
        {method === "windows" && (
          <WindowsAuthForm
            credentials={credentials}
            onCredentialChange={onCredentialChange}
          />
        )}
        {method === "azure_ad" && (
          <AzureADForm
            credentials={credentials}
            onCredentialChange={onCredentialChange}
          />
        )}
        {method === "ldap" && (
          <LDAPForm
            credentials={credentials}
            onCredentialChange={onCredentialChange}
          />
        )}
      </div>
    </div>
  );
}

function PasswordForm({ engine, credentials, onCredentialChange }) {
  return (
    <>
      {engine === "oracle" && (
        <div className="auth-note">
          💡 Oracle database login: enter your database username and password.
        </div>
      )}
      <div className="form-field">
        <label htmlFor="username">Username</label>
        <input
          id="username"
          type="text"
          placeholder="e.g., dbuser"
          value={credentials.username || ""}
          onChange={(e) => onCredentialChange("username", e.target.value)}
        />
      </div>
      <div className="form-field">
        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          placeholder="••••••••"
          value={credentials.password || ""}
          onChange={(e) => onCredentialChange("password", e.target.value)}
        />
      </div>
    </>
  );
}

function WalletForm({ credentials, onCredentialChange }) {
  return (
    <>
      <div className="auth-note">
        💡 Upload your Oracle Wallet file (.sso or .p12). Your database credentials
        will be securely encrypted and stored.
      </div>
      <div className="form-field">
        <label htmlFor="walletFile">Oracle Wallet File</label>
        <input
          id="walletFile"
          type="file"
          accept=".sso,.p12"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) {
              onCredentialChange("walletFile", file);
              onCredentialChange("walletFileName", file.name);
            }
          }}
        />
        <div className="field-hint">
          {credentials.walletFileName || "Select a .sso or .p12 wallet file"}
        </div>
      </div>
      <div className="form-field">
        <label htmlFor="walletPassword">Wallet Password</label>
        <input
          id="walletPassword"
          type="password"
          placeholder="••••••••"
          value={credentials.walletPassword || ""}
          onChange={(e) => onCredentialChange("walletPassword", e.target.value)}
        />
        <div className="field-hint">Leave empty if your wallet has no password</div>
      </div>
    </>
  );
}

function KerberosForm({ credentials, onCredentialChange }) {
  return (
    <>
      <div className="auth-note">
        💡 Kerberos authentication requires a keytab file and principal name.
      </div>
      <div className="form-field">
        <label htmlFor="keytabFile">Kerberos Keytab File</label>
        <input
          id="keytabFile"
          type="file"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) {
              onCredentialChange("keytabFile", file);
              onCredentialChange("keytabFileName", file.name);
            }
          }}
        />
        <div className="field-hint">
          {credentials.keytabFileName || "Select your keytab file"}
        </div>
      </div>
      <div className="form-field">
        <label htmlFor="principal">Principal</label>
        <input
          id="principal"
          type="text"
          placeholder="e.g., user@REALM.COM"
          value={credentials.principal || ""}
          onChange={(e) => onCredentialChange("principal", e.target.value)}
        />
        <div className="field-hint">Kerberos principal (user@REALM)</div>
      </div>
    </>
  );
}

function WindowsAuthForm({ credentials, onCredentialChange }) {
  return (
    <>
      <div className="auth-note">
        💡 Windows Integrated Authentication uses your system credentials. This only
        works when the backend is running on a Windows host in the same domain.
      </div>
      <div className="form-field">
        <label htmlFor="domain">Domain (optional)</label>
        <input
          id="domain"
          type="text"
          placeholder="e.g., CORP"
          value={credentials.domain || ""}
          onChange={(e) => onCredentialChange("domain", e.target.value)}
        />
        <div className="field-hint">Leave empty to use the local machine</div>
      </div>
    </>
  );
}

function AzureADForm({ credentials, onCredentialChange }) {
  return (
    <>
      <div className="auth-note">
        💡 Azure AD authentication requires you to log in with your Azure credentials.
      </div>
      <div className="form-field">
        <label htmlFor="tenantId">Tenant ID</label>
        <input
          id="tenantId"
          type="text"
          placeholder="e.g., xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
          value={credentials.tenantId || ""}
          onChange={(e) => onCredentialChange("tenantId", e.target.value)}
        />
      </div>
      <div className="form-field">
        <label htmlFor="clientId">Client ID</label>
        <input
          id="clientId"
          type="text"
          placeholder="e.g., xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
          value={credentials.clientId || ""}
          onChange={(e) => onCredentialChange("clientId", e.target.value)}
        />
      </div>
      <div className="form-field">
        <label htmlFor="clientSecret">Client Secret</label>
        <input
          id="clientSecret"
          type="password"
          placeholder="••••••••"
          value={credentials.clientSecret || ""}
          onChange={(e) => onCredentialChange("clientSecret", e.target.value)}
        />
      </div>
    </>
  );
}

function LDAPForm({ credentials, onCredentialChange }) {
  return (
    <>
      <div className="auth-note">
        💡 LDAP authentication: your credentials will be passed to the LDAP server.
      </div>
      <div className="form-field">
        <label htmlFor="username">Username</label>
        <input
          id="username"
          type="text"
          placeholder="e.g., john.doe"
          value={credentials.username || ""}
          onChange={(e) => onCredentialChange("username", e.target.value)}
        />
      </div>
      <div className="form-field">
        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          placeholder="••••••••"
          value={credentials.password || ""}
          onChange={(e) => onCredentialChange("password", e.target.value)}
        />
      </div>
    </>
  );
}

export default AuthConfigForm;
```
---
#### `components/TLSConfigForm.jsx`

Step 3. TLS toggle + conditional fields (CA cert upload, client cert/key for mTLS, verify checkbox with warning). Engine-aware labels: "SSL Mode" for PG, "Encrypt" for MSSQL, "SSL (TCPS)" for Oracle.

**Code:**
```javascript

import React from "react";
import { ENGINES } from "../constants/engines";

function TLSConfigForm({ engine, tls, onToggle, onChange }) {
  const config = ENGINES[engine] || {};
  const tlsModes = config.tls?.modes || [];

  return (
    <div className="tls-form">
      <h2>TLS / SSL Configuration</h2>
      <p style={{ color: "var(--color-text-muted)", marginBottom: "var(--space-lg)" }}>
        Encrypt your database connection and verify the server's certificate.
      </p>

      {/* TLS toggle */}
      <div className="form-field form-field--inline">
        <input
          id="tlsToggle"
          type="checkbox"
          checked={tls.enabled || false}
          onChange={(e) => onToggle(e.target.checked)}
        />
        <label htmlFor="tlsToggle" style={{ marginBottom: 0 }}>
          Enable TLS / SSL Encryption
          <span className="toggle-hint"> – recommended for production</span>
        </label>
      </div>

      {tls.enabled && (
        <>
          {/* TLS Mode */}
          {tlsModes.length > 0 && (
            <div className="form-field">
              <label htmlFor="tlsMode">
                {engine === "postgresql"
                  ? "SSL Mode"
                  : engine === "mssql"
                    ? "Encrypt"
                    : "SSL Mode"}
              </label>
              <select
                id="tlsMode"
                value={tls.mode || ""}
                onChange={(e) => onChange("mode", e.target.value)}
              >
                <option value="">Select mode…</option>
                {tlsModes.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Verify Server Certificate */}
          <div className="form-field form-field--inline">
            <input
              id="verifyCert"
              type="checkbox"
              checked={tls.verifyServerCert !== false}
              onChange={(e) => onChange("verifyServerCert", e.target.checked)}
            />
            <label htmlFor="verifyCert" style={{ marginBottom: 0 }}>
              Verify Server Certificate
            </label>
          </div>

          {!tls.verifyServerCert && (
            <div className="warning-banner">
              ⚠️ <strong>Security Risk:</strong> You are skipping certificate verification. This
              leaves your connection vulnerable to man-in-the-middle attacks. Only disable
              verification for testing with self-signed certificates — never in production.
            </div>
          )}

          {/* CA Certificate Upload */}
          {tls.verifyServerCert && (
            <div className="form-field">
              <label htmlFor="caCert">CA Certificate (optional)</label>
              <input
                id="caCert"
                type="file"
                accept=".pem,.crt,.cer"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) onChange("caCert", file);
                }}
              />
              <div className="field-hint">
                {tls.caCert?.name || "Upload a .pem or .crt file if using a custom CA"}
              </div>
            </div>
          )}

          {/* mTLS: Client Certificate and Key */}
          <div style={{ marginTop: "var(--space-lg)", paddingTop: "var(--space-lg)", borderTop: "1px solid var(--color-border)" }}>
            <h3>Mutual TLS (mTLS) – Optional</h3>
            <p style={{ color: "var(--color-text-muted)", fontSize: "0.85rem" }}>
              Upload client certificate and key for mutual TLS authentication.
            </p>

            <div className="form-field">
              <label htmlFor="clientCert">Client Certificate</label>
              <input
                id="clientCert"
                type="file"
                accept=".pem,.crt,.cer"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) onChange("clientCert", file);
                }}
              />
              <div className="field-hint">
                {tls.clientCert?.name || "Upload your client certificate (.pem or .crt)"}
              </div>
            </div>

            <div className="form-field">
              <label htmlFor="clientKey">Client Key</label>
              <input
                id="clientKey"
                type="file"
                accept=".pem,.key"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) onChange("clientKey", file);
                }}
              />
              <div className="field-hint">
                {tls.clientKey?.name || "Upload your private key (.pem or .key)"}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default TLSConfigForm;
```
---
#### `components/TestConnectionPanel.jsx`

Step 4. "Test Connection" button, spinner during test, result display (success with latency or failure with categorised error), and the Save button (disabled until test passes).

**Code:**
```javascript

// src/features/data-sources/components/TestConnectionPanel.jsx
//
// PURPOSE:
//   Renders the "Test Connection" button and its results.
//   This component is intentionally stateless — all state lives in useConnectionTest.
//
// ERROR CATEGORY DISPLAY:
//   Each category maps to an icon + plain-English label so users know what to fix.

import React from "react";

// Maps backend error category strings to human-readable labels with icons
const ERROR_LABELS = {
  AUTH_FAILED: { icon: "🔐", label: "Authentication Failed" },
  HOST_UNREACHABLE: { icon: "🌐", label: "Host Unreachable" },
  TLS_HANDSHAKE_FAILED: { icon: "🔒", label: "TLS Handshake Failed" },
  TIMEOUT: { icon: "⏱️", label: "Connection Timeout" },
  UNSUPPORTED_CONFIG: { icon: "⚙️", label: "Unsupported Configuration" },
  NETWORK_ERROR: { icon: "📡", label: "Network Error" },
  UNKNOWN: { icon: "⚠️", label: "Unknown Error" },
};

/**
 * @param {string}   status    - 'idle' | 'testing' | 'success' | 'failed'
 * @param {Object}   result    - { success, latencyMs, category?, message? } | null
 * @param {Function} onTest    - Called when "Test Connection" is clicked
 * @param {Function} onSave    - Called when "Save Data Source" is clicked
 * @param {boolean}  isSaving  - True while the save request is in flight
 */
function TestConnectionPanel({ status, result, onTest, onSave, isSaving }) {
  const isTesting = status === "testing";
  const canSave = status === "success";

  return (
    <div className="test-panel">
      <h3>Test Your Connection</h3>
      <p className="test-panel__hint">
        Run a connection test before saving. The test is non-destructive — only
        a <code>SELECT 1</code> query is executed.
      </p>

      {/* Test button */}
      <button
        type="button"
        className={`btn btn--test ${isTesting ? "btn--loading" : ""}`}
        onClick={onTest}
        disabled={isTesting}
      >
        {isTesting ? (
          <>
            <Spinner /> Testing...
          </>
        ) : (
          "⚡ Test Connection"
        )}
      </button>

      {/* Result area — only rendered after a test has run */}
      {result && (
        <div
          className={`test-result ${result.success ? "test-result--success" : "test-result--failed"}`}
        >
          {result.success ? (
            // Success
            <p>
              ✅ <strong>Connection successful</strong> — responded in{" "}
              {result.latencyMs}ms
            </p>
          ) : (
            // Failure — show category badge + actionable message
            <>
              <p className="test-result__category">
                {ERROR_LABELS[result.category]?.icon || "⚠️"}
                &nbsp;
                <strong>
                  {ERROR_LABELS[result.category]?.label || result.category}
                </strong>
              </p>
              <p className="test-result__message">{result.message}</p>
            </>
          )}
        </div>
      )}

      {/* Save button — disabled until test passes */}
      <button
        type="button"
        className="btn btn--primary"
        onClick={onSave}
        disabled={!canSave || isSaving}
        title={
          !canSave
            ? "A successful connection test is required before saving."
            : ""
        }
      >
        {isSaving ? (
          <>
            <Spinner /> Saving...
          </>
        ) : (
          "💾 Save Data Source"
        )}
      </button>
    </div>
  );
}

function Spinner() {
  return <span className="spinner" aria-hidden="true" />;
}

export default TestConnectionPanel;
```
---
#### `pages/AddDataSourcePage.jsx`

Wizard orchestrator. Manages the current step, calls `resolveFileUploads()` to upload File objects before the test payload is sent, and calls `createDatasource()` on save.

**Code:**
```javascript

// src/features/data-sources/pages/AddDataSourcePage.jsx
//
// PURPOSE:
//   The main wizard container. Orchestrates all 5 steps and coordinates
//   the form hook, test hook, file uploads, and the final save call.
//
// WIZARD STEPS:
//   0 - EngineSelector:       pick Oracle / PostgreSQL / MSSQL
//   1 - ConnectionDetailsForm: host, port, db name, connection name
//   2 - AuthConfigForm:        auth method + credentials
//   3 - TLSConfigForm:         TLS toggle + cert uploads
//   4 - TestConnectionPanel:   test the connection, then save
//
// FILE UPLOAD FLOW:
//   File inputs in AuthConfigForm and TLSConfigForm store File objects
//   in the form state. Before calling /test or POST /, this page uploads
//   each File to /api/v1/datasources/upload and replaces the File object
//   with the returned server path. This keeps the JSON payload clean.

import React, { useState } from "react";
import { useDataSourceForm } from "../hooks/useDataSourceForm";
import { useConnectionTest } from "../hooks/useConnectionTest";
import { uploadSecureFile, createDatasource } from "../api/datasource.api";
import EngineSelector from "../components/EngineSelector";
import ConnectionDetailsForm from "../components/ConnectionDetailsForm";
import AuthConfigForm from "../components/AuthConfigForm";
import TLSConfigForm from "../components/TLSConfigForm";
import TestConnectionPanel from "../components/TestConnectionPanel";

const STEPS = [
  { label: "Engine", icon: "🗄️" },
  { label: "Connection", icon: "🔌" },
  { label: "Auth", icon: "🔐" },
  { label: "TLS / SSL", icon: "🔒" },
  { label: "Test & Save", icon: "✅" },
];

/**
 * @param {Function} onSuccess - Called with the saved datasource on successful save
 */
function AddDataSourcePage({ onSuccess }) {
  const [step, setStep] = useState(0);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);

  const form = useDataSourceForm();
  const test = useConnectionTest();

  // ---- File upload helper ----

  /**
   * Uploads any File objects in the payload to the server,
   * returning an updated payload with File objects replaced by path strings.
   *
   * @param {Object} payload - buildPayload() output (may contain File objects)
   * @returns {Promise<Object>} Payload with File objects replaced by server paths
   */
  async function resolveFileUploads(payload) {
    // Work on a shallow copy — don't mutate the original
    const p = {
      ...payload,
      credentials: { ...payload.credentials },
      tls: { ...payload.tls },
    };

    // Oracle Wallet file
    if (p.credentials.walletFile instanceof File) {
      const { path } = await uploadSecureFile(
        p.credentials.walletFile,
        "wallet",
      );
      p.credentials.walletLocation = path;
      delete p.credentials.walletFile; // remove File object — not JSON-serialisable
      delete p.credentials.walletFileName;
    }

    // Kerberos keytab
    if (p.credentials.keytabFile instanceof File) {
      const { path } = await uploadSecureFile(
        p.credentials.keytabFile,
        "keytab",
      );
      p.credentials.keytabPath = path;
      delete p.credentials.keytabFile;
      delete p.credentials.keytabFileName;
    }

    // TLS CA cert
    if (p.tls.caCert instanceof File) {
      const { path } = await uploadSecureFile(p.tls.caCert, "ca_cert");
      p.tls.caCertPath = path;
      delete p.tls.caCert;
    }

    // mTLS client cert and key
    if (p.tls.clientCert instanceof File) {
      const { path } = await uploadSecureFile(p.tls.clientCert, "client_cert");
      p.tls.clientCertPath = path;
      delete p.tls.clientCert;
    }

    if (p.tls.clientKey instanceof File) {
      const { path } = await uploadSecureFile(p.tls.clientKey, "client_key");
      p.tls.clientKeyPath = path;
      delete p.tls.clientKey;
    }

    return p;
  }

  // ---- Wizard actions ----

  async function handleTest() {
    const payload = form.buildPayload();
    const resolvedPayload = await resolveFileUploads(payload);
    test.runTest(resolvedPayload);
  }

  async function handleSave() {
    if (!test.canSave) return;

    setIsSaving(true);
    setSaveError(null);

    try {
      const payload = form.buildPayload();
      const saved = await createDatasource(payload);
      if (onSuccess) onSuccess(saved);
    } catch (err) {
      setSaveError(err.message || "Save failed. Please try again.");
    } finally {
      setIsSaving(false);
    }
  }

  /**
   * Determines whether the "Next" button should be enabled for the current step.
   * Keeps validation light — just checks required fields are non-empty.
   */
  function canAdvance() {
    const { engine, connection, auth } = form;
    if (step === 0) return !!engine;
    if (step === 1)
      return !!(
        connection.name &&
        connection.host &&
        connection.port &&
        connection.database
      );
    if (step === 2) return !!auth.method;
    return true; // TLS and test steps are always advanceable
  }

  // ---- Render ----

  return (
    <div className="wizard-page">
      {/* Step progress indicator */}
      <StepIndicator steps={STEPS} current={step} />

      {/* Step content */}
      <div className="wizard-body">
        {step === 0 && (
          <EngineSelector
            selected={form.engine}
            onSelect={(key) => {
              form.selectEngine(key);
              test.resetTest();
            }}
          />
        )}

        {step === 1 && (
          <ConnectionDetailsForm
            engine={form.engine}
            values={form.connection}
            onChange={(f, v) => {
              form.updateConnection(f, v);
              test.resetTest();
            }}
          />
        )}

        {step === 2 && (
          <AuthConfigForm
            engine={form.engine}
            method={form.auth.method}
            credentials={form.auth.credentials}
            onMethodChange={(m) => {
              form.setAuthMethod(m);
              test.resetTest();
            }}
            onCredentialChange={(f, v) => {
              form.updateCredential(f, v);
              test.resetTest();
            }}
          />
        )}

        {step === 3 && (
          <TLSConfigForm
            engine={form.engine}
            tls={form.tls}
            onToggle={(v) => {
              form.toggleTls(v);
              test.resetTest();
            }}
            onChange={(f, v) => {
              form.updateTls(f, v);
              test.resetTest();
            }}
          />
        )}

        {step === 4 && (
          <TestConnectionPanel
            status={test.status}
            result={test.result}
            onTest={handleTest}
            onSave={handleSave}
            isSaving={isSaving}
          />
        )}

        {saveError && <p className="error-banner">{saveError}</p>}
      </div>

      {/* Navigation */}
      <div className="wizard-nav">
        {step > 0 && (
          <button type="button" onClick={() => setStep((s) => s - 1)}>
            ← Back
          </button>
        )}
        {step < 4 && (
          <button
            type="button"
            onClick={() => setStep((s) => s + 1)}
            disabled={!canAdvance()}
          >
            Next →
          </button>
        )}
      </div>
    </div>
  );
}

// Simple step progress indicator component
function StepIndicator({ steps, current }) {
  return (
    <ol className="step-indicator">
      {steps.map((step, i) => (
        <li
          key={i}
          className={`step-indicator__item ${i === current ? "active" : ""} ${i < current ? "done" : ""}`}
          aria-current={i === current ? "step" : undefined}
        >
          <span>{step.icon}</span>
          <span>{step.label}</span>
        </li>
      ))}
    </ol>
  );
}

export default AddDataSourcePage;
```
---

#### `pages/DataSourceListPage.jsx`

**Role:** Displays registered data sources.
Displays all registered data sources for the current tenant as cards showing engine, name, host, and last test status.

**Code:**
```javascript
// src/features/data-sources/pages/DataSourceListPage.jsx
//
// PURPOSE:
//   Displays all registered data sources for the current tenant.
//   Each source is shown as a card with engine, name, host, and last test status.
//   Contains an "Add New" button that navigates to the wizard page.
//
// DATA FLOW:
//   On mount → calls listDatasources() API → renders cards
//   On "Add New" click → navigates to /datasources/new (the wizard)

import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listDatasources } from "../api/datasource.api.js";
import { ENGINES } from "../constants/engines.js";

function DataSourceListPage() {
  const navigate = useNavigate();

  // Sources fetched from the backend
  const [sources, setSources] = useState([]);
  // Loading state — show spinner while fetching
  const [loading, setLoading] = useState(true);
  // Error state — show message if fetch fails
  const [error, setError] = useState(null);

  // Fetch data sources when the page mounts
  useEffect(() => {
    async function load() {
      try {
        const data = await listDatasources();
        setSources(data);
      } catch (err) {
        setError("Failed to load data sources. Is the backend running?");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []); // Empty array = run once on mount only

  return (
    <div className="datasource-list-page">
      {/* Page header with title and "Add New" button */}
      <div className="datasource-list-page__header">
        <div>
          <h2>Data Sources</h2>
          <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem" }}>
            Registered database connections available for querying.
          </p>
        </div>
        <button
          className="btn btn--primary"
          onClick={() => navigate("/datasources/new")}
        >
          + Add Data Source
        </button>
      </div>

      {/* Loading state */}
      {loading && <p className="loading-text">Loading data sources…</p>}

      {/* Error state */}
      {error && <p className="error-banner">{error}</p>}

      {/* Empty state — no sources registered yet */}
      {!loading && !error && sources.length === 0 && (
        <div className="empty-state">
          <div className="empty-state__icon">🗄️</div>
          <h3>No data sources yet</h3>
          <p style={{ marginBottom: "var(--space-lg)" }}>
            Connect your first database to start querying with InsightX.
          </p>
          <button
            className="btn btn--primary"
            onClick={() => navigate("/datasources/new")}
          >
            + Add Your First Data Source
          </button>
        </div>
      )}

      {/* Data source cards grid */}
      {!loading && !error && sources.length > 0 && (
        <div className="datasource-grid">
          {sources.map((source) => (
            <DataSourceCard key={source.id} source={source} />
          ))}
        </div>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   DataSourceCard
   Renders a single data source as a summary card.
   ───────────────────────────────────────────────────────────────────────────── */
function DataSourceCard({ source }) {
  // Look up engine metadata (icon, label) from the constants file
  const engineConfig = ENGINES[source.engine] || {};

  // Map last_test_status to a visual dot colour
  const statusDotClass =
    {
      success: "status-dot--success",
      failed: "status-dot--failed",
    }[source.last_test_status] || "status-dot--unknown";

  const statusLabel =
    {
      success: "Last test passed",
      failed: "Last test failed",
    }[source.last_test_status] || "Not tested";

  return (
    <div className="datasource-card">
      {/* Card header: engine icon + name + engine badge */}
      <div className="datasource-card__header">
        <span className="datasource-card__icon">
          {engineConfig.icon || "🗄️"}
        </span>
        <div>
          <div className="datasource-card__name">{source.name}</div>
          <span className="datasource-card__badge">
            {engineConfig.label || source.engine}
          </span>
        </div>
      </div>

      {/* Connection metadata */}
      <div className="datasource-card__meta">
        <div>
          🔌 {source.host}:{source.port}
        </div>
        <div>🗃️ {source.database_name}</div>
        <div>🔐 {source.auth_method}</div>
        <div>
          <span className={`status-dot ${statusDotClass}`} />
          {statusLabel}
        </div>
        {source.tls_enabled && <div>🔒 TLS enabled</div>}
      </div>
    </div>
  );
}

export default DataSourceListPage;
```

---
---

## 4. System Architecture

### Component Interaction Diagram

```
╔══════════════════════════════════════════════════════════════════════╗
║                         BROWSER (React 18)                           ║
║                                                                      ║
║  ┌────────────────────────────────────────────────────────────────┐  ║
║  │                  AddDataSourcePage (Wizard)                    │  ║
║  │                                                                │  ║
║  │  [Step 0]      [Step 1]      [Step 2]   [Step 3]  [Step 4]    │  ║
║  │  Engine   →  Connection  →    Auth   →  TLS/SSL → Test+Save   │  ║
║  │                                                                │  ║
║  │           useDataSourceForm()         useConnectionTest()      │  ║
║  └────────────────────────┬───────────────────────────────────────┘  ║
║                           │                                          ║
║  ┌────────────────────────▼───────────────────────────────────────┐  ║
║  │                   datasource.api.js                            │  ║
║  │   POST /test    POST /upload    POST /    GET /                 │  ║
║  └────────────────────────┬───────────────────────────────────────┘  ║
╚═══════════════════════════│══════════════════════════════════════════╝
                            │  HTTP/JSON  (port 3000 → proxy → 8000)
                            │
╔═══════════════════════════▼══════════════════════════════════════════╗
║                      FASTAPI BACKEND (port 8000)                     ║
║                                                                      ║
║  ┌─────────────────────────────────────────────────────────────┐     ║
║  │                        router.py                            │     ║
║  │  Pydantic validation → HTTPException → DI (Depends)         │     ║
║  └──────────────────────────┬──────────────────────────────────┘     ║
║                             │                                        ║
║  ┌──────────────────────────▼──────────────────────────────────┐     ║
║  │                        service.py                           │     ║
║  │  test_datasource_connection()   create_datasource()         │     ║
║  │  list_datasources()             _mask_sensitive_fields()    │     ║
║  └──────────┬──────────────────────────────┬────────────────────┘    ║
║             │                              │                         ║
║  ┌──────────▼────────────────┐   ┌─────────▼─────────────────┐      ║
║  │    connection_tester.py   │   │  credential_encryptor.py  │      ║
║  │  Strategy: driver_map     │   │  AES-256-GCM encrypt()    │      ║
║  │  asyncio.wait_for(10s)    │   │                 decrypt() │      ║
║  │  _classify_error()        │   └───────────────────────────┘      ║
║  └──────┬────────────────────┘                                       ║
║         │                                                            ║
║  ┌──────▼─────────────────────────────────────────────────┐         ║
║  │                    drivers/                             │         ║
║  │  postgres_driver.py    mssql_driver.py    oracle_driver.py │      ║
║  │  (asyncpg — async)     (pyodbc — thread)  (oracledb — async) │    ║
║  │       Adapter: all return {success, latency_ms, raw_error}   │    ║
║  └──────┬─────────────────────────────────────────────────┘         ║
╚═════════│════════════════════════════════════════════════════════════╝
          │
          │  Native DB protocols
          │  (TCP / TCPS / ODBC / Oracle Net)
          │
╔═════════▼════════════════════════════════════════════════════════════╗
║                        TARGET DATABASES                              ║
║                                                                      ║
║   ┌──────────────┐   ┌──────────────────┐   ┌───────────────────┐   ║
║   │  PostgreSQL  │   │   MS SQL Server  │   │   Oracle 12c+     │   ║
║   │              │   │                  │   │                   │   ║
║   │  asyncpg     │   │  pyodbc +        │   │  python-oracledb  │   ║
║   │  ssl.ctx     │   │  ODBC Driver 18  │   │  Thin Mode        │   ║
║   └──────────────┘   └──────────────────┘   └───────────────────┘   ║
╚══════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════╗
║                  INSIGHTX METADATA DATABASE                          ║
║                  (PostgreSQL — separate from target DBs)             ║
║                                                                      ║
║   Table: datasources                                                 ║
║   ├── Connection details        (plaintext — not sensitive)          ║
║   ├── encrypted_credentials     (AES-256-GCM — never returned)       ║
║   └── tls_*_cert_path           (server-side paths — never returned) ║
╚══════════════════════════════════════════════════════════════════════╝
```

### Request Lifecycle: "Test Connection" Button

```
1.  User fills wizard steps 0–3 and clicks "Test Connection" on step 4.

2.  AddDataSourcePage.jsx calls resolveFileUploads():
      - Any File objects (wallet, keytab, certs) are uploaded via POST /upload
      - The returned server-side paths replace the File objects in the payload

3.  useConnectionTest.runTest(payload) calls datasource.api.testDatasourceConnection()
      → POST /api/v1/datasources/test  (plaintext payload, no DB write)

4.  router.py:
      - FastAPI runs Pydantic validation on the request body (DatasourcePayload)
      - If validation fails → HTTP 422 (never reaches the service)
      - If valid → calls service.test_datasource_connection(payload)

5.  service.py calls connection_tester.test_connection(config)

6.  connection_tester.py:
      - Selects the driver from driver_map based on config["engine"]
      - asyncio.wait_for(driver_fn(config), timeout=10)

7.  driver (e.g., postgres_driver.py):
      - Builds ssl.SSLContext from TLS config
      - Calls asyncpg.connect(host, port, db, user, password, ssl=ctx, timeout=10)
      - Executes SELECT 1
      - Returns {success: True/False, latency_ms: N, raw_error?: e}

8.  connection_tester.py calls _classify_error() on failure:
      - Translates driver exception → {category, message}

9.  HTTP 200 always returned:
      - Success: {success: true, latency_ms: 240}
      - Failure: {success: false, category: "AUTH_FAILED", message: "..."}

10. Frontend:
      - Success → ✅ badge + latency + Save button enabled
      - Failure → ❌ badge + category label + message, Save button disabled
```

---

## 5. Prerequisites

### Backend

| Requirement           | Version  | Notes                                                                                                                              |
| --------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Python                | 3.11+    | 3.9+ minimum; 3.11 recommended                                                                                                     |
| PostgreSQL            | 13+      | InsightX metadata DB only                                                                                                          |
| Microsoft ODBC Driver | 17 or 18 | Required for MSSQL connections. [Download](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server) |
| Oracle Instant Client | Optional | Only if Kerberos auth (Thick Mode) is needed                                                                                       |

### Frontend

| Requirement | Version |
| ----------- | ------- |
| Node.js     | 18+     |
| npm         | 9+      |

---

## 6. Running the Application

### 6.1 Backend

```bash
# 1. Navigate to the backend directory
cd backend

# 2. Create and activate a Python virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# OR
.venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy the example environment file and fill in your values
cp .env.example .env
# Edit .env — see Section 7 for required variables

# 5. Create the secure uploads directory
mkdir -p /var/insightx/secure-uploads
# On Windows:
# mkdir C:\insightx\secure-uploads
# Then update SECURE_FILES_DIR in .env accordingly

# 6. Run the database migration against your InsightX metadata DB
psql -U your_user -d insightx_meta -f database/migrations/001_create_datasources.sql

# 7. Start the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# The API is now available at:
#   http://localhost:8000
#   Interactive docs: http://localhost:8000/docs
#   ReDoc: http://localhost:8000/redoc
```

---

### 6.2 Frontend

```bash
# 1. Navigate to the frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Copy the example environment file
cp .env.example .env.local
# Edit .env.local if needed (see Section 7)

# 4. Start the development server
npm run dev      # Vite
# OR
npm start        # Create React App
```

---

### 6.3 Frontend Proxy Setup (**Critical**)

> **This is the most common reason the frontend fails to reach the backend in development.**

The frontend API calls use relative URLs (`/api/v1/datasources`). In development, React runs on port 3000 and FastAPI on port 8000. Without a proxy, the browser sends API calls to `localhost:3000/api/...` which does not exist.

**If you are using Vite**, add this to `vite.config.js`:

```javascript
// vite.config.js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Forwards any request starting with /api to the FastAPI backend
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

**If you are using Create React App**, add one line to `package.json`:

```json
{
  "name": "insightx-frontend",
  "proxy": "http://localhost:8000",
  ...
}
```

After adding the proxy, restart the dev server. API calls to `/api/v1/datasources` will now be forwarded to FastAPI on port 8000.

---

## 7. Environment Variables

### Backend `.env`

```env
# ── InsightX Metadata Database ──────────────────────────────────────────────
# Must use the +asyncpg dialect for async SQLAlchemy
DATABASE_URL=postgresql+asyncpg://insightx:your_password@localhost:5432/insightx_meta

# ── Credential Encryption ────────────────────────────────────────────────────
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
# Store in a secrets manager (AWS Secrets Manager, Azure Key Vault) in production
# NEVER commit this value to version control
CREDENTIAL_ENCRYPTION_KEY=your_64_character_hex_string_here

# ── File Storage ─────────────────────────────────────────────────────────────
# Must be outside the webroot. In Docker, mount as a persistent volume.
SECURE_FILES_DIR=/var/insightx/secure-uploads

# ── Upload Limits ────────────────────────────────────────────────────────────
MAX_UPLOAD_SIZE_MB=5
```

### Frontend `.env.local`

```env
# Only needed if you are NOT using the proxy approach and want an absolute URL instead.
# Leave blank if the Vite/CRA proxy is configured.
# VITE_API_BASE_URL=http://localhost:8000
```

---

## 8. Testing Database Connections

### 8.1 Local First, Then Network — Always

Test locally before testing over a network. Local testing eliminates the network as a variable, making it much easier to isolate whether an error is a credential problem, a driver configuration problem, or a network/firewall problem. Once a local connection succeeds, introducing a real network address isolates any network-layer issues cleanly.

**The recommended progression:**

```
Local Docker container → Same LAN (another machine) → Remote / Cloud DB
```

---

### 8.2 PostgreSQL — Local Setup with Docker

```bash
# Start a local PostgreSQL instance
docker run -d \
  --name insightx-test-pg \
  -e POSTGRES_USER=testuser \
  -e POSTGRES_PASSWORD=testpass \
  -e POSTGRES_DB=testdb \
  -p 5432:5432 \
  postgres:15

# Verify it is running
docker ps
docker logs insightx-test-pg
```

**Test checklist for PostgreSQL:**

| #   | Scenario                                                     | Expected Result                   |
| --- | ------------------------------------------------------------ | --------------------------------- |
| 1   | Engine: PG, Auth: password, correct credentials, TLS off     | ✅ Success + latency              |
| 2   | Engine: PG, Auth: password, wrong password                   | ❌ `AUTH_FAILED`                  |
| 3   | Engine: PG, Auth: password, wrong host (`localhost99`)       | ❌ `HOST_UNREACHABLE`             |
| 4   | Engine: PG, Auth: password, wrong port (`9999`)              | ❌ `HOST_UNREACHABLE`             |
| 5   | Engine: PG, TLS enabled, `Verify Server Cert` off            | ✅ Success (self-signed accepted) |
| 6   | Engine: PG, TLS enabled, `Verify Server Cert` on, no CA cert | ❌ `TLS_HANDSHAKE_FAILED`         |

> **TLS test:** PostgreSQL Docker images do not have SSL enabled by default. To test TLS locally, either use a managed cloud PostgreSQL with SSL (e.g., AWS RDS, Supabase) or generate a self-signed cert and configure `postgresql.conf` manually.

---

### 8.3 MS SQL Server — Local Setup with Docker

```bash
# Start a local MSSQL instance (SQL Server 2022 on Linux — no Windows needed)
docker run -d \
  --name insightx-test-mssql \
  -e ACCEPT_EULA=Y \
  -e MSSQL_SA_PASSWORD=StrongPass1! \
  -p 1433:1433 \
  mcr.microsoft.com/mssql/server:2022-latest

# Wait ~30 seconds for the server to initialise, then verify:
docker logs insightx-test-mssql | tail -5
# Should show: "SQL Server is now ready for client connections."

# Connect to verify (using sqlcmd inside the container)
docker exec -it insightx-test-mssql /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P 'StrongPass1!' -No -Q "SELECT @@VERSION"
```

**Test checklist for MSSQL:**

| #   | Scenario                                                            | Expected Result                            |
| --- | ------------------------------------------------------------------- | ------------------------------------------ |
| 1   | Engine: MSSQL, Auth: password (SA), correct creds, TLS off          | ✅ Success                                 |
| 2   | Engine: MSSQL, Auth: password, wrong password                       | ❌ `AUTH_FAILED`                           |
| 3   | Engine: MSSQL, Auth: password, wrong host                           | ❌ `HOST_UNREACHABLE`                      |
| 4   | Engine: MSSQL, Auth: password, `Encrypt=yes`, `TrustServerCert=yes` | ✅ Success (TLS, no cert verify)           |
| 5   | Engine: MSSQL, Auth: windows                                        | ⚠️ Only works on Windows host              |
| 6   | Engine: MSSQL, Auth: azure_ad                                       | Requires real Azure AD tenant + MSAL token |

> **ODBC Driver check:** Run `python -c "import pyodbc; print(pyodbc.drivers())"` on the backend host. You should see `ODBC Driver 17 for SQL Server` or `ODBC Driver 18 for SQL Server` in the list. If not, the MSSQL driver will fail before even attempting a connection.

---

### 8.4 Oracle — Local Setup with Docker

Oracle is the most complex to run locally. Use Oracle Database Free 23c (formerly XE) — it is free for development.

```bash
# Option A: Oracle Free 23c (official image — requires login to container-registry.oracle.com)
# 1. Accept the license at: https://container-registry.oracle.com
# 2. Log in to the Oracle Container Registry
docker login container-registry.oracle.com

# 3. Pull and run
docker run -d \
  --name insightx-test-oracle \
  -p 1521:1521 \
  -e ORACLE_PWD=StrongPass1! \
  container-registry.oracle.com/database/free:latest

# The first startup takes 5–10 minutes. Watch the logs:
docker logs -f insightx-test-oracle
# Wait for: "DATABASE IS READY TO USE!"

# Default service name: FREE
# Default SID:          FREE
# Default system user:  system (password = ORACLE_PWD)

# Option B: Community Oracle XE image (no registry login needed — unofficial)
docker run -d \
  --name insightx-test-oracle-xe \
  -p 1521:1521 \
  -e ORACLE_PASSWORD=StrongPass1! \
  gvenzl/oracle-free:latest
```

**Test checklist for Oracle:**

| #   | Scenario                                                                         | Expected Result                                              |
| --- | -------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| 1   | Engine: Oracle, Connection: Service Name (`FREE`), Auth: password, correct creds | ✅ Success                                                   |
| 2   | Engine: Oracle, Connection: SID (`FREE`), Auth: password, correct creds          | ✅ Success                                                   |
| 3   | Engine: Oracle, Auth: password, wrong password                                   | ❌ `AUTH_FAILED` (`ORA-01017`)                               |
| 4   | Engine: Oracle, Auth: password, wrong host                                       | ❌ `HOST_UNREACHABLE` (`ORA-12541`)                          |
| 5   | Engine: Oracle, Auth: wallet                                                     | Requires Oracle Wallet files — test after other methods pass |
| 6   | Engine: Oracle, Auth: kerberos                                                   | ❌ `UNSUPPORTED_CONFIG` (Thin Mode) — expected               |

> **python-oracledb Thin Mode note:** For password auth and wallet, Thin Mode works without any Oracle Client. You should see connections working with just `pip install python-oracledb`. Kerberos will always fail in Thin Mode with a classifiable error — this is expected behaviour documented in the driver.

---

### 8.5 Universal Error Verification Tests

Run these against all three engines after basic success is confirmed. These verify that `_classify_error()` is working correctly.

```
Test: Wrong hostname → must return category: "HOST_UNREACHABLE"
Test: Wrong password → must return category: "AUTH_FAILED"
Test: TLS enabled, wrong CA cert → must return category: "TLS_HANDSHAKE_FAILED"
Test: Correct host/port but DB service not running → must return category: "HOST_UNREACHABLE"
```

You can verify the raw API response using curl or the interactive docs at `http://localhost:8000/docs`:

```bash
# Example: test a PostgreSQL connection via curl
curl -X POST http://localhost:8000/api/v1/datasources/test \
  -H "Content-Type: application/json" \
  -d '{
    "name": "local-pg-test",
    "engine": "postgresql",
    "host": "localhost",
    "port": 5432,
    "database": "testdb",
    "auth_method": "password",
    "credentials": {
      "username": "testuser",
      "password": "testpass"
    },
    "tls": { "enabled": false }
  }'

# Expected success response:
# {"success": true, "latency_ms": 18, "category": null, "message": null}

# Expected failure (wrong password):
# {"success": false, "latency_ms": 12, "category": "AUTH_FAILED", "message": "Authentication failed..."}
```

---

### 8.6 Network Testing (After Local Passes)

Once every engine passes locally, run the same test matrix against a real network target (another machine on the same LAN, or a cloud DB). This tests:

- Firewall rule correctness (port 5432/1433/1521 open)
- DNS resolution of hostnames
- TLS certificate validity against a real CA
- Connection latency under real conditions

If a test passes locally but fails over the network, the problem is almost always a **firewall rule** or **TLS certificate mismatch** — not the application code.

---

_Generated for InsightX M1 — Data Source Onboarding_  
_Backend: FastAPI 0.104+ / Python 3.11 · Frontend: React 18_
