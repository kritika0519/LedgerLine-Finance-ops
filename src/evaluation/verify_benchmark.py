from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    GROUND_TRUTH_FILE,
    PROCESSED_DIR,
    STATUS_TO_GROUND_TRUTH,
)


RECONCILIATION_FILE = PROCESSED_DIR / "reconciliation_results.csv"


def load_inputs(
    reconciliation_file=RECONCILIATION_FILE,
    ground_truth_file=GROUND_TRUTH_FILE,
):
    reconciliation_file = Path(reconciliation_file)
    ground_truth_file = Path(ground_truth_file)

    if not reconciliation_file.exists():
        raise FileNotFoundError(
            f"Reconciliation file not found: {reconciliation_file}"
        )

    if not ground_truth_file.exists():
        raise FileNotFoundError(
            f"Ground truth file not found: {ground_truth_file}"
        )

    return (
        pd.read_csv(reconciliation_file),
        pd.read_csv(ground_truth_file),
    )


def verify_reconciliation(reconciliation, ground_truth):
    required_recon = {"transaction_id", "payment_id", "final_status"}
    required_truth = {
        "transaction_id",
        "payment_id",
        "expected_final_decision",
    }

    missing_recon = required_recon - set(reconciliation.columns)
    missing_truth = required_truth - set(ground_truth.columns)

    if missing_recon:
        raise ValueError(
            f"Missing reconciliation columns: {sorted(missing_recon)}"
        )

    if missing_truth:
        raise ValueError(
            f"Missing ground truth columns: {sorted(missing_truth)}"
        )

    if reconciliation["transaction_id"].duplicated().any():
        raise ValueError("Duplicate transaction_id in reconciliation output.")

    if ground_truth["transaction_id"].duplicated().any():
        raise ValueError("Duplicate transaction_id in ground truth.")

    recon = reconciliation[
        ["transaction_id", "payment_id", "final_status"]
    ].copy()

    recon["actual_final_decision"] = recon["final_status"].map(
        STATUS_TO_GROUND_TRUTH
    )

    merged = recon.merge(
        ground_truth[
            ["transaction_id", "payment_id", "expected_final_decision"]
        ],
        on="transaction_id",
        how="outer",
        suffixes=("_actual", "_expected"),
        indicator=True,
    )

    decision_mismatches = merged[
        (merged["_merge"] != "both")
        | (
            merged["actual_final_decision"]
            != merged["expected_final_decision"]
        )
    ].copy()

    payment_assignment_differences = merged[
        (merged["_merge"] == "both")
        & (
            merged["actual_final_decision"]
            == merged["expected_final_decision"]
        )
        & (
            merged["payment_id_actual"].fillna("")
            != merged["payment_id_expected"].fillna("")
        )
    ].copy()

    matched_payments = reconciliation[
        reconciliation["final_status"] == "MATCHED"
    ]["payment_id"].dropna()

    duplicate_matched_payments = int(
        matched_payments.duplicated().sum()
    )

    return {
        "total_reconciliation_rows": len(reconciliation),
        "total_ground_truth_rows": len(ground_truth),
        "decision_mismatch_count": len(decision_mismatches),
        "payment_assignment_difference_count": len(
            payment_assignment_differences
        ),
        "duplicate_transaction_rows": int(
            reconciliation["transaction_id"].duplicated().sum()
        ),
        "duplicate_matched_payments": duplicate_matched_payments,
        "decision_mismatches": decision_mismatches,
        "payment_assignment_differences": (
            payment_assignment_differences
        ),
    }


def main():
    reconciliation, ground_truth = load_inputs()
    report = verify_reconciliation(reconciliation, ground_truth)

    print("=" * 70)
    print("GROUND TRUTH VERIFICATION")
    print("=" * 70)
    print(
        "Reconciliation rows : "
        f"{report['total_reconciliation_rows']}"
    )
    print(
        "Ground truth rows    : "
        f"{report['total_ground_truth_rows']}"
    )
    print(
        "FINAL DECISION MISMATCH COUNT: "
        f"{report['decision_mismatch_count']}"
    )
    print(
        "Payment assignment differences: "
        f"{report['payment_assignment_difference_count']}"
    )
    print(
        "Duplicate tx rows   : "
        f"{report['duplicate_transaction_rows']}"
    )
    print(
        "Duplicate MATCHED payments: "
        f"{report['duplicate_matched_payments']}"
    )

    if report["decision_mismatch_count"] > 0:
        print("\nFirst final decision mismatches:")
        print(
            report["decision_mismatches"]
            .head(20)
            .to_string(index=False)
        )
        raise SystemExit(1)

    if report["payment_assignment_difference_count"] > 0:
        print("\nPayment assignment differences are informational:")
        print(
            report["payment_assignment_differences"]
            .head(20)
            .to_string(index=False)
        )

    if report["duplicate_matched_payments"] > 0:
        raise SystemExit(1)

    print("\nPASS: Final decisions match ground truth.")


if __name__ == "__main__":
    main()
