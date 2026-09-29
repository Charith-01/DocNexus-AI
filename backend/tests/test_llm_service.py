from types import SimpleNamespace

import pytest

from app.schemas.answers import GroundedDraft
from app.services.llm_service import (
    GeminiService,
    LLMConfigurationError,
    LLMInvalidResponseError,
    LLMProviderUnavailableError,
)
from app.core.config import settings


class FakeModels:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


def service(models):
    return GeminiService(client=SimpleNamespace(models=models))


def test_structured_generation_uses_provider_parsed_response():
    models = FakeModels(
        SimpleNamespace(
            parsed={"answer": "Supported [S1]", "answerable": True, "cited_source_ids": ["S1"]},
            text=None,
        )
    )
    draft = service(models).generate_grounded_answer("Question?", "<EVIDENCE />")
    assert isinstance(draft, GroundedDraft)
    assert models.calls[0]["model"]
    assert "api" not in str(models.calls[0]).casefold()


def test_malformed_provider_response_fails_safely():
    models = FakeModels(SimpleNamespace(parsed=None, text="not-json"))
    with pytest.raises(LLMInvalidResponseError, match="invalid response"):
        service(models).generate_grounded_answer("Question?", "evidence")


def test_provider_failure_has_safe_error_without_provider_details():
    models = FakeModels(error=RuntimeError("secret provider diagnostic"))
    with pytest.raises(LLMProviderUnavailableError) as captured:
        service(models).generate_grounded_answer("Question?", "evidence")
    assert "secret" not in str(captured.value).casefold()


def test_missing_api_key_fails_without_exposing_a_key(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    with pytest.raises(LLMConfigurationError, match="not configured"):
        _ = GeminiService().client
