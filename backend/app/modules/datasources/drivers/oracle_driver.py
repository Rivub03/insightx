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