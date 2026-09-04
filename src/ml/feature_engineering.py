from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    HIGH_ATTENTION_DATE_THRESHOLD_DAYS,
    PROCESSED_DIR,
)


CLASSIFIED_FILE = PROCESSED_DIR / "classified_reconciliation_results.csv"
EXACT_FILE = PROCESSED_DIR / "exact_match_results.csv"

HIGH_ATTENTION_STATUSES = {
    "AMOUNT_MISMATCH",
    "DUPLICATE_PAYMENT",
    "LEDGER_EXCEPTION",
    "PAYMENT_FAILED",
    "PAYMENT_REFUNDED",
}

LEAKAGE_COLUMNS = {
    "transaction_id",
    "payment_id",
    "invoice_id",
    "expected_final_decision",
    "expected_exception_type",
    "high_attention",
    "final_status",
    "exception_type",
    "risk_level",
    "recommended_action",
    "is_exception",
    "reason",
}

NUMERIC_FEATURES = [
    "bank_amount",
    "payment_amount",
    "amount_difference",
    "absolute_amount_difference",
    "amount_difference_pct",
    "date_difference",
    "transaction_payment_id_delta",
    "has_payment_id",
]

BOOLEAN_FEATURES = [
    "amount_match",
    "date_match",
    "ledger_found",
    "same_transaction_payment_numeric_id",
]

CATEGORICAL_FEATURES = [
    "ledger_status",
    "payment_status",
    "date_severity",
    "match_status",
    "has_normalized_reference",
]


def load_classified_data(
    classified_file=CLASSIFIED_FILE,
    exact_file=EXACT_FILE,
):
    classified = pd.read_csv(classified_file)

    exact_path = Path(exact_file)
    if not exact_path.exists():
        return classified

    exact = pd.read_csv(exact_path)
    enrich_columns = [
        "transaction_id",
        "bank_amount",
        "payment_amount",
        "normalized_reference",
        "match_status",
    ]
    enrich_columns = [
        column for column in enrich_columns if column in exact.columns
    ]

    return classified.merge(
        exact[enrich_columns].drop_duplicates("transaction_id"),
        on="transaction_id",
        how="left",
        suffixes=("", "_exact"),
    )


def _to_bool(value):
    if isinstance(value, bool):
        return value

    if pd.isna(value):
        return False

    return str(value).strip().lower() in {
        "true",
        "1",
        "yes",
        "y",
    }


def _numeric_id(value):
    if pd.isna(value):
        return None

    digits = "".join(ch for ch in str(value) if ch.isdigit())

    if not digits:
        return None

    return int(digits)


def create_high_attention_target(df):
    final_status = df["final_status"].astype(str).str.upper()
    date_difference = pd.to_numeric(
        df.get("date_difference"),
        errors="coerce",
    ).fillna(0)

    high_attention = final_status.isin(HIGH_ATTENTION_STATUSES) | (
        (final_status == "DATE_MISMATCH")
        & (date_difference > HIGH_ATTENTION_DATE_THRESHOLD_DAYS)
    )

    return high_attention.astype(int)


def build_feature_frame(df):
    result = df.copy()

    for column in [
        "bank_amount",
        "payment_amount",
        "amount_difference",
        "absolute_amount_difference",
        "date_difference",
    ]:
        if column in result.columns:
            result[column] = pd.to_numeric(
                result[column],
                errors="coerce",
            )

    if "bank_amount" not in result.columns:
        result["bank_amount"] = pd.NA

    if "payment_amount" not in result.columns:
        result["payment_amount"] = pd.NA

    if "amount_difference" not in result.columns:
        result["amount_difference"] = (
            result["bank_amount"] - result["payment_amount"]
        )

    if "absolute_amount_difference" not in result.columns:
        result["absolute_amount_difference"] = (
            result["amount_difference"].abs()
        )

    result["amount_difference_pct"] = (
        result["absolute_amount_difference"]
        / result["bank_amount"].abs().replace(0, pd.NA)
    ).fillna(0)

    result["date_difference"] = pd.to_numeric(
        result.get("date_difference"),
        errors="coerce",
    ).fillna(0)

    for column in BOOLEAN_FEATURES:
        if column not in result.columns:
            result[column] = False

    for column in ["amount_match", "date_match", "ledger_found"]:
        result[column] = result[column].apply(_to_bool)

    transaction_numbers = result["transaction_id"].apply(_numeric_id)
    payment_numbers = result["payment_id"].apply(_numeric_id)

    result["has_payment_id"] = payment_numbers.notna().astype(int)

    result["same_transaction_payment_numeric_id"] = (
        transaction_numbers.notna()
        & payment_numbers.notna()
        & (transaction_numbers == payment_numbers)
    )

    result["transaction_payment_id_delta"] = (
        transaction_numbers - payment_numbers
    ).abs()

    result["has_normalized_reference"] = (
        result.get("normalized_reference", pd.Series(index=result.index))
        .notna()
        .map({True: "YES", False: "NO"})
    )

    for column in CATEGORICAL_FEATURES:
        if column not in result.columns:
            result[column] = "UNKNOWN"

        result[column] = (
            result[column]
            .fillna("UNKNOWN")
            .astype(str)
            .str.strip()
            .str.upper()
        )

    for column in NUMERIC_FEATURES:
        if column not in result.columns:
            result[column] = 0

        result[column] = pd.to_numeric(
            result[column],
            errors="coerce",
        ).fillna(0)

    result["high_attention"] = create_high_attention_target(result)

    feature_columns = (
        NUMERIC_FEATURES
        + BOOLEAN_FEATURES
        + CATEGORICAL_FEATURES
    )

    return result, feature_columns


def get_feature_documentation():
    return {
        "target": (
            "high_attention=1 for investigation-heavy exceptions "
            "or date mismatches above the configured severity threshold."
        ),
        "excluded_for_leakage": sorted(LEAKAGE_COLUMNS),
        "numeric_features": NUMERIC_FEATURES,
        "boolean_features": BOOLEAN_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "date_threshold_days": HIGH_ATTENTION_DATE_THRESHOLD_DAYS,
    }


def main():
    df = load_classified_data()
    features, feature_columns = build_feature_frame(df)

    print("=" * 70)
    print("ML FEATURE ENGINEERING")
    print("=" * 70)
    print(f"Rows: {len(features)}")
    print(f"Feature columns: {len(feature_columns)}")
    print("\nTarget distribution:")
    print(features["high_attention"].value_counts().to_string())
    print("\nSelected features:")
    for column in feature_columns:
        print(f"- {column}")


if __name__ == "__main__":
    main()
