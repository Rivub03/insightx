from abc import ABC, abstractmethod
from app.modules.datasources.schemas import ConnectionTestRequest

class BaseDatabaseDriver(ABC):
    """
    Abstract Base Class enforcing a standard interface for all database drivers.
    Prevents spaghetti code by requiring all drivers to accept the same payload
    and return a standardized dictionary result.
    """
    
    @abstractmethod
    async def test_connection(self, config: ConnectionTestRequest) -> dict:
        pass