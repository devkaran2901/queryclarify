import pytest
from app.services.connection_manager import connection_manager
from app.database.schema_inspector import schema_inspector


def test_test_connection_invalid_credentials():
    success, msg = connection_manager.test_connection(
        host="localhost",
        port=5435,
        database="non_existent_db_12345",
        username="invalid_user",
        password="wrong_password"
    )
    assert success is False
    assert "Authentication failed" in msg or "does not exist" in msg or "failed" in msg


def test_test_connection_invalid_port():
    success, msg = connection_manager.test_connection(
        host="127.0.0.1",
        port=59999,
        database="queryclarify",
        username="postgres",
        password="postgres"
    )
    assert success is False
    assert "Could not connect" in msg or "failed" in msg


def test_valid_demo_database_connection():
    success, msg = connection_manager.test_connection(
        host="localhost",
        port=5435,
        database="queryclarify",
        username="postgres",
        password="postgres"
    )
    assert success is True
    assert "Successfully connected" in msg


def test_dynamic_schema_inspection():
    engine = connection_manager.get_engine(session_id=None)
    tables = schema_inspector.get_tables(engine)
    assert "customers" in tables
    assert "orders" in tables
    assert "products" in tables
    assert "order_items" in tables

    schema_summary = schema_inspector.get_schema_summary(engine)
    assert "TABLE customers" in schema_summary
    assert "TABLE orders" in schema_summary
