import pytest
from app.services.sql_validator import sql_validator


def test_valid_select_query():
    sql = "SELECT id, name, country FROM customers WHERE country = 'India'"
    is_valid, sanitized_sql, msg, tables = sql_validator.validate_and_sanitize(sql)
    assert is_valid is True
    assert "LIMIT" in sanitized_sql
    assert "customers" in tables


def test_reject_drop_table():
    sql = "DROP TABLE customers;"
    is_valid, _, msg, _ = sql_validator.validate_and_sanitize(sql)
    assert is_valid is False
    assert "Only SELECT queries are allowed" in msg or "Forbidden" in msg or "invalid" in msg


def test_reject_delete_from():
    sql = "DELETE FROM orders WHERE id = 1"
    is_valid, _, msg, _ = sql_validator.validate_and_sanitize(sql)
    assert is_valid is False
    assert "Only SELECT queries are allowed" in msg or "Forbidden" in msg


def test_reject_update():
    sql = "UPDATE products SET price = 0 WHERE id = 1"
    is_valid, _, msg, _ = sql_validator.validate_and_sanitize(sql)
    assert is_valid is False


def test_reject_multi_statement_injection():
    sql = "SELECT * FROM customers; DELETE FROM customers;"
    is_valid, _, msg, _ = sql_validator.validate_and_sanitize(sql)
    assert is_valid is False
    assert "Multi-statement" in msg or "multiple" in msg


def test_reject_invalid_table_name():
    sql = "SELECT * FROM secret_admin_passwords"
    is_valid, _, msg, _ = sql_validator.validate_and_sanitize(sql)
    assert is_valid is False
    assert "do not exist in the" in msg
