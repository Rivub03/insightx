from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from enum import Enum

class EngineType(str, Enum):
    ORACLE = "oracle"
    POSTGRESQL = "postgresql"
    MSSQL = "mssql"

class AuthMethod(str, Enum):
    PASSWORD = "username_password"
    ORACLE_WALLET = "oracle_wallet"
    KERBEROS = "kerberos"
    AZURE_AD = "azure_ad"

class ConnectionTestRequest(BaseModel):
    # Core fields required across all engines
    engine: EngineType
    host: str = Field(..., description="Database server address")
    port: int = Field(..., description="Database port (e.g., 5432, 1521)")
    database_name: str = Field(..., description="DB or Service Name")
    
    # Authentication parameters
    auth_method: AuthMethod = AuthMethod.PASSWORD
    username: Optional[str] = None
    password: Optional[str] = None
    
    # TLS / Security parameters
    tls_enabled: bool = False
    tls_config: Optional[Dict[str, Any]] = Field(default_factory=dict)