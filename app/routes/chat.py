import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Header, status
from app.models.chat_schemas import ChatSession, ChatMessage, SendMessageRequest
from app.services.chat_manager import chat_manager

logger = logging.getLogger("routes_chat")
router = APIRouter(prefix="/api", tags=["Chat"])


@router.get("/chats", response_model=List[ChatSession])
def list_chats():
    """List all active chat sessions."""
    return chat_manager.list_chats()


@router.post("/chats", response_model=ChatSession)
def create_chat(x_session_id: Optional[str] = Header(default="default")):
    """Create a new chat session."""
    session_id = x_session_id or "default"
    return chat_manager.create_chat(db_session_id=session_id)


@router.get("/chats/{chat_id}", response_model=ChatSession)
def get_chat(chat_id: str):
    """Get chat session details by ID."""
    chat = chat_manager.get_chat(chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session '{chat_id}' not found."
        )
    return chat


@router.delete("/chats/{chat_id}")
def delete_chat(chat_id: str):
    """Delete a chat session."""
    success = chat_manager.delete_chat(chat_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session '{chat_id}' not found."
        )
    return {"message": f"Chat session '{chat_id}' deleted successfully."}


@router.post("/chat/message", response_model=ChatMessage)
def send_chat_message(req: SendMessageRequest):
    """Send user message or clarification choice within chat session."""
    if not req.message and not req.selected_option:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content or selected_option must be provided."
        )

    try:
        msg = chat_manager.send_message(
            chat_id=req.chat_id,
            user_text=req.message,
            selected_option_id=req.selected_option
        )
        return msg
    except Exception as e:
        logger.error(f"Error sending chat message: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat message: {str(e)}"
        )
