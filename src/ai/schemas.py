from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class EvidenceItem(BaseModel):
    source: str
    field: str
    value: Any


class InvestigationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: str
    final_status: str
    summary: str
    reason: str
    evidence: list[EvidenceItem]
    recommended_action: str
    recommendation_explanation: str
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    confidence_basis: str
    analyst_notes: list[str]
    provider: Literal["deterministic_fallback", "llm", "gemini"]