import logging
from typing import Optional
from app.database.schema_inspector import schema_inspector
from app.models.llm_schemas import SQLResponse
from app.prompts.sql_prompt import SQL_GENERATION_SYSTEM_PROMPT
from app.services.groq_client import groq_client

logger = logging.getLogger("sql_generator")


class SQLGenerator:
    """
    Generates PostgreSQL SELECT queries from natural language questions and schema context.
    """

    def generate(self, question: str, clarification_context: Optional[str] = None) -> SQLResponse:
        logger.info(f"Generating SQL for question: '{question}'")
        schema_text = schema_inspector.get_schema_summary()
        
        system_prompt = SQL_GENERATION_SYSTEM_PROMPT.format(schema_text=schema_text)
        
        user_prompt_lines = [f"User Question: {question}"]
        if clarification_context:
            user_prompt_lines.append(f"Clarification Context: {clarification_context}")
        
        user_prompt = "\n".join(user_prompt_lines)

        sql_res = groq_client.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=SQLResponse
        )
        return sql_res


sql_generator = SQLGenerator()
