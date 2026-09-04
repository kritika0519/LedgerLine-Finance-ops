from pathlib import Path
from typing import Any

import pandas as pd

from src.config import PROCESSED_DIR
from src.ml.risk_scoring import add_unified_risk_columns


RESULTS_FILE = PROCESSED_DIR / "ml_risk_results.csv"
REQUIRED_COLUMNS = {
    "transaction_id",
    "final_status",
    "exception_type",
    "risk_level",
    "is_exception",
}


class ResultsService:
    def __init__(self, results_file: Path = RESULTS_FILE):
        self.results_file = Path(results_file)

    def load(self) -> pd.DataFrame:
        if not self.results_file.exists():
            raise FileNotFoundError("Reconciliation results are unavailable.")

        try:
            results = pd.read_csv(self.results_file)
        except (OSError, pd.errors.ParserError, UnicodeDecodeError) as exc:
            raise ValueError("Reconciliation results are invalid.") from exc

        if results.empty:
            raise ValueError("Reconciliation results are empty.")

        missing = REQUIRED_COLUMNS - set(results.columns)
        if missing:
            raise ValueError("Reconciliation results have an invalid schema.")

        if results["transaction_id"].duplicated().any():
            raise ValueError("Reconciliation results contain duplicate transactions.")

        if "ml_risk_probability" not in results.columns:
            results["ml_risk_probability"] = 0.0
        if "ml_prediction" not in results.columns:
            results["ml_prediction"] = 0
        results = add_unified_risk_columns(results)
        if "top_risk_factors" not in results.columns:
            results["top_risk_factors"] = results.get("ml_reason", "")
        return results

    @staticmethod
    def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
        clean = frame.where(pd.notna(frame), None)
        return clean.to_dict(orient="records")

    def summary(self) -> dict[str, Any]:
        results = self.load()
        total = len(results)
        exceptions = results[results["is_exception"].astype(bool)]
        return {
            "total_transactions": total,
            "matched_transactions": int((results["final_status"] == "MATCHED").sum()),
            "exception_count": len(exceptions),
            "exception_rate": round(len(exceptions) / total, 4),
            "risk_distribution": results["risk_level"].value_counts().astype(int).to_dict(),
            "exception_distribution": exceptions["exception_type"].value_counts().astype(int).to_dict(),
        }

    def query(
        self,
        *,
        final_status: str | None = None,
        exception_type: str | None = None,
        risk_level: str | None = None,
        ml_prediction: int | None = None,
        page: int = 1,
        page_size: int = 50,
        exceptions_only: bool = False,
        sort_by: str = "risk_score",
        descending: bool = True,
    ) -> tuple[list[dict[str, Any]], int]:
        results = self.load()
        if final_status:
            results = results[results["final_status"].str.upper() == final_status.upper()]
        if exception_type:
            results = results[results["exception_type"].str.upper() == exception_type.upper()]
        if risk_level:
            results = results[results["risk_level"].str.upper() == risk_level.upper()]
        if ml_prediction is not None:
            results = results[results["ml_prediction"] == ml_prediction]
        if exceptions_only:
            results = results[results["is_exception"].astype(bool)]

        allowed_sort = {"risk_score", "ml_risk_probability", "date_difference", "amount_difference"}
        results = results.sort_values(
            sort_by if sort_by in allowed_sort else "risk_score",
            ascending=not descending,
            kind="stable",
        )
        total = len(results)
        start = (page - 1) * page_size
        return self._records(results.iloc[start:start + page_size]), total

    def get_transaction(self, transaction_id: str) -> dict[str, Any] | None:
        results = self.load()
        match = results[results["transaction_id"].astype(str) == transaction_id]
        if match.empty:
            return None
        return self._records(match.iloc[:1])[0]