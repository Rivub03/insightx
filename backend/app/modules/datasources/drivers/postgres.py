import time
import asyncio
import psycopg
from app.modules.datasources.drivers.base import BaseDatabaseDriver
from app.modules.datasources.schemas import ConnectionTestRequest

class PostgresDriver(BaseDatabaseDriver):
    
    async def test_connection(self, config: ConnectionTestRequest) -> dict:
        start_time = time.time()
        
        # 1. Map the abstract Pydantic schema into a Postgres-specific connection string
        conn_params = f"host={config.host} port={config.port} dbname={config.database_name} user={config.username} password={config.password} connect_timeout=5"
        
        # 2. Handle TLS logic explicitly based on engine rules
        if config.tls_enabled:
            ssl_mode = config.tls_config.get("ssl_mode", "require")
            conn_params += f" sslmode={ssl_mode}"

        # 3. Offload the blocking driver call to a separate thread
        # This prevents the FastAPI event loop from freezing during network timeouts
        def _connect():
            with psycopg.connect(conn_params) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")
                    
        try:
            await asyncio.to_thread(_connect)
            elapsed = int((time.time() - start_time) * 1000)
            return {"success": True, "message": "Connected successfully!", "elapsed_ms": elapsed}
        except Exception as e:
            # 4. Map raw driver errors to client-safe responses
            return {"success": False, "error": str(e), "elapsed_ms": int((time.time() - start_time) * 1000)}