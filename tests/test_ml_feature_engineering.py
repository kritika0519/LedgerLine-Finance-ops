import pandas as pd

from src.ml.feature_engineering import (
    build_feature_frame,
    create_high_attention_target,
)


def test_high_attention_target_uses_business_risk_rules():
    df = pd.DataFrame(
        [
            {
                "final_status": "MATCHED",
                "date_difference": 0,
            },
            {
                "final_status": "DATE_MISMATCH",
                "date_difference": 2,
            },
            {
                "final_status": "DATE_MISMATCH",
                "date_difference": 12,
            },
            {
                "final_status": "PAYMENT_FAILED",
                "date_difference": 0,
            },
        ]
    )

    assert create_high_attention_target(df).tolist() == [0, 0, 1, 1]


def test_feature_frame_excludes_identity_and_label_columns():
    df = pd.DataFrame(
        [
            {
                "transaction_id": "TXN0001",
                "payment_id": "PAY0001",
                "final_status": "MATCHED",
                "amount_match": True,
                "date_match": True,
                "ledger_found": True,
                "ledger_status": "POSTED",
                "payment_status": "SUCCESS",
                "date_severity": "NO_DATE_EXCEPTION",
                "match_status": "MATCHED",
                "bank_amount": 100,
                "payment_amount": 100,
                "amount_difference": 0,
                "absolute_amount_difference": 0,
                "date_difference": 0,
            }
        ]
    )

    feature_frame, feature_columns = build_feature_frame(df)

    assert "transaction_id" not in feature_columns
    assert "payment_id" not in feature_columns
    assert "final_status" not in feature_columns
    assert feature_frame["high_attention"].tolist() == [0]
    assert "transaction_payment_id_delta" in feature_columns
