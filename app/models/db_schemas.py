from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DBConnectionRequest(BaseModel):
    host: str = Field(default="localhost", description="PostgreSQL host address")
    port: int = Field(default=5432, description="PostgreSQL port")
    database: str = Field(description="Database name")
    username: str = Field(description="Database username")
    password: str = Field(description="Database password")


class DBTestResponse(BaseModel):
    success: bool
    message: str
    database_name: Optional[str] = None


class DBSchemaResponse(BaseModel):
    connected: bool
    database_name: str
    host: str
    port: int
    schema_text: str
    tables: List[str]
