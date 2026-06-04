import asyncio
from fastapi import APIRouter, HTTPException, status
from app.modules.datasources.schemas import ConnectionTestRequest
from app.modules.datasources.service import DataSourceService

# Mount this router in main.py under the /api/v1 prefix
router = APIRouter(prefix="/sources", tags=["Data Sources"])

@router.post("/test")
async def test_database_connection(payload: ConnectionTestRequest):
    """
    Transient endpoint to validate database credentials and network reachability.
    Does not persist data to the system database.
    """
    try:
        # Enforce a strict 10.0 second application-level timeout
        result = await asyncio.wait_for(
            DataSourceService.verify_connection(payload), 
            timeout=10.0
        )
        
        if not result["success"]:
            # Return HTTP 400 with the specific error context from the driver
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result)
            
        return result
        
    except asyncio.TimeoutError:
        # Catch hard hangs and return a standard timeout format
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail={"success": False, "error": "Connection attempt timed out after 10 seconds."}
        )