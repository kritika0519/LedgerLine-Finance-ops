import pandas as pd

from src.ml.risk_scoring import add_unified_risk_columns


def test_unified_risk_score_preserves_reconciliation_status():
    result = add_unified_risk_columns(
        pd.DataFrame(
            [
                {
                    "transaction_id": "TXN0001",
                    "final_status": "DATE_MISMATCH",
                    "absolute_amount_difference": 0,
                    "date_difference": 12,
                    "ml_risk_probability": 0.8,
                }
            ]
        )
    )

    assert result.loc[0, "final_status"] == "DATE_MISMATCH"
    assert result.loc[0, "risk_score"] > 0
    assert result.loc[0, "risk_level"] in {
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
    }