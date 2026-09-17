import logging
from app.database.schema_inspector import schema_inspector
from app.models.llm_schemas import AmbiguityResponse
from app.prompts.ambiguity_prompt import AMBIGUITY_DETECTION_SYSTEM_PROMPT
from app.services.groq_client import groq_client

logger = logging.getLogger("ambiguity_detector")


class AmbiguityDetector:
    """
    Analyzes natural language queries to detect ambiguous or underspecified intent.
    """

    def analyze(self, user_question: str) -> AmbiguityResponse:
        """
        Evaluates the user question against database schema context.
        """
        logger.info(f"Analyzing question for ambiguity: '{user_question}'")
        schema_text = schema_inspector.get_schema_summary()
        
        system_prompt = AMBIGUITY_DETECTION_SYSTEM_PROMPT.format(schema_text=schema_text)
        user_prompt = f"User Question: {user_question}"

        ambiguity_res = groq_client.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=AmbiguityResponse
        )
        return ambiguity_res


ambiguity_detector = AmbiguityDetector()
