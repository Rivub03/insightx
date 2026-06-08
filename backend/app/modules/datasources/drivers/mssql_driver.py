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