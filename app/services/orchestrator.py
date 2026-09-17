import uuid
import logging
from typing import Dict, Any, Optional
from app.models.api_schemas import QueryRequest, QueryResponse
from app.models.llm_schemas import AmbiguityResponse
from app.services.ambiguity_detector import ambiguity_detector
from app.services.clarification_engine import clarification_engine
from app.services.sql_generator import sql_generator
from app.services.sql_validator import sql_validator
from app.services.query_executor import query_executor

logger = logging.getLogger("orchestrator")


class QueryOrchestrator:
    """
    Main pipeline orchestrator for QueryClarify.
    Manages session state, ambiguity detection, clarification resolution,
    SQL generation, SQLGlot validation, and PostgreSQL execution.
    """

    def __init__(self):
        # In-memory session store: session_id -> dict
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def process_query(self, request: QueryRequest) -> QueryResponse:
        session_id = request.session_id or str(uuid.uuid4())
        session_data = self.sessions.get(session_id, {})

        # Scenario 1: User is submitting a clarification answer to a pending clarification prompt
        if request.selected_option and session_data.get("status") == "clarification_required":
            return self._handle_clarification_response(session_id, session_data, request.selected_option)

        # Scenario 2: New query initiation
        return self._handle_new_query(session_id, request.question)

    def _handle_new_query(self, session_id: str, question: str) -> QueryResponse:
        logger.info(f"[Session {session_id}] Processing new query: '{question}'")

        # Step 1: Ambiguity Detection
        ambiguity: AmbiguityResponse = ambiguity_detector.analyze(question)

        # If question is ambiguous, save state and ask for clarification
        if ambiguity.ambiguous and ambiguity.options:
            self.sessions[session_id] = {
                "session_id": session_id,
                "status": "clarification_required",
                "original_question": question,
                "ambiguity": ambiguity
            }
            return QueryResponse(
                session_id=session_id,
                status="clarification_required",
                question=question,
                ambiguity=ambiguity,
                clarification_question=ambiguity.clarification_question,
                clarification_options=ambiguity.options
            )

        # If question is unambiguous, proceed directly to SQL generation & execution
        return self._generate_validate_execute(
            session_id=session_id,
            question=question,
            clarification_context=None,
            ambiguity=ambiguity
        )

    def _handle_clarification_response(
        self,
        session_id: str,
        session_data: Dict[str, Any],
        selected_option_id: str
    ) -> QueryResponse:
        original_question = session_data["original_question"]
        ambiguity: AmbiguityResponse = session_data["ambiguity"]

        # Resolve selected choice
        selected_opt = clarification_engine.resolve_clarification(ambiguity, selected_option_id)
        if not selected_opt:
            return QueryResponse(
                session_id=session_id,
                status="error",
                question=original_question,
                error=f"Invalid clarification choice '{selected_option_id}'. Please select a valid option."
            )

        # Build context string combining original question & selected option
        clarification_context = clarification_engine.build_resolved_prompt_context(
            original_question=original_question,
            clarification_question=ambiguity.clarification_question or "",
            selected_option=selected_opt
        )

        logger.info(f"[Session {session_id}] Clarification resolved with option: {selected_opt.label}")

        # Clear active clarification state for session
        self.sessions[session_id]["status"] = "resolved"

        return self._generate_validate_execute(
            session_id=session_id,
            question=original_question,
            clarification_context=clarification_context,
            ambiguity=ambiguity
        )

    def _generate_validate_execute(
        self,
        session_id: str,
        question: str,
        clarification_context: Optional[str],
        ambiguity: AmbiguityResponse
    ) -> QueryResponse:
        # Step 2: SQL Generation
        sql_res = sql_generator.generate(question=question, clarification_context=clarification_context)

        # Step 3: SQLGlot Validation & Read-Only Safety Enforcer
        is_valid, clean_sql, val_msg, tables_used = sql_validator.validate_and_sanitize(sql_res.sql)
        
        if not is_valid:
            logger.warning(f"[Session {session_id}] SQL Validation failed: {val_msg}")
            return QueryResponse(
                session_id=session_id,
                status="error",
                question=question,
                ambiguity=ambiguity,
                sql=sql_res.sql,
                explanation=sql_res.explanation,
                tables_used=tables_used,
                error=f"SQL Safety Guardrail Rejected Query: {val_msg}"
            )

        # Step 4: PostgreSQL Execution
        success, columns, rows, duration_ms, summary, exec_error = query_executor.execute(clean_sql)

        if not success:
            return QueryResponse(
                session_id=session_id,
                status="error",
                question=question,
                ambiguity=ambiguity,
                sql=clean_sql,
                explanation=sql_res.explanation,
                tables_used=tables_used,
                error=exec_error
            )

        return QueryResponse(
            session_id=session_id,
            status="completed",
            question=question,
            ambiguity=ambiguity,
            sql=clean_sql,
            explanation=sql_res.explanation,
            tables_used=tables_used,
            columns=columns,
            rows=rows,
            row_count=len(rows),
            execution_time_ms=duration_ms,
            summary=summary
        )


orchestrator = QueryOrchestrator()
