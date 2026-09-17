from typing import List, Optional
from pydantic import BaseModel, Field


class ClarificationOption(BaseModel):
    id: str = Field(description="Unique identifier for the clarification choice (e.g. 'revenue', 'most_orders')")
    label: str = Field(description="User-friendly short title (e.g. 'Highest Revenue')")
    description: str = Field(description="Clear explanation of what this interpretation entails")


class AmbiguityResponse(BaseModel):
    ambiguous: bool = Field(description="True if the question is underspecified or ambiguous; False if unambiguous")
    ambiguity_type: Optional[str] = Field(
        default=None,
        description="Category of ambiguity: 'metric', 'time', 'ranking', 'entity', 'filter', 'business_term', or None"
    )
    reason: Optional[str] = Field(
        default=None,
        description="Reasoning behind why the question is ambiguous or clear"
    )
    ambiguities: List[str] = Field(
        default_factory=list,
        description="List of specific ambiguous phrases or terms found in the question"
    )
    clarification_question: Optional[str] = Field(
        default=None,
        description="Concise multiple-choice question to ask the user to resolve ambiguity"
    )
    options: List[ClarificationOption] = Field(
        default_factory=list,
        description="Multiple-choice options for the user to pick from"
    )


class SQLResponse(BaseModel):
    sql: str = Field(description="PostgreSQL-compatible SELECT query")
    explanation: str = Field(description="Brief explanation of how the SQL query resolves the user's intent")
    tables_used: List[str] = Field(description="List of table names referenced in the query")
