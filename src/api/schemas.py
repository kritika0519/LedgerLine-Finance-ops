from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str
    service: str
    records_available: int


class PaginatedTransactions(BaseModel):
    items: list[dict[str, Any]]
    page: int
    page_size: int
    total: int
    pages: int


class SummaryResponse(BaseModel):
    total_transactions: int
    matched_transactions: int
    exception_count: int
    exception_rate: float
    risk_distribution: dict[str, int]
    exception_distribution: dict[str, int]


class TransactionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    transaction_id: str
    payment_id: str | None = None
    final_status: str
    reason: str | None = None
    amount_match: bool | None = None
    amount_difference: float | None = None
    date_match: bool | None = None
    date_difference: float | None = None
    ledger_status: str | None = None
    payment_status: str | None = None
    exception_type: str | None = None
    deterministic_risk_score: float | None = None
    risk_level: str | None = None
    ml_risk_probability: float | None = None
    ml_prediction: int | None = None
    risk_score: float | None = None
    top_risk_factors: str | None = None
    recommended_action: str | None = None


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Safe, client-facing error message")