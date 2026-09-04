import pandas as pd

from src.reconciliation.reconciler import (
    calculate_amount_difference,
    reconcile_record,
)


def _bank_row(amount=100.0, date="2026-01-01"):
    return pd.Series(
        {
            "transaction_id": "TXN0001",
            "amount": amount,
            "transaction_date": pd.Timestamp(date),
        }
    )


def _payment_row(
    amount=100.0,
    date="2026-01-01",
    status="SUCCESS",
    invoice_id="INV0001",
    customer_id="CUST0001",
):
    return pd.Series(
        {
            "payment_id": "PAY0001",
            "amount": amount,
            "payment_date": pd.Timestamp(date),
            "payment_status": status,
            "invoice_id": invoice_id,
            "customer_id": customer_id,
        }
    )


def _exact_row(status="MATCHED", payment_id="PAY0001"):
    return pd.Series(
        {
            "transaction_id": "TXN0001",
            "payment_id": payment_id,
            "match_status": status,
        }
    )


def _ledger(status="POSTED"):
    return pd.DataFrame(
        [
            {
                "ledger_id": "LED0001",
                "invoice_id": "INV0001",
                "customer_id": "CUST0001",
                "posting_status": status,
            }
        ]
    )


def test_clean_record_reconciles_to_matched():
    result = reconcile_record(
        _exact_row(),
        _bank_row(),
        _payment_row(),
        _ledger(),
    )

    assert result["final_status"] == "MATCHED"
    assert result["amount_difference"] == 0
    assert result["date_difference"] == 0


def test_payment_failed_and_refunded_are_distinct():
    failed = reconcile_record(
        _exact_row(),
        _bank_row(),
        _payment_row(status="FAILED"),
        _ledger(),
    )
    refunded = reconcile_record(
        _exact_row(),
        _bank_row(),
        _payment_row(status="REFUNDED"),
        _ledger(),
    )

    assert failed["final_status"] == "PAYMENT_FAILED"
    assert refunded["final_status"] == "PAYMENT_REFUNDED"


def test_ledger_not_posted_is_ledger_exception():
    result = reconcile_record(
        _exact_row(),
        _bank_row(),
        _payment_row(),
        _ledger(status="PENDING"),
    )

    assert result["final_status"] == "LEDGER_EXCEPTION"
    assert "PENDING" in result["reason"]


def test_date_mismatch_preserves_day_difference():
    result = reconcile_record(
        _exact_row(),
        _bank_row(date="2026-01-03"),
        _payment_row(date="2026-01-01"),
        _ledger(),
    )

    assert result["final_status"] == "DATE_MISMATCH"
    assert result["date_difference"] == 2


def test_amount_difference_is_signed_and_rounded():
    assert calculate_amount_difference(
        _bank_row(amount=125.555),
        _payment_row(amount=100.111),
    ) == 25.44
