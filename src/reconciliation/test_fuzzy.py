from pathlib import Path
import sys

import pandas as pd


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SRC_PATH = PROJECT_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


# ============================================================
# IMPORT FUZZY MATCHER
# ============================================================

from reconciliation.fuzzy_matcher import (
    fuzzy_match,
    save_results,
)


# ============================================================
# FILE PATHS
# ============================================================

BANK_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "bank_transactions.csv"
)

PAYMENT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "payment_gateway.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "fuzzy_match_results.csv"
)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("FUZZY RECONCILIATION TEST")
    print("=" * 70)

    # --------------------------------------------------------
    # Check files
    # --------------------------------------------------------

    if not BANK_FILE.exists():
        raise FileNotFoundError(
            f"Bank file not found:\n{BANK_FILE}"
        )

    if not PAYMENT_FILE.exists():
        raise FileNotFoundError(
            f"Payment file not found:\n{PAYMENT_FILE}"
        )

    # --------------------------------------------------------
    # Load datasets
    # --------------------------------------------------------

    print("\nLoading datasets...")

    bank = pd.read_csv(BANK_FILE)

    payment = pd.read_csv(PAYMENT_FILE)

    print(
        f"Bank transactions loaded: {len(bank)} rows"
    )

    print(
        f"Payment gateway records loaded: {len(payment)} rows"
    )

    # --------------------------------------------------------
    # Display columns
    # --------------------------------------------------------

    print("\nBank columns:")
    print(bank.columns.tolist())

    print("\nPayment columns:")
    print(payment.columns.tolist())

    # --------------------------------------------------------
    # Run fuzzy matching
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("RUNNING FUZZY MATCHING")
    print("=" * 70)

    results = fuzzy_match(
        bank,
        payment
    )

    # --------------------------------------------------------
    # Basic result information
    # --------------------------------------------------------

    print("\nFuzzy matching completed.")

    print(
        f"Total bank transactions: {len(bank)}"
    )

    print(
        f"Total results: {len(results)}"
    )

    # --------------------------------------------------------
    # Match status summary
    # --------------------------------------------------------

    print("\nMatch Status Summary:")

    print(
        results["match_status"].value_counts()
    )

    # --------------------------------------------------------
    # Confidence summary
    # --------------------------------------------------------

    print("\nConfidence Summary:")

    print(
        results["match_confidence"].value_counts()
    )

    # --------------------------------------------------------
    # Score summary
    # --------------------------------------------------------

    print("\nScore Statistics:")

    print(
        results["match_score"].describe()
    )

    # --------------------------------------------------------
    # Display first 20 results
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("FUZZY MATCH RESULTS")
    print("=" * 70)

    display_columns = [
        "transaction_id",
        "payment_id",
        "invoice_id",
        "bank_amount",
        "payment_amount",
        "bank_date",
        "payment_date",
        "match_score",
        "match_confidence",
        "match_status",
    ]

    print(
        results[display_columns]
        .head(20)
        .to_string(index=False)
    )

    # --------------------------------------------------------
    # Save results
    # --------------------------------------------------------

    output_path = save_results(
        results,
        OUTPUT_FILE
    )

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(
        f"Total bank records : {len(bank)}"
    )

    print(
        f"Total results      : {len(results)}"
    )

    print("\nMatch status:")

    print(
        results["match_status"].value_counts()
    )

    print("\nConfidence levels:")

    print(
        results["match_confidence"].value_counts()
    )

    print("\nScore statistics:")

    print(
        results["match_score"].describe()
    )

    print(
        f"\nResults saved to: {output_path}"
    )

    print(
        "\nFuzzy reconciliation test completed successfully."
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()