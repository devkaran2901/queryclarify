import logging
from typing import Optional, List
from sqlalchemy.engine import Engine
from app.database.schema_inspector import schema_inspector
from app.models.llm_schemas import SQLResponse
from app.prompts.sql_prompt import SQL_GENERATION_SYSTEM_PROMPT
from app.services.groq_client import groq_client

logger = logging.getLogger("sql_generator")


class SQLGenerator:
    """
    Generates PostgreSQL SELECT queries from natural language questions, schema context, and conversation history.
    """

    def generate(
        self,
        question: str,
        clarification_context: Optional[str] = None,
        chat_history_summary: Optional[str] = None,
        engine: Optional[Engine] = None
    ) -> SQLResponse:
        logger.info(f"Generating SQL for question: '{question}'")
        schema_text = schema_inspector.get_schema_summary(engine)
        
        system_prompt = SQL_GENERATION_SYSTEM_PROMPT.format(schema_text=schema_text)
        
        user_prompt_lines = []
        if chat_history_summary:
            user_prompt_lines.append(f"Conversation History Context:\n{chat_history_summary}")
            
        user_prompt_lines.append(f"User Question: {question}")
        
        if clarification_context:
            user_prompt_lines.append(f"Clarification Context: {clarification_context}")
        
        user_prompt = "\n\n".join(user_prompt_lines)

        sql_res = groq_client.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=SQLResponse
        )
        return sql_res


sql_generator = SQLGenerator()
