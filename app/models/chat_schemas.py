from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.llm_schemas import AmbiguityResponse, ClarificationOption


class ChatMessage(BaseModel):
    id: str
    sender: str  # "user" | "assistant"
    text: str
    timestamp: str
    status: Optional[str] = None  # "completed" | "clarification_required" | "error"
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


class ChatSession(BaseModel):
    id: str
    title: str
    created_at: str
    db_session_id: str
    messages: List[ChatMessage] = Field(default_factory=list)


class SendMessageRequest(BaseModel):
    chat_id: str
    message: str
    selected_option: Optional[str] = None
