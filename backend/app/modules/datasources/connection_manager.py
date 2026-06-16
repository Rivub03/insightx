# backend/app/modules/datasources/connection_manager.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from typing import Optional, Dict
import logging
from .credential_encryptor import decrypt_credentials  # Existing
from .schemas import DataSourceConfig

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Runtime connection factory - critical for M1 compliance."""
    
    _engines = {}  # In-memory cache: key = (tenant_id, datasource_id) -> engine
    # WARNING: For production, use Redis or DB-backed cache with TTL for scalability.

    @classmethod
    def get_engine(cls, config: DataSourceConfig, user_context: Dict = None) -> sqlalchemy.engine.Engine:
        """Creates or reuses engine at runtime. Never use env vars for customer DBs."""
        cache_key = (config.tenant_id, config.id)
        
        if cache_key in cls._engines:
            engine = cls._engines[cache_key]
            # Optional: ping to validate
            try:
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                return engine
            except Exception:
                logger.warning("Stale engine, recreating...")
                cls.dispose_engine(cache_key)
        
        # Build runtime URL with decrypted creds + user context (ABAC)
        decrypted = decrypt_credentials(config.encrypted_creds)
        url = cls._build_url(config, decrypted, user_context)
        
        engine = create_engine(
            url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,  # Critical: detects dead connections
            pool_timeout=30,
            connect_args=cls._get_connect_args(config)  # TLS, auth specifics
        )
        
        cls._engines[cache_key] = engine
        logger.info(f"Runtime engine created for {config.name} (tenant: {config.tenant_id})")
        return engine

    @staticmethod
    def _build_url(config: DataSourceConfig, creds: Dict, user_context: Optional[Dict]) -> str:
        """Dynamic URL - runtime only, supports advanced auth."""
        # Example for PostgreSQL; extend for MSSQL/Oracle with if/elif
        if config.db_type == "postgresql":
            return f"postgresql://{creds['username']}:{creds['password']}@{config.host}:{config.port}/{config.database}"
        # Add Oracle wallet/Kerberos/Azure AD logic here (driver-specific)
        raise ValueError(f"Unsupported DB type: {config.db_type}")

    @staticmethod
    def _get_connect_args(config: DataSourceConfig) -> Dict:
        """Engine-specific TLS/auth args."""
        args = {}
        if config.tls_config and config.tls_config.enabled:
            args["sslmode"] = config.tls_config.ssl_mode
            # Add cert paths if uploaded (temp secure storage)
        return args

    @classmethod
    def dispose_engine(cls, key):
        """Clean up to prevent persistence after restart/session end."""
        if key in cls._engines:
            cls._engines[key].dispose()
            del cls._engines[key]

    @classmethod
    def dispose_all(cls):
        """Call on app shutdown or user logout."""
        for engine in cls._engines.values():
            engine.dispose()
        cls._engines.clear()