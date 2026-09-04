import pandas as pd

from src.reconciliation.exception_classifier import (
    classify_exception_type,
    classify_risk_level,
    determine_action,
)


def test_payment_failed_is_a_first_class_exception():
    row = pd.Series({"final_status": "PAYMENT_FAILED"})

    assert classify_exception_type(row) == "PAYMENT_FAILED"


def test_payment_refunded_is_a_first_class_exception():
    row = pd.Series({"final_status": "PAYMENT_REFUNDED"})

    assert classify_exception_type(row) == "PAYMENT_REFUNDED"


def test_payment_exceptions_are_high_risk_with_specific_actions():
    failed = pd.Series(
        {
            "exception_type": "PAYMENT_FAILED",
            "date_severity": "NOT_APPLICABLE",
            "risk_level": "HIGH",
        }
    )
    refunded = pd.Series(
        {
            "exception_type": "PAYMENT_REFUNDED",
            "date_severity": "NOT_APPLICABLE",
            "risk_level": "HIGH",
        }
    )

    assert classify_risk_level(failed) == "HIGH"
    assert determine_action(failed) == "INVESTIGATE_FAILED_PAYMENT"
    assert determine_action(refunded) == "REVIEW_REFUND"
