import os

import pytest

from dialect_mediator.core.models import MediationResult, Text

from bot.services import mediation


def test_mediate_text_requires_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(RuntimeError):
        mediation.mediate_text("hola")


def test_mediate_text_invokes_mediator(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "abc123")

    captured = {}

    class FakeMediator:
        def __init__(self, profile, llm):
            captured["profile"] = profile
            captured["llm"] = llm

        def mediate(self, text: Text) -> MediationResult:
            captured["text"] = text
            return MediationResult(mediated_text="resultado")

    class FakeGemini:
        def __init__(self, api_key: str):
            captured["api_key"] = api_key

    monkeypatch.setattr(mediation, "Mediator", FakeMediator)
    monkeypatch.setattr(mediation, "GeminiClient", FakeGemini)

    result = mediation.mediate_text("texto original")

    assert result == "resultado"
    assert captured["text"].content == "texto original"
    assert captured["api_key"] == "abc123"
    assert "profile" in captured
    assert "llm" in captured
