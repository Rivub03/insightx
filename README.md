# insightx

A mock insightx application

## Project Structure

### Directory Structure

```
insightx/
├── backend/
│ ├── app/
│ │ ├── core/ # Global, system-wide cross-cutting concerns
│ │ │ ├── **init**.py
│ │ │ ├── config.py # Application settings, environment variable loading
│ │ │ ├── database.py # InsightX system database engine & session maker
│ │ │ ├── security.py # System wide AES-256-GCM encryption/decryption utilities
│ │ │ └── exceptions.py # Global FastAPI error-mapping and interceptor handlers
│ │ │
│ │ ├── modules/ # Monolithic core divided into distinct, isolated domains
│ │ │ ├── **init**.py
│ │ │ │
│ │ │ ├── datasources/ # --- MODULE 1: DATA SOURCE ONBOARDING ---
│ │ │ │ ├── **init**.py
│ │ │ │ ├── router.py # Exposes /sources and /sources/test endpoints
│ │ │ │ ├── service.py # Business logic: orchestrates encryption, storage, & testing
│ │ │ │ ├── models.py # DB Entity models tracking engine details & credentials
│ │ │ │ ├── schemas.py # Pydantic models for custom field validations per engine
│ │ │ │ └── drivers/ # Low-level native driver orchestration wrappers
│ │ │ │ ├── **init**.py
│ │ │ │ ├── base.py # Abstract Base Class declaring unified connection contracts
│ │ │ │ ├── postgres.py # Native driver implementation utilizing psycopg v3
│ │ │ │ ├── oracle.py # Native driver implementation utilizing python-oracledb Thin Mode
│ │ │ │ └── mssql.py # Native driver implementation utilizing pyodbc + Linux ODBC 18
│ │ │ │
│ │ │ ├── dictionary/ # --- MODULE 2: DATA DICTIONARY GENERATION (Future) ---
│ │ │ └── nltosql/ # --- MODULE 3: NATURAL LANGUAGE TO SQL (Future) ---
│ │ │
│ │ ├── middleware/ # App-level custom interceptors
│ │ │ └── upload.py # Secure file stream processing (for Wallets, Certs, Keytabs)
│ │ │
│ │ └── main.py # Gateway file initializing FastAPI, CORS, and mounting modules
│ │
│ ├── migrations/ # Database schema schema evolution tracker (Alembic files)
│ ├── requirements.txt # Direct backend dependency declarations
│ └── Dockerfile # Explicit container recipe ensuring installation of msodbcsql18
│
├── frontend/
│ ├── src/
│ │ ├── app/ # Next.js App Router structural layout layer
│ │ │ ├── layout.tsx # Global application HTML framing and UI providers
│ │ │ ├── page.tsx # Primary dashboard interface
│ │ │ └── datasources/
│ │ │ ├── page.tsx # Saved Data Source inventory list grid
│ │ │ └── add/
│ │ │ └── page.tsx # Interactive step-by-step connection setup workspace
│ │ │
│ │ ├── features/ # Domain-Driven layout mirroring backend structures
│ │ │ └── datasources/ # Encompasses all UI logic for Module 1
│ │ │ ├── components/ # Isolated component components
│ │ │ │ ├── EngineSelector.tsx
│ │ │ │ ├── ConnectionDetailsForm.tsx
│ │ │ │ ├── AuthConfigForm.tsx
│ │ │ │ ├── TLSConfigForm.tsx
│ │ │ │ └── TestConnectionPanel.tsx
│ │ │ ├── hooks/ # Custom state engines isolating React lifecycles
│ │ │ │ ├── useDataSourceForm.ts
│ │ │ │ └── useConnectionTest.ts
│ │ │ ├── services/ # Pure API communication scripts using fetch/axios
│ │ │ │ └── datasourceApi.ts
│ │ │ └── types/ # Domain strict compile-time TypeScript declarations
│ │ │ └── index.ts
│ │ │
│ │ ├── components/ # Shareable primitive UI elements (Buttons, Inputs, Cards)
│ │ │ └── ui/
│ │ │
│ │ └── core/ # Application-wide unchanging constants and utility definitions
│ │ ├── constants/
│ │ │ └── engines.ts # Static engine specifications (Ports, validation rules)
│ │ └── utils/
```
