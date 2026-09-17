from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.models.llm_schemas import AmbiguityResponse, ClarificationOption


class QueryRequest(BaseModel):
    session_id: Optional[str] = None
    question: str
    selected_option: Optional[str] = None


class QueryResponse(BaseModel):
    session_id: str
    status: str  # "clarification_required" | "completed" | "error"
    question: str
    ambiguity: Optional[AmbiguityResponse] = None
    clarification_question: Optional[str] = None
    clarification_options: Optional[List[ClarificationOption]] = None
    sql: Optional[str] = None
    explanation: Optional[str] = None
    tables_used: Optional[List[str]] = None
    columns: Optional[List[str]] = None
    rows: Optional[List[Dict[str, Any]]] = None
    row_count: Optional[int] = None
    execution_time_ms: Optional[float] = None
    summary: Optional[str] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    database: str = "connected"
    model: str
