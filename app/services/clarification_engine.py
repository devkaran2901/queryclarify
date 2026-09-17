import logging
from typing import Optional
from app.models.llm_schemas import AmbiguityResponse, ClarificationOption

logger = logging.getLogger("clarification_engine")


class ClarificationEngine:
    """
    Manages resolution of user clarification choices to form unambiguous context instructions
    for Text-to-SQL generation.
    """

    def resolve_clarification(
        self,
        ambiguity: AmbiguityResponse,
        selected_option_id: str
    ) -> Optional[ClarificationOption]:
        """
        Finds the matching option selected by the user.
        """
        for opt in ambiguity.options:
            if opt.id.lower() == selected_option_id.lower():
                return opt
        return None

    def build_resolved_prompt_context(
        self,
        original_question: str,
        clarification_question: str,
        selected_option: ClarificationOption
    ) -> str:
        """
        Constructs context string combining original question and user clarification choice.
        """
        return (
            f"Original Question: '{original_question}'\n"
            f"Clarification Asked: '{clarification_question}'\n"
            f"User Selected Interpretation: '{selected_option.label}' ({selected_option.description})"
        )


clarification_engine = ClarificationEngine()
