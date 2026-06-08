# insightx

A mock insightx application

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

---

#### `app/core/config.py`

**Role:** Settings management.  
Uses `pydantic-settings` to load environment variables (and `.env` files) with type validation. The `settings` singleton is the single place any module reads configuration — no module calls `os.getenv()` directly. If a required variable is missing, the app fails at startup with a clear error.

**Key variables:** `DATABASE_URL`, `CREDENTIAL_ENCRYPTION_KEY`, `SECURE_FILES_DIR`.

---

#### `app/db/base.py`

**Role:** SQLAlchemy declarative base.  
Contains only `class Base(DeclarativeBase)`. Kept separate to prevent circular imports when models reference each other (a common SQLAlchemy pain point).

---

#### `app/db/session.py`

**Role:** Async database session factory.  
Creates the `async_engine` pointed at the InsightX metadata PostgreSQL database. The `get_db()` async generator is a FastAPI dependency — it yields an `AsyncSession` per request, commits on success, and rolls back on exception. Route handlers never manage sessions manually.

---

#### `app/db/models/datasource.py`

**Role:** SQLAlchemy ORM model.  
Defines the `datasources` table structure with all constraints (unique name per tenant, valid oracle*connection_type values, valid last_test_status values). Sensitive columns (`encrypted_credentials`, `tls*\*\_cert_path`) exist in the model but are always stripped before any API response by `service.py`'s `\_mask_sensitive_fields()`.

---

#### `app/config/engines_config.py`

**Role:** Single source of truth for engine metadata (backend copy).  
A plain Python dict that defines, per engine: default port, supported auth methods, valid TLS modes, and whether a connection type toggle is needed. Both the validator (`schemas.py`) and the frontend (`engines.js`) reference equivalent copies of this data. **Keep the two in sync.**

---

#### `app/modules/datasources/schemas.py`

**Role:** Request and response validation (Pydantic v2, replaces Joi).  
Defines `DatasourcePayload` with a `model_validator` that enforces three cross-field rules: oracle_connection_type is required iff engine is oracle; auth_method must be valid for the engine; credentials dict must contain the required keys for the auth method. FastAPI turns any `ValueError` raised here into an HTTP 422 with per-field details automatically.

**Key models:** `DatasourcePayload` (input), `TestConnectionResponse`, `DatasourceResponse`, `DatasourceListResponse`, `FileUploadResponse`.

---

#### `app/modules/datasources/credential_encryptor.py`

**Role:** AES-256-GCM encryption/decryption for credential dicts.  
Credentials are JSON-serialised and encrypted before any DB write. The stored format is `iv_hex:tag_hex:ciphertext_hex` (a single TEXT column). GCM mode includes an authentication tag — if the stored value is tampered with, `decrypt()` raises `InvalidTag` rather than silently returning garbage. The key is read from `CREDENTIAL_ENCRYPTION_KEY` at call time, not at import time.

---

#### `app/modules/datasources/connection_tester.py`

**Role:** Connection test dispatcher and error classifier.  
Uses a `driver_map` dict (Strategy pattern) to call the right driver at runtime. Wraps the driver call in `asyncio.wait_for()` with a 10-second hard timeout. After the driver returns, `_classify_error()` translates raw driver exceptions into one of six category strings (`AUTH_FAILED`, `HOST_UNREACHABLE`, `TLS_HANDSHAKE_FAILED`, `TIMEOUT`, `UNSUPPORTED_CONFIG`, `UNKNOWN`) that the frontend displays distinctly.

---

#### `app/modules/datasources/drivers/postgres_driver.py`

**Role:** Adapter for `asyncpg` (PostgreSQL).  
Builds an `ssl.SSLContext` from the TLS config (loading CA cert and optional client cert/key from file paths), connects with `asyncpg.connect()`, runs `SELECT 1`, and returns the normalised result dict. Fully async — no executor wrapper needed.

---

#### `app/modules/datasources/drivers/mssql_driver.py`

