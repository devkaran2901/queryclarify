import pytest
from app.services.ambiguity_detector import ambiguity_detector


def test_unambiguous_query_detection():
    question = "Show all customers from India."
    res = ambiguity_detector.analyze(question)
    assert res.ambiguous is False
    assert res.clarification_question is None


def test_ambiguous_query_detection_best_customer():
    question = "Who is our best customer?"
    res = ambiguity_detector.analyze(question)
    assert res.ambiguous is True
    assert res.ambiguity_type in ["metric", "ranking"]
    assert res.clarification_question is not None
    assert len(res.options) >= 2


def test_ambiguous_query_detection_recent_sales():
    question = "Show recent sales."
    res = ambiguity_detector.analyze(question)
    assert res.ambiguous is True
    assert res.ambiguity_type in ["time", "filter"]
    assert res.clarification_question is not None
