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