import json

import pandas as pd
import pytest

from src.ai.providers import GeminiInvestigationProvider, OpenAIInvestigationProvider
from src.ai.service import InvestigationService
from src.api.services import ResultsService


def test_fallback_investigation_is_evidence_based_and_preserves_status(tmp_path):
    output = tmp_path / "results.csv"
    pd.DataFrame([{
        "transaction_id": "TXN42",
        "final_status": "AMOUNT_MISMATCH",
        "exception_type": "AMOUNT_MISMATCH",
        "risk_level": "HIGH",
        "is_exception": True,
        "amount_difference": 12.5,
        "date_difference": 0,
        "payment_status": "SUCCESS",
        "ledger_status": "POSTED",
        "recommended_action": "INVESTIGATE_AMOUNT_DIFFERENCE",
        "ml_risk_probability": 0.8,
    }]).to_csv(output, index=False)

    result = InvestigationService(ResultsService(output)).investigate("TXN42")

    assert result is not None
    assert result.provider == "deterministic_fallback"
    assert result.final_status == "AMOUNT_MISMATCH"
    assert any(item.field == "amount_difference" and item.value == 12.5 for item in result.evidence)
    assert result.recommended_action == "INVESTIGATE_AMOUNT_DIFFERENCE"
    assert all("ground_truth" not in item.model_dump_json() for item in result.evidence)


def test_llm_provider_sends_only_supplied_evidence(monkeypatch):
    provider = OpenAIInvestigationProvider("test-key")
    captured = {}

    def fake_call(evidence):
        captured.update(evidence)
        return {
            "summary": "An amount variance was recorded.",
            "reason": "The supplied amount difference explains the exception.",
            "evidence": [{"source": "reconciliation", "field": "amount_difference", "value": 12.5}],
            "recommendation_explanation": "Follow the existing action.",
            "confidence": "HIGH",
            "confidence_basis": "Two supplied evidence fields support this review.",
            "analyst_notes": ["Compare the source records."],
        }

    monkeypatch.setattr(provider, "_call", fake_call)
    result = provider.investigate({
        "transaction_id": "TXN42",
        "final_status": "AMOUNT_MISMATCH",
        "amount_difference": 12.5,
        "recommended_action": "INVESTIGATE_AMOUNT_DIFFERENCE",
    })

    assert result.provider == "llm"
    assert result.final_status == "AMOUNT_MISMATCH"
    assert result.recommended_action == "INVESTIGATE_AMOUNT_DIFFERENCE"
    assert "ground_truth" not in captured


@pytest.mark.parametrize("failure", [RuntimeError("network"), ValueError("malformed")])
def test_provider_failure_falls_back_to_deterministic(monkeypatch, failure):
    provider = OpenAIInvestigationProvider("test-key")
    monkeypatch.setattr(provider, "investigate", lambda evidence: (_ for _ in ()).throw(failure))
    monkeypatch.setattr("src.ai.service.configured_provider", lambda: provider)

    result = InvestigationService().investigate("TXN0001")

    assert result is not None
    assert result.provider == "deterministic_fallback"
    assert result.final_status == "DATE_MISMATCH"


def test_llm_malformed_evidence_is_rejected(monkeypatch):
    provider = OpenAIInvestigationProvider("test-key")
    monkeypatch.setattr(provider, "_call", lambda evidence: {
        "summary": "Unsupported.",
        "reason": "Unsupported.",
        "evidence": [{"source": "invented", "field": "amount", "value": 999}],
        "recommendation_explanation": "Unsupported.",
        "confidence": "HIGH",
        "confidence_basis": "Unsupported.",
        "analyst_notes": [],
    })

    with pytest.raises(ValueError):
        provider.investigate({"transaction_id": "TXN42", "final_status": "MATCHED"})


def test_gemini_provider_parses_structured_response_and_preserves_authority(monkeypatch):
    provider = GeminiInvestigationProvider("test-gemini-key", model="gemini-test")
    captured = {}

    def fake_call(evidence):
        captured.update(provider._payload(evidence))
        return {
            "summary": "A payment amount variance was recorded.",
            "reason": "The supplied amount difference explains the exception.",
            "evidence": [{"source": "reconciliation", "field": "amount_difference", "value": 12.5}],
            "recommendation_explanation": "Follow the recorded action.",
            "confidence": "HIGH",
            "confidence_basis": "The amount difference is explicitly supplied.",
            "analyst_notes": ["Compare the source amounts."],
        }

    monkeypatch.setattr(provider, "_call", fake_call)
    result = provider.investigate({
        "transaction_id": "TXN42",
        "final_status": "AMOUNT_MISMATCH",
        "amount_difference": 12.5,
        "recommended_action": "INVESTIGATE_AMOUNT_DIFFERENCE",
    })

    assert result.provider == "gemini"
    assert result.final_status == "AMOUNT_MISMATCH"
    assert result.recommended_action == "INVESTIGATE_AMOUNT_DIFFERENCE"
    assert captured["generationConfig"]["responseMimeType"] == "application/json"
    assert "ground_truth" not in json.dumps(captured)


def test_gemini_failure_falls_back_to_deterministic(monkeypatch):
    provider = GeminiInvestigationProvider("test-gemini-key")
    monkeypatch.setattr(provider, "investigate", lambda evidence: (_ for _ in ()).throw(RuntimeError("timeout")))
    monkeypatch.setattr("src.ai.service.configured_provider", lambda: provider)

    result = InvestigationService().investigate("TXN0001")

    assert result is not None
    assert result.provider == "deterministic_fallback"
    assert result.final_status == "DATE_MISMATCH"