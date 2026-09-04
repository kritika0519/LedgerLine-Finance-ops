import os
import json
from urllib import error, request
from typing import Any, Protocol

from pydantic import ValidationError

from src.ai.schemas import EvidenceItem, InvestigationResponse


class InvestigationProvider(Protocol):
    name: str

    def investigate(self, evidence: dict[str, Any]) -> InvestigationResponse:
        ...


class DeterministicInvestigationProvider:
    name = "deterministic_fallback"

    def investigate(self, evidence: dict[str, Any]) -> InvestigationResponse:
        status = str(evidence.get("final_status", "UNKNOWN")).upper()
        exception_type = str(evidence.get("exception_type", status)).upper()
        amount_difference = evidence.get("amount_difference")
        date_difference = evidence.get("date_difference")
        payment_status = evidence.get("payment_status")
        ledger_status = evidence.get("ledger_status")
        items = []

        def add(source: str, field: str, value: Any) -> None:
            if value is not None and str(value).strip().lower() not in {"", "nan", "none"}:
                items.append({"source": source, "field": field, "value": value})

        add("reconciliation", "final_status", status)
        add("reconciliation", "exception_type", exception_type)
        add("reconciliation", "amount_difference", amount_difference)
        add("reconciliation", "date_difference", date_difference)
        add("payment", "payment_status", payment_status)
        add("ledger", "ledger_status", ledger_status)

        discrepancies = []
        if status == "AMOUNT_MISMATCH" and amount_difference is not None:
            discrepancies.append(f"the recorded amount differs by {amount_difference}")
        if status == "DATE_MISMATCH" and date_difference is not None:
            discrepancies.append(f"the dates differ by {date_difference} days")
        if payment_status in {"FAILED", "REFUNDED"}:
            discrepancies.append(f"the payment status is {payment_status}")
        if ledger_status not in {None, "POSTED", "UNKNOWN", "NAN", "NONE", ""}:
            discrepancies.append(f"the ledger status is {ledger_status}")
        if status == "DUPLICATE_PAYMENT":
            discrepancies.append("the reconciliation result identifies a duplicate payment")
        if not discrepancies:
            discrepancies.append(f"the reconciliation result is {status}")

        action = str(evidence.get("recommended_action") or "MANUAL_REVIEW")
        risk = str(evidence.get("risk_level") or "UNKNOWN").upper()
        confidence = "HIGH" if len(items) >= 2 and risk in {"HIGH", "CRITICAL"} else "MEDIUM" if items else "LOW"
        factors = evidence.get("top_risk_factors")
        notes = [f"Review the recorded evidence before taking action: {action.replace('_', ' ').lower()}."]
        if factors:
            notes.append(f"Existing risk factors: {factors}")

        return InvestigationResponse(
            transaction_id=str(evidence["transaction_id"]),
            final_status=status,
            summary=f"{exception_type.replace('_', ' ').title()} was recorded for this transaction.",
            reason="This transaction was flagged because " + " and ".join(discrepancies) + ".",
            evidence=[EvidenceItem(**item) for item in items],
            recommended_action=action,
            recommendation_explanation="This is the existing deterministic operational recommendation; the investigation layer does not replace it.",
            confidence=confidence,
            confidence_basis=f"Based on {len(items)} non-empty fields returned by the reconciliation API; no statistical probability is asserted.",
            analyst_notes=notes,
            provider=self.name,
        )


