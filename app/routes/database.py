import logging
from fastapi import APIRouter, HTTPException, Header, status
from typing import Optional
from app.models.db_schemas import DBConnectionRequest, DBTestResponse, DBSchemaResponse
from app.services.connection_manager import connection_manager
from app.database.schema_inspector import schema_inspector

logger = logging.getLogger("routes_database")
router = APIRouter(prefix="/api/database", tags=["Database"])


@router.post("/test", response_model=DBTestResponse)
def test_database_connection(req: DBConnectionRequest):
    """Test connection to target PostgreSQL database."""
    success, message = connection_manager.test_connection(
        host=req.host,
        port=req.port,
        database=req.database,
        username=req.username,
        password=req.password
    )
    return DBTestResponse(
        success=success,
        message=message,
        database_name=req.database if success else None
    )


@router.post("/connect", response_model=DBTestResponse)
def connect_database(req: DBConnectionRequest, x_session_id: Optional[str] = Header(default="default")):
    """Establishes database engine for current session."""
    session_id = x_session_id or "default"
    success, message = connection_manager.connect(
        session_id=session_id,
        host=req.host,
        port=req.port,
        database=req.database,
        username=req.username,
        password=req.password
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    return DBTestResponse(
        success=True,
        message=message,
        database_name=req.database
    )


@router.post("/disconnect")
def disconnect_database(x_session_id: Optional[str] = Header(default="default")):
    """Disconnects session's database and reverts to demo DB."""
    session_id = x_session_id or "default"
    connection_manager.disconnect(session_id)
    return {"message": "Disconnected custom database. Reverted to demo database."}


@router.get("/schema", response_model=DBSchemaResponse)
def get_connected_schema(x_session_id: Optional[str] = Header(default="default")):
    """Returns dynamic schema summary for current session's database."""
    session_id = x_session_id or "default"
    engine = connection_manager.get_engine(session_id)
    info = connection_manager.get_status(session_id)
    
    schema_text = schema_inspector.get_schema_summary(engine)
    tables = schema_inspector.get_tables(engine)

    return DBSchemaResponse(
        connected=info["connected"],
        database_name=info["database_name"],
        host=info["host"],
        port=info["port"],
        schema_text=schema_text,
        tables=tables
    )
