import pytest

from app.services.answer_metrics import (
    abstention_success_rate,
    answerability_accuracy,
    citation_document_accuracy,
    citation_validity_rate,
    unsupported_claim_rate,
)


def test_answerability_and_abstention_metrics():
    expected = [True, False, False]
    predicted = [True, False, True]
    assert answerability_accuracy(expected, predicted) == pytest.approx(2 / 3)
    assert abstention_success_rate(expected, predicted) == 0.5


def test_citation_metrics():
    assert citation_validity_rate(["S1", "S9"], {"S1", "S2"}) == 0.5
    assert citation_validity_rate([], {"S1"}) == 1.0
    assert citation_document_accuracy({"a", "other"}, {"a", "b"}) == 0.5


def test_unsupported_claim_rate():
    assert unsupported_claim_rate([True, False, True]) == pytest.approx(1 / 3)
    assert unsupported_claim_rate([]) == 0.0
