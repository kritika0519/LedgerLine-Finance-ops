from typing import Any

from src.ai.providers import (
    DeterministicInvestigationProvider,
    configured_provider,
)
from src.ai.schemas import InvestigationResponse
from src.api.services import ResultsService


class InvestigationService:
    def __init__(self, results_service: ResultsService | None = None):
        self.results_service = results_service or ResultsService()

    def investigate(self, transaction_id: str) -> InvestigationResponse | None:
        transaction = self.results_service.get_transaction(transaction_id)
        if transaction is None:
            return None

        evidence: dict[str, Any] = {
            key: value for key, value in transaction.items()
            if key != "ground_truth" and not key.startswith("expected_")
        }
        provider = configured_provider()
        try:
            return provider.investigate(evidence)
        except (RuntimeError, ValueError, KeyError, TypeError):
            return DeterministicInvestigationProvider().investigate(evidence)