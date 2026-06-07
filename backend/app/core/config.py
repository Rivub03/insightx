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
    # Must use the +asyncpg dialect for SQLAlchemy async support:
    #   postgresql+asyncpg://user:password@host:port/database_name
    database_url: str

    # --- AES-256-GCM credential encryption key ---
    # 64 hex characters = 32 bytes = 256 bits
    # Store this in a secrets manager (AWS Secrets Manager, Azure Key Vault) in production
    credential_encryption_key: str

    # --- Secure file storage ---
    # Directory for TLS certs, Oracle Wallets, and Kerberos keytabs
    # Must be outside the webroot and writable by the app process
    # In Docker, mount this as a persistent volume — NOT ephemeral container storage
    secure_files_dir: str = "/var/insightx/secure-uploads"

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