class OpenAIInvestigationProvider:
    name = "llm"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 15.0,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _payload(self, evidence: dict[str, Any]) -> dict[str, Any]:
        return {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a finance operations investigation assistant. "
                        "Use only the JSON evidence supplied by the user. "
                        "Return only valid JSON with keys: summary, reason, "
                        "evidence, recommendation_explanation, confidence, "
                        "confidence_basis, analyst_notes. Evidence must contain "
                        "only exact source, field, and value pairs from the input. "
                        "Do not change final_status or recommended_action. Do not "
                        "invent missing amounts, dates, actions, or facts."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(evidence, ensure_ascii=True, default=str),
                },
            ],
        }

    def _call(self, evidence: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(self._payload(evidence)).encode("utf-8")
        http_request = request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout) as response:
                response_body = json.loads(response.read().decode("utf-8"))
        except (error.URLError, error.HTTPError, TimeoutError, OSError) as exc:
            raise RuntimeError("LLM provider request failed.") from exc

        try:
            content = response_body["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("LLM provider returned malformed output.") from exc

    def investigate(self, evidence: dict[str, Any]) -> InvestigationResponse:
        raw = self._call(evidence)
        supplied = {
            (str(key), str(value))
            for key, value in evidence.items()
            if key not in {"ground_truth"} and not key.startswith("expected_")
        }
        raw_evidence = raw.get("evidence")
        if not isinstance(raw_evidence, list):
            raise ValueError("LLM provider returned invalid evidence.")
        for item in raw_evidence:
            if not isinstance(item, dict):
                raise ValueError("LLM provider returned invalid evidence.")
            field = str(item.get("field"))
            value = str(item.get("value"))
            if (field, value) not in supplied:
                raise ValueError("LLM provider returned unsupported evidence.")

        try:
            result = InvestigationResponse(
                transaction_id=str(evidence["transaction_id"]),
                final_status=str(evidence["final_status"]),
                summary=raw["summary"],
                reason=raw["reason"],
                evidence=[EvidenceItem(**item) for item in raw_evidence],
                recommended_action=str(evidence.get("recommended_action") or "MANUAL_REVIEW"),
                recommendation_explanation=raw["recommendation_explanation"],
                confidence=raw["confidence"],
                confidence_basis=raw["confidence_basis"],
                analyst_notes=raw["analyst_notes"],
                provider=self.name,
            )
        except (KeyError, TypeError, ValidationError) as exc:
            raise ValueError("LLM provider returned an invalid investigation.") from exc
        return result


class GeminiInvestigationProvider:
    name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout: float = 15.0,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _payload(self, evidence: dict[str, Any]) -> dict[str, Any]:
        return {
            "systemInstruction": {
                "parts": [{
                    "text": (
                        "You are a finance operations investigation assistant. "
                        "Use only the JSON transaction evidence supplied. Return "
                        "only valid JSON with keys: summary, reason, evidence, "
                        "recommendation_explanation, confidence, confidence_basis, "
                        "analyst_notes. Evidence must contain only exact source, "
                        "field, and value pairs from the input. Never change "
                        "final_status or recommended_action. Never invent missing "
                        "amounts, dates, actions, or facts."
                    )
                }]
            },
            "contents": [{
                "role": "user",
                "parts": [{
                    "text": json.dumps(evidence, ensure_ascii=True, default=str)
                }]
            }],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
            },
        }

    def _call(self, evidence: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(self._payload(evidence)).encode("utf-8")
        http_request = request.Request(
            f"{self.base_url}/models/{self.model}:generateContent",
            data=body,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            },
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout) as response:
                response_body = json.loads(response.read().decode("utf-8"))
        except (error.URLError, error.HTTPError, TimeoutError, OSError) as exc:
            raise RuntimeError("Gemini provider request failed.") from exc

        try:
            content = response_body["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Gemini provider returned malformed output.") from exc

    def investigate(self, evidence: dict[str, Any]) -> InvestigationResponse:
        raw = self._call(evidence)
        supplied = {
            (str(key), str(value))
            for key, value in evidence.items()
            if key != "ground_truth" and not key.startswith("expected_")
        }
        raw_evidence = raw.get("evidence")
        if not isinstance(raw_evidence, list):
            raise ValueError("Gemini provider returned invalid evidence.")
        for item in raw_evidence:
            if not isinstance(item, dict):
                raise ValueError("Gemini provider returned invalid evidence.")
            field = str(item.get("field"))
            value = str(item.get("value"))
            if (field, value) not in supplied:
                raise ValueError("Gemini provider returned unsupported evidence.")

        confidence = str(raw.get("confidence", "")).strip().upper()
        confidence = next(
            (level for level in ("HIGH", "MEDIUM", "LOW") if level in confidence),
            "",
        )
        analyst_notes = raw.get("analyst_notes")
        if isinstance(analyst_notes, str):
            analyst_notes = [analyst_notes]

        try:
            return InvestigationResponse(
                transaction_id=str(evidence["transaction_id"]),
                final_status=str(evidence["final_status"]),
                summary=raw["summary"],
                reason=raw["reason"],
                evidence=[EvidenceItem(**item) for item in raw_evidence],
                recommended_action=str(evidence.get("recommended_action") or "MANUAL_REVIEW"),
                recommendation_explanation=raw["recommendation_explanation"],
                confidence=confidence,
                confidence_basis=raw["confidence_basis"],
                analyst_notes=analyst_notes,
                provider=self.name,
            )
        except (KeyError, TypeError, ValidationError) as exc:
            raise ValueError("Gemini provider returned an invalid investigation.") from exc


def configured_provider() -> InvestigationProvider:
    provider = os.getenv("AI_INVESTIGATION_PROVIDER", "deterministic").strip().lower()
    if provider in {"", "deterministic", "fallback"}:
        return DeterministicInvestigationProvider()
    if provider == "openai" and os.getenv("OPENAI_API_KEY"):
        return OpenAIInvestigationProvider(
            api_key=os.environ["OPENAI_API_KEY"],
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            timeout=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "15")),
        )
    if provider == "gemini" and os.getenv("GEMINI_API_KEY"):
        return GeminiInvestigationProvider(
            api_key=os.environ["GEMINI_API_KEY"],
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            timeout=float(os.getenv("GEMINI_TIMEOUT_SECONDS", "15")),
        )
    return DeterministicInvestigationProvider()