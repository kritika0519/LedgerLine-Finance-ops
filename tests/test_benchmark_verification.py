import pandas as pd

from src.evaluation.verify_benchmark import verify_reconciliation


def test_verify_reconciliation_accepts_matching_rows():
    reconciliation = pd.DataFrame(
        [
            {
                "transaction_id": "TXN0001",
                "payment_id": "PAY0001",
                "final_status": "MATCHED",
            }
        ]
    )
    ground_truth = pd.DataFrame(
        [
            {
                "transaction_id": "TXN0001",
                "payment_id": "PAY0001",
                "expected_final_decision": "CLEAN_MATCH",
            }
        ]
    )

    report = verify_reconciliation(reconciliation, ground_truth)

    assert report["decision_mismatch_count"] == 0


def test_verify_reconciliation_reports_status_mismatches():
    reconciliation = pd.DataFrame(
        [
            {
                "transaction_id": "TXN0001",
                "payment_id": "PAY0001",
                "final_status": "DATE_MISMATCH",
            }
        ]
    )
    ground_truth = pd.DataFrame(
        [
            {
                "transaction_id": "TXN0001",
                "payment_id": "PAY0001",
                "expected_final_decision": "CLEAN_MATCH",
            }
        ]
    )

    report = verify_reconciliation(reconciliation, ground_truth)

    assert report["decision_mismatch_count"] == 1


def test_verify_reconciliation_separates_payment_assignment_differences():
    reconciliation = pd.DataFrame(
        [
            {
                "transaction_id": "TXN0001",
                "payment_id": "PAY9999",
                "final_status": "DUPLICATE_PAYMENT",
            }
        ]
    )
    ground_truth = pd.DataFrame(
        [
            {
                "transaction_id": "TXN0001",
                "payment_id": "PAY0001",
                "expected_final_decision": "DUPLICATE_PAYMENT",
            }
        ]
    )

    report = verify_reconciliation(reconciliation, ground_truth)

    assert report["decision_mismatch_count"] == 0
    assert report["payment_assignment_difference_count"] == 1
