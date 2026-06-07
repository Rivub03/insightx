# app/modules/datasources/drivers/postgres_driver.py
#
# PURPOSE:
#   Wraps asyncpg to test a PostgreSQL connection.
#   Fully async — no executor wrapper needed.
#
# LIBRARY: asyncpg (pip install asyncpg)
#
# TLS NOTES:
#   asyncpg's `ssl` parameter accepts:
#     False / None            → no TLS
#     True                    → require TLS, verify server cert using system CA store
#     ssl.SSLContext          → custom context (custom CA, client cert, skip verification)
#
#   We build a custom SSLContext when TLS is enabled so we can:
#     - Load a custom CA cert (cafile= reads directly from the file path)
#     - Load client cert + key for mutual TLS
#     - Optionally disable server cert verification for self-signed certs
#
# TIMEOUT:
#   asyncpg's connect() accepts `timeout` in seconds.
#   The outer asyncio.wait_for() in connection_tester.py provides an
#   additional safety net in case the driver's own timeout misfires.

import ssl
import time
from typing import Optional
import asyncpg


def _build_ssl_context(tls: dict) -> Optional[ssl.SSLContext]:
    """
    Builds an ssl.SSLContext from the TLS config dict.
    Returns None if TLS is disabled.

    Args:
        tls: TLS config dict from the datasource payload

    Returns:
        ssl.SSLContext or None
    """
    if not tls or not tls.get("enabled"):
        return None

    if tls.get("verify_server_cert", True):
        # Verify the server certificate.
        # create_default_context() sets verify_mode=CERT_REQUIRED and check_hostname=True by default.
        if tls.get("ca_cert_path"):
            # Use the custom CA certificate file to verify the server
            ctx = ssl.create_default_context(cafile=tls["ca_cert_path"])
        else:
            # Use the system's default CA store
            ctx = ssl.create_default_context()
    else:
        # User has opted to skip server cert verification (e.g., self-signed cert in dev)
        # This should show a visible warning in the UI (handled on the frontend)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode    = ssl.CERT_NONE

    # Mutual TLS — load client certificate and private key
    if tls.get("client_cert_path") and tls.get("client_key_path"):
        ctx.load_cert_chain(
            certfile=tls["client_cert_path"],
            keyfile=tls["client_key_path"],
        )

    return ctx


async def test_postgres_connection(config: dict) -> dict:
    """
    Tests a PostgreSQL connection by establishing a connection and
    running a trivial query. Non-destructive — no data is read or written.

    Args:
        config: Normalised connection config dict with keys:
            host, port, database, credentials {username, password},
            auth_method, tls (optional)

    Returns:
        {
            "success": bool,
            "latency_ms": int,
            "raw_error": Exception  # only on failure
        }
    """
    host        = config["host"]
    port        = int(config["port"])
    database    = config["database"]
    credentials = config["credentials"]
    tls         = config.get("tls") or {}

    ssl_context = _build_ssl_context(tls)

    start = int(time.time() * 1000)
    conn  = None

    try:
        conn = await asyncpg.connect(
            host     = host,
            port     = port,
            database = database,
            user     = credentials["username"],
            password = credentials["password"],
            ssl      = ssl_context,
            timeout  = 10.0,  # seconds — asyncpg's own connect timeout
        )

        # SELECT 1 is the cheapest possible query to confirm the connection is live.
        # asyncpg.connect() does not guarantee a fully authenticated session
        # on all server versions without an actual query.
        await conn.fetchval("SELECT 1")

        return {"success": True, "latency_ms": int(time.time() * 1000) - start}

    except Exception as exc:
        return {
            "success":    False,
            "latency_ms": int(time.time() * 1000) - start,
            "raw_error":  exc,
        }

    finally:
        # Always release the connection — asyncpg connections are not pooled here
        if conn:
            try:
                await conn.close()
            except Exception:
                pass  # Ignore cleanup errors — the test result is already determined