**Role:** Adapter for `pyodbc` (MS SQL Server).  
`pyodbc` is synchronous, so the actual connection logic runs in `asyncio.to_thread()` to avoid blocking FastAPI's event loop. Handles three auth methods: password (SQL Auth), Windows NTLM, and Azure AD (token encoded as UTF-16-LE struct via `SQL_COPT_SS_ACCESS_TOKEN`). Detects the installed ODBC driver version automatically via `pyodbc.drivers()`.

> **System requirement:** Microsoft ODBC Driver 17 or 18 for SQL Server must be installed on the backend host OS. See [Microsoft's installation guide](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server).

---

#### `app/modules/datasources/drivers/oracle_driver.py`

**Role:** Adapter for `python-oracledb` (Oracle 12c+).  
Runs in **Thin Mode** by default (no Oracle Client libraries needed). Builds the DSN/connect string in three formats: Easy Connect (service name), SID legacy format, or TCPS (Oracle SSL). Supports password auth and Oracle Wallet in Thin Mode. Kerberos requires Thick Mode — the driver will return a classifiable `UNSUPPORTED_CONFIG` error if attempted in Thin Mode.

> **Note on Kerberos + Thick Mode:** Call `oracledb.init_oracle_client(lib_dir=...)` in `main.py` before any connections are made if Thick Mode is needed.

---

#### `app/modules/datasources/service.py`

**Role:** Business logic layer.  
Three public functions: `test_datasource_connection()` (delegates to tester, no DB writes), `create_datasource()` (encrypts credentials, writes to DB, checks for duplicate names), `list_datasources()` (tenant-scoped query, credentials always stripped). The `_mask_sensitive_fields()` private function is the gatekeeper — it is the only path from a DB record to an API response, and it always removes `encrypted_credentials` and cert paths.

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

#### `api/datasource.api.js`

All `fetch()` calls to the backend in one place. Components never call `fetch()` directly. Handles file uploads via `FormData` (no `Content-Type` header — the browser sets the multipart boundary automatically).

#### `hooks/useDataSourceForm.js`

Central form state for all 5 wizard steps. `selectEngine()` resets all downstream state when the engine changes. `setAuthMethod()` resets only credentials, preserving connection fields (per US 107148 acceptance criteria). `buildPayload()` assembles the complete JSON body for the API.

#### `hooks/useConnectionTest.js`

State machine for the test flow: `idle → testing → success | failed`. `resetTest()` is called inside every `onChange` handler in the wizard so that editing any field after a successful test re-disables the Save button.

#### `components/EngineSelector.jsx`

Step 0. Clickable cards, one per engine. Calls `selectEngine()` on click.

#### `components/ConnectionDetailsForm.jsx`

Step 1. Host, port, database name, connection name. Port auto-fills from `engines.js`. Shows Oracle SID/Service Name toggle when engine is Oracle.

#### `components/AuthConfigForm.jsx`

Step 2. Auth method tabs (filtered by engine) + the corresponding credential sub-form. Switching the tab calls `setAuthMethod()`, which resets only credential fields. Sub-forms: `PasswordForm`, `OracleWalletForm`, `KerberosForm`, `WindowsAuthForm`, `AzureADForm`.

#### `components/TLSConfigForm.jsx`

Step 3. TLS toggle + conditional fields (CA cert upload, client cert/key for mTLS, verify checkbox with warning). Engine-aware labels: "SSL Mode" for PG, "Encrypt" for MSSQL, "SSL (TCPS)" for Oracle.

#### `components/TestConnectionPanel.jsx`

Step 4. "Test Connection" button, spinner during test, result display (success with latency or failure with categorised error), and the Save button (disabled until test passes).

#### `pages/AddDataSourcePage.jsx`

Wizard orchestrator. Manages the current step, calls `resolveFileUploads()` to upload File objects before the test payload is sent, and calls `createDatasource()` on save.

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
