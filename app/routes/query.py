import logging
from fastapi import APIRouter, HTTPException, status
from app.models.api_schemas import QueryRequest, QueryResponse, HealthResponse
from app.database.connection import SessionLocal
from app.database.schema_inspector import schema_inspector
from app.services.orchestrator import orchestrator
from app.config import settings
from sqlalchemy import text

logger = logging.getLogger("routes_query")
router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """Health check endpoint to verify API server and database connection."""
    db_status = "connected"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "error"

    return HealthResponse(
        status="ok" if db_status == "connected" else "degraded",
        database=db_status,
        model=settings.GROQ_MODEL
    )


@router.post("/api/query", response_model=QueryResponse, tags=["Query"])
def submit_query(request: QueryRequest):
    """
    Main endpoint for natural language queries and clarification responses.
    """
    if not request.question and not request.selected_option:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'question' or 'selected_option' must be provided."
        )

    try:
        response = orchestrator.process_query(request)
        return response
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal system error: {str(e)}"
        )


@router.get("/api/schema", tags=["Schema"])
def get_schema():
    """Returns database schema metadata summary."""
    return {"schema": schema_inspector.get_schema_summary()}
