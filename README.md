# insightx

A mock insightx application

## Project Directory Structure:

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
