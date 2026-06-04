from app.modules.datasources.schemas import ConnectionTestRequest
from app.modules.datasources.drivers.postgres import PostgresDriver
# import OracleDriver, MSSQLDriver here when built

class DataSourceService:
    
    @staticmethod
    async def verify_connection(config: ConnectionTestRequest) -> dict:
        """
        Routes the connection request to the appropriate driver instance based on the engine type.
        """
        if config.engine == "postgresql":
            driver = PostgresDriver()
        elif config.engine == "oracle":
            # driver = OracleDriver()
            return {"success": False, "error": "Oracle driver pending implementation"}
        elif config.engine == "mssql":
            # driver = MSSQLDriver()
            return {"success": False, "error": "MSSQL driver pending implementation"}
        else:
            return {"success": False, "error": "Unsupported engine"}
            
        return await driver.test_connection(config)