import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional
from app.models.chat_schemas import ChatSession, ChatMessage
from app.models.llm_schemas import AmbiguityResponse
from app.services.connection_manager import connection_manager
from app.database.schema_inspector import schema_inspector
from app.services.ambiguity_detector import ambiguity_detector
from app.services.clarification_engine import clarification_engine
from app.services.sql_generator import sql_generator
from app.services.sql_validator import sql_validator
from app.services.query_executor import query_executor

logger = logging.getLogger("chat_manager")


class ChatManager:
    """
    Manages in-memory chat sessions, conversation trajectories, and orchestrates
    multi-turn ambiguity detection, clarification resolution, and SQL execution.
    """

    def __init__(self):
        # Maps chat_id -> ChatSession
        self.chats: Dict[str, ChatSession] = {}

    def create_chat(self, title: str = "New Conversation", db_session_id: str = "default") -> ChatSession:
        chat_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        session = ChatSession(
            id=chat_id,
            title=title,
            created_at=timestamp,
            db_session_id=db_session_id,
            messages=[]
        )
        self.chats[chat_id] = session
        logger.info(f"Created chat session '{chat_id}' with title '{title}'")
        return session

    def list_chats(self) -> List[ChatSession]:
        """Returns list of active chat sessions ordered by created_at descending."""
        return sorted(list(self.chats.values()), key=lambda c: c.created_at, reverse=True)

    def get_chat(self, chat_id: str) -> Optional[ChatSession]:
        return self.chats.get(chat_id)

    def delete_chat(self, chat_id: str) -> bool:
        if chat_id in self.chats:
            del self.chats[chat_id]
            logger.info(f"Deleted chat session '{chat_id}'")
            return True
        return False

    def send_message(
        self,
        chat_id: str,
        user_text: str,
        selected_option_id: Optional[str] = None
    ) -> ChatMessage:
        chat = self.chats.get(chat_id)
        if not chat:
            title = user_text[:30] + ("..." if len(user_text) > 30 else "")
            chat = self.create_chat(title=title)

        if chat.title == "New Conversation" and user_text:
            chat.title = user_text[:30] + ("..." if len(user_text) > 30 else "")

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Append User Message
        user_msg = ChatMessage(
            id=str(uuid.uuid4()),
            sender="user",
            text=user_text,
            timestamp=timestamp
        )
        chat.messages.append(user_msg)

        engine = connection_manager.get_engine(chat.db_session_id)
        allowed_tables = set(schema_inspector.get_tables(engine))

        last_assistant_msg = self._get_last_clarification_prompt(chat)

        if selected_option_id and last_assistant_msg and last_assistant_msg.ambiguity:
            return self._process_clarification_response(
                chat=chat,
                user_text=user_text,
                selected_option_id=selected_option_id,
                last_assistant_msg=last_assistant_msg,
                engine=engine,
                allowed_tables=allowed_tables
            )

        return self._process_new_query(
            chat=chat,
            user_text=user_text,
            engine=engine,
            allowed_tables=allowed_tables
        )

    def _process_new_query(self, chat: ChatSession, user_text: str, engine, allowed_tables) -> ChatMessage:
        logger.info(f"[Chat {chat.id}] Processing query: '{user_text}'")

        ambiguity: AmbiguityResponse = ambiguity_detector.analyze(user_text, engine=engine)
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        if ambiguity.ambiguous and ambiguity.options:
            assistant_msg = ChatMessage(
                id=str(uuid.uuid4()),
                sender="assistant",
                text=ambiguity.clarification_question or "Please clarify your request.",
                timestamp=timestamp,
                status="clarification_required",
                ambiguity=ambiguity,
                clarification_question=ambiguity.clarification_question,
                clarification_options=ambiguity.options
            )
            chat.messages.append(assistant_msg)
            return assistant_msg

        return self._generate_validate_execute(
            chat=chat,
            user_text=user_text,
            clarification_context=None,
            ambiguity=ambiguity,
            engine=engine,
            allowed_tables=allowed_tables
        )

    def _process_clarification_response(
        self,
        chat: ChatSession,
        user_text: str,
        selected_option_id: str,
        last_assistant_msg: ChatMessage,
        engine,
        allowed_tables
    ) -> ChatMessage:
        ambiguity = last_assistant_msg.ambiguity
        selected_opt = clarification_engine.resolve_clarification(ambiguity, selected_option_id)

        if not selected_opt:
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            err_msg = ChatMessage(
                id=str(uuid.uuid4()),
                sender="assistant",
                text="Invalid clarification choice selected.",
                timestamp=timestamp,
                status="error",
                error=f"Clarification option '{selected_option_id}' not recognized."
            )
            chat.messages.append(err_msg)
            return err_msg

        clarification_context = clarification_engine.build_resolved_prompt_context(
            original_question=user_text,
            clarification_question=last_assistant_msg.clarification_question or "",
            selected_option=selected_opt
        )

        return self._generate_validate_execute(
            chat=chat,
            user_text=user_text,
            clarification_context=clarification_context,
            ambiguity=ambiguity,
            engine=engine,
            allowed_tables=allowed_tables
        )

    def _generate_validate_execute(
        self,
        chat: ChatSession,
        user_text: str,
        clarification_context: Optional[str],
        ambiguity: Optional[AmbiguityResponse],
        engine,
        allowed_tables
    ) -> ChatMessage:
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        history_summary = self._build_chat_history_summary(chat)

        sql_res = sql_generator.generate(
            question=user_text,
            clarification_context=clarification_context,
            chat_history_summary=history_summary,
            engine=engine
        )

        is_valid, clean_sql, val_msg, tables_used = sql_validator.validate_and_sanitize(
            sql_res.sql,
            dynamic_allowed_tables=allowed_tables
        )

        if not is_valid:
            msg = ChatMessage(
                id=str(uuid.uuid4()),
                sender="assistant",
                text=f"Query blocked by SQL safety guardrail: {val_msg}",
                timestamp=timestamp,
                status="error",
                ambiguity=ambiguity,
                sql=sql_res.sql,
                explanation=sql_res.explanation,
                tables_used=tables_used,
                error=val_msg
            )
            chat.messages.append(msg)
            return msg

        success, columns, rows, duration_ms, summary, exec_error = query_executor.execute(
            clean_sql,
            engine=engine
        )

        if not success:
            msg = ChatMessage(
                id=str(uuid.uuid4()),
                sender="assistant",
                text=f"Database execution error: {exec_error}",
                timestamp=timestamp,
                status="error",
                ambiguity=ambiguity,
                sql=clean_sql,
                explanation=sql_res.explanation,
                tables_used=tables_used,
                error=exec_error
            )
            chat.messages.append(msg)
            return msg

        msg = ChatMessage(
            id=str(uuid.uuid4()),
            sender="assistant",
            text=summary,
            timestamp=timestamp,
            status="completed",
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
        chat.messages.append(msg)
        return msg

    def _get_last_clarification_prompt(self, chat: ChatSession) -> Optional[ChatMessage]:
        for msg in reversed(chat.messages):
            if msg.sender == "assistant" and msg.status == "clarification_required":
                return msg
        return None

    def _build_chat_history_summary(self, chat: ChatSession) -> str:
        turns = []
        for msg in chat.messages[-6:]:
            if msg.sender == "user":
                turns.append(f"User: {msg.text}")
            elif msg.sender == "assistant" and msg.sql:
                turns.append(f"Assistant SQL executed: {msg.sql}")
        return "\n".join(turns)


chat_manager = ChatManager()
