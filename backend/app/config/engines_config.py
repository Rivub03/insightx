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
