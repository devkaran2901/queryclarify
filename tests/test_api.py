import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "degraded"]
    assert "database" in data


def test_schema_endpoint():
    response = client.get("/api/schema")
    assert response.status_code == 200
    data = response.json()
    assert "TABLE customers" in data["schema"]
    assert "TABLE orders" in data["schema"]


def test_unambiguous_query_flow():
    payload = {"question": "Show all customers from India."}
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "sql" in data
    assert "SELECT" in data["sql"].upper()
    assert isinstance(data["rows"], list)


def test_ambiguous_query_and_clarification_flow():
    # Turn 1: Ambiguous query submission
    payload1 = {"question": "Who is our best customer?"}
    res1 = client.post("/api/query", json=payload1)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "clarification_required"
    assert data1["clarification_question"] is not None
    assert len(data1["clarification_options"]) >= 2
    
    session_id = data1["session_id"]
    selected_option = data1["clarification_options"][0]["id"]

    # Turn 2: Clarification choice submission
    payload2 = {
        "session_id": session_id,
        "question": "Who is our best customer?",
        "selected_option": selected_option
    }
    res2 = client.post("/api/query", json=payload2)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "completed"
    assert data2["sql"] is not None
    assert isinstance(data2["rows"], list)
