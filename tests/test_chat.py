import pytest
from app.services.chat_manager import chat_manager


def test_create_and_list_chats():
    chat = chat_manager.create_chat(title="Test Chat Session")
    assert chat.id is not None
    assert chat.title == "Test Chat Session"

    all_chats = chat_manager.list_chats()
    assert any(c.id == chat.id for c in all_chats)


def test_chat_message_flow():
    chat = chat_manager.create_chat(title="Query Flow Test")
    
    # Send unambiguous question
    msg = chat_manager.send_message(
        chat_id=chat.id,
        user_text="Show all customers from India."
    )
    assert msg.sender == "assistant"
    assert msg.status == "completed"
    assert msg.sql is not None
    assert "customers" in msg.tables_used


def test_chat_ambiguity_and_clarification_flow():
    chat = chat_manager.create_chat(title="Ambiguity Flow Test")
    
    # Send ambiguous question
    msg1 = chat_manager.send_message(
        chat_id=chat.id,
        user_text="Who is our best customer?"
    )
    assert msg1.sender == "assistant"
    assert msg1.status == "clarification_required"
    assert msg1.clarification_question is not None
    assert len(msg1.clarification_options) >= 2

    # Send clarification option response
    selected_opt = msg1.clarification_options[0].id
    msg2 = chat_manager.send_message(
        chat_id=chat.id,
        user_text="Who is our best customer?",
        selected_option_id=selected_opt
    )
    assert msg2.sender == "assistant"
    assert msg2.status == "completed"
    assert msg2.sql is not None


def test_delete_chat():
    chat = chat_manager.create_chat(title="Delete Test")
    chat_id = chat.id
    assert chat_manager.get_chat(chat_id) is not None

    deleted = chat_manager.delete_chat(chat_id)
    assert deleted is True
    assert chat_manager.get_chat(chat_id) is None
