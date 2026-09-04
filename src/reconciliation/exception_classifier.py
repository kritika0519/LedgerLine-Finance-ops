from pathlib import Path
import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

INPUT_FILE = (
    PROCESSED_DIR
    / "reconciliation_results.csv"
)

OUTPUT_FILE = (
    PROCESSED_DIR
    / "classified_reconciliation_results.csv"
)


# ============================================================
# LOAD DATA
# ============================================================

def load_reconciliation_data():

    print("=" * 70)
    print("EXCEPTION CLASSIFICATION")
    print("=" * 70)

    print("\nLoading reconciliation results...")

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"Input file not found:\n{INPUT_FILE}"
        )

    df = pd.read_csv(
        INPUT_FILE
    )

    print(
        f"Records loaded: {len(df)}"
    )

    return df


# ============================================================
# PREPARE DATA
# ============================================================

def prepare_data(df):

    df = df.copy()

    # --------------------------------------------------------
    # Convert date difference
    # --------------------------------------------------------

    if "date_difference" in df.columns:

        df["date_diff"] = pd.to_numeric(
            df["date_difference"],
            errors="coerce"
        )

    else:

        df["date_diff"] = None

    # --------------------------------------------------------
    # Convert boolean-like columns
    # --------------------------------------------------------

    for column in [
        "amount_match",
        "date_match",
        "ledger_found"
    ]:

        if column in df.columns:

            df[column] = (
                df[column]
                .astype(str)
                .str.lower()
                .map({
                    "true": True,
                    "false": False
                })
            )

    return df


# ============================================================
# EXCEPTION TYPE
# ============================================================

def classify_exception_type(row):

    status = str(
        row.get(
            "final_status",
            ""
        )
    ).upper()

    # --------------------------------------------------------
    # Duplicate payment
    # --------------------------------------------------------

    if status == "DUPLICATE_PAYMENT":

        return "DUPLICATE_PAYMENT"

    # --------------------------------------------------------
    # Amount mismatch
    # --------------------------------------------------------

    if status == "AMOUNT_MISMATCH":

        return "AMOUNT_MISMATCH"

    # --------------------------------------------------------
    # Ledger exception
    # --------------------------------------------------------

    if status == "LEDGER_EXCEPTION":

        return "LEDGER_EXCEPTION"

    # --------------------------------------------------------
    # Payment status exceptions
    # --------------------------------------------------------

    if status == "PAYMENT_FAILED":

        return "PAYMENT_FAILED"

    if status == "PAYMENT_REFUNDED":

        return "PAYMENT_REFUNDED"

    # --------------------------------------------------------
    # Missing payment
    # --------------------------------------------------------

    if status in [
        "MISSING_PAYMENT",
        "UNMATCHED"
    ]:

        return "MISSING_PAYMENT"

    # --------------------------------------------------------
    # Missing bank record
    # --------------------------------------------------------

    if status == "MISSING_BANK":

        return "MISSING_BANK"

    # --------------------------------------------------------
    # Missing ledger
    # --------------------------------------------------------

    if status == "MISSING_LEDGER":

        return "MISSING_LEDGER"

    # --------------------------------------------------------
    # Ledger mismatch
    # --------------------------------------------------------

    if status == "LEDGER_MISMATCH":

        return "LEDGER_MISMATCH"

    # --------------------------------------------------------
    # Date mismatch
    # --------------------------------------------------------

    if status == "DATE_MISMATCH":

        date_diff = row.get(
            "date_diff"
        )

        if pd.isna(date_diff):

            return "DATE_MISMATCH"

        if date_diff <= 2:

            return "SETTLEMENT_DELAY"

        return "DATE_MISMATCH"

    # --------------------------------------------------------
    # Clean match
    # --------------------------------------------------------

    if status == "MATCHED":

        return "NO_EXCEPTION"

    # --------------------------------------------------------
    # Fallback
    # --------------------------------------------------------

    return "UNKNOWN_EXCEPTION"


# ============================================================
# DATE SEVERITY
# ============================================================

def classify_date_severity(row):

    exception_type = row[
        "exception_type"
    ]

    date_diff = row.get(
        "date_diff"
    )

    # --------------------------------------------------------
    # No date exception
    # --------------------------------------------------------

    if exception_type == "NO_EXCEPTION":

        return "NO_DATE_EXCEPTION"

    # --------------------------------------------------------
    # Duplicate payment
    # --------------------------------------------------------

    if exception_type == "DUPLICATE_PAYMENT":

        return "NOT_APPLICABLE"

    # --------------------------------------------------------
    # Missing / non-date exceptions
    # --------------------------------------------------------

    if exception_type in [
        "AMOUNT_MISMATCH",
        "PAYMENT_FAILED",
        "PAYMENT_REFUNDED",
        "MISSING_PAYMENT",
        "MISSING_BANK",
        "MISSING_LEDGER",
        "LEDGER_EXCEPTION",
        "LEDGER_MISMATCH",
        "UNKNOWN_EXCEPTION"
    ]:

        return "NOT_APPLICABLE"

    # --------------------------------------------------------
    # Date-based exceptions
    # --------------------------------------------------------

    if pd.isna(date_diff):

        return "UNKNOWN"

    if date_diff == 0:

        return "NONE"

    if date_diff <= 2:

        return "LOW"

    if date_diff <= 7:

        return "MEDIUM"

    if date_diff <= 30:

        return "HIGH"

    return "CRITICAL"


# ============================================================
# RISK LEVEL
# ============================================================

def classify_risk_level(row):

    exception_type = row[
        "exception_type"
    ]

    date_severity = row[
        "date_severity"
    ]

    # --------------------------------------------------------
    # Clean records
    # --------------------------------------------------------

    if exception_type == "NO_EXCEPTION":

        return "LOW"

    # --------------------------------------------------------
    # Duplicate payment
    # --------------------------------------------------------

    if exception_type == "DUPLICATE_PAYMENT":

        return "HIGH"

    # --------------------------------------------------------
    # Amount mismatch
    # --------------------------------------------------------

    if exception_type == "AMOUNT_MISMATCH":

        return "HIGH"

    # --------------------------------------------------------
    # Payment status exceptions
    # --------------------------------------------------------

    if exception_type in [
        "PAYMENT_FAILED",
        "PAYMENT_REFUNDED"
    ]:

        return "HIGH"

    # --------------------------------------------------------
    # Missing records
    # --------------------------------------------------------

    if exception_type in [
        "MISSING_PAYMENT",
        "MISSING_BANK",
        "MISSING_LEDGER"
    ]:

        return "HIGH"

    # --------------------------------------------------------
    # Ledger mismatch
    # --------------------------------------------------------

    if exception_type in [
        "LEDGER_EXCEPTION",
        "LEDGER_MISMATCH"
    ]:

        return "HIGH"

    # --------------------------------------------------------
    # Date-based risk
    # --------------------------------------------------------

    if date_severity == "LOW":

        return "LOW"

    if date_severity == "MEDIUM":

        return "MEDIUM"

    if date_severity == "HIGH":

        return "HIGH"

    if date_severity == "CRITICAL":

        return "CRITICAL"

    return "MEDIUM"


# ============================================================
# RECOMMENDED ACTION
# ============================================================

def determine_action(row):

    exception_type = row[
        "exception_type"
    ]

    date_severity = row[
        "date_severity"
    ]

    risk_level = row[
        "risk_level"
    ]

    # --------------------------------------------------------
    # Clean
    # --------------------------------------------------------

    if exception_type == "NO_EXCEPTION":

        return "AUTO_RECONCILE"

    # --------------------------------------------------------
    # Duplicate payment
    # --------------------------------------------------------

    if exception_type == "DUPLICATE_PAYMENT":

        return "MANUAL_REVIEW_DUPLICATE"

    # --------------------------------------------------------
    # Amount mismatch
    # --------------------------------------------------------

    if exception_type == "AMOUNT_MISMATCH":

        return "INVESTIGATE_AMOUNT_DIFFERENCE"

    # --------------------------------------------------------
    # Payment failed
    # --------------------------------------------------------

    if exception_type == "PAYMENT_FAILED":

        return "INVESTIGATE_FAILED_PAYMENT"

    # --------------------------------------------------------
    # Payment refunded
    # --------------------------------------------------------

    if exception_type == "PAYMENT_REFUNDED":

        return "REVIEW_REFUND"

    # --------------------------------------------------------
    # Missing payment
    # --------------------------------------------------------

    if exception_type == "MISSING_PAYMENT":

        return "INVESTIGATE_MISSING_PAYMENT"

    # --------------------------------------------------------
    # Missing bank
    # --------------------------------------------------------

    if exception_type == "MISSING_BANK":

        return "INVESTIGATE_BANK_RECORD"

    # --------------------------------------------------------
    # Missing ledger
    # --------------------------------------------------------

    if exception_type == "MISSING_LEDGER":

        return "VERIFY_LEDGER_ENTRY"

    # --------------------------------------------------------
    # Ledger mismatch
    # --------------------------------------------------------

    if exception_type in [
        "LEDGER_EXCEPTION",
        "LEDGER_MISMATCH"
    ]:

        return "INVESTIGATE_LEDGER"

    # --------------------------------------------------------
    # Settlement delay
    # --------------------------------------------------------

    if exception_type == "SETTLEMENT_DELAY":

        return "VERIFY_SETTLEMENT_TIMING"

    # --------------------------------------------------------
    # Date exception
    # --------------------------------------------------------

    if exception_type == "DATE_MISMATCH":

        if date_severity == "MEDIUM":

            return "MANUAL_REVIEW"

        if date_severity == "HIGH":

            return "HIGH_PRIORITY_INVESTIGATION"

        if date_severity == "CRITICAL":

            return "ESCALATE"

        return "MANUAL_REVIEW"

    # --------------------------------------------------------
    # Unknown
    # --------------------------------------------------------

    return "MANUAL_REVIEW"


# ============================================================
# EXCEPTION FLAG
# ============================================================

def create_exception_flag(row):

    return (
        row["exception_type"]
        != "NO_EXCEPTION"
    )


# ============================================================
# PROCESS CLASSIFICATION
# ============================================================

def classify_exceptions(df):

    df = df.copy()

    print("\nCalculating date differences...")

    # --------------------------------------------------------
    # Exception type
    # --------------------------------------------------------

    print(
        "Classifying exception types..."
    )

    df["exception_type"] = df.apply(
        classify_exception_type,
        axis=1
    )

    # --------------------------------------------------------
    # Date severity
    # --------------------------------------------------------

    print(
        "Calculating date severity..."
    )

    df["date_severity"] = df.apply(
        classify_date_severity,
        axis=1
    )

    # --------------------------------------------------------
    # Risk
    # --------------------------------------------------------

    print(
        "Calculating risk levels..."
    )

    df["risk_level"] = df.apply(
        classify_risk_level,
        axis=1
    )

    # --------------------------------------------------------
    # Action
    # --------------------------------------------------------

    print(
        "Determining recommended actions..."
    )

    df["recommended_action"] = df.apply(
        determine_action,
        axis=1
    )

    # --------------------------------------------------------
    # Exception flag
    # --------------------------------------------------------

    df["is_exception"] = df.apply(
        create_exception_flag,
        axis=1
    )

    return df


# ============================================================
# PRINT SUMMARY
# ============================================================

def print_summary(df):

    print("\n" + "=" * 70)
    print("EXCEPTION SUMMARY")
    print("=" * 70)

    # --------------------------------------------------------
    # Exception types
    # --------------------------------------------------------

    print("\nException types:")

    print(
        df[
            "exception_type"
        ]
        .value_counts()
        .to_string()
    )

    # --------------------------------------------------------
    # Date severity
    # --------------------------------------------------------

    print("\nDate severity:")

    print(
        df[
            "date_severity"
        ]
        .value_counts()
        .to_string()
    )

    # --------------------------------------------------------
    # Risk
    # --------------------------------------------------------

    print("\nRisk levels:")

    print(
        df[
            "risk_level"
        ]
        .value_counts()
        .to_string()
    )

    # --------------------------------------------------------
    # Actions
    # --------------------------------------------------------

    print("\nRecommended actions:")

    print(
        df[
            "recommended_action"
        ]
        .value_counts()
        .to_string()
    )

    # --------------------------------------------------------
    # Flag
    # --------------------------------------------------------

    print("\nException flag:")

    print(
        df[
            "is_exception"
        ]
        .value_counts()
        .to_string()
    )


# ============================================================
# KEY METRICS
# ============================================================

def print_metrics(df):

    total = len(df)

    clean = (
        df["is_exception"] == False
    ).sum()

    exceptions = (
        df["is_exception"] == True
    ).sum()

    if total > 0:

        exception_rate = (
            exceptions / total
        ) * 100

    else:

        exception_rate = 0

    print("\n" + "=" * 70)
    print("KEY METRICS")
    print("=" * 70)

    print(
        f"\nTotal records      : {total}"
    )

    print(
        f"Clean records      : {clean}"
    )

    print(
        f"Exception records  : {exceptions}"
    )

    print(
        f"Exception rate     : "
        f"{exception_rate:.2f}%"
    )


# ============================================================
# DATE RANGE SUMMARY
# ============================================================

def print_date_distribution(df):

    print("\n" + "=" * 70)
    print("DATE DIFFERENCE DISTRIBUTION")
    print("=" * 70)

    print(
        df[
            "date_diff"
        ]
        .value_counts(
            dropna=False
        )
        .sort_index()
        .to_string()
    )

    # --------------------------------------------------------
    # Ranges
    # --------------------------------------------------------

    zero = (
        df["date_diff"] == 0
    ).sum()

    one_two = (
        df["date_diff"].between(
            1,
            2,
            inclusive="both"
        )
    ).sum()

    three_seven = (
        df["date_diff"].between(
            3,
            7,
            inclusive="both"
        )
    ).sum()

    eight_thirty = (
        df["date_diff"].between(
            8,
            30,
            inclusive="both"
        )
    ).sum()

    thirty_one_ninety = (
        df["date_diff"].between(
            31,
            90,
            inclusive="both"
        )
    ).sum()

    ninety_one_plus = (
        df["date_diff"] >= 91
    ).sum()

    print("\n" + "=" * 70)
    print("DATE RANGE SUMMARY")
    print("=" * 70)

    print(
        f"\n0 days      : {zero}"
    )

    print(
        f"1-2 days    : {one_two}"
    )

    print(
        f"3-7 days    : {three_seven}"
    )

    print(
        f"8-30 days   : {eight_thirty}"
    )

    print(
        f"31-90 days  : {thirty_one_ninety}"
    )

    print(
        f"91+ days    : {ninety_one_plus}"
    )


# ============================================================
# PRINT SAMPLE
# ============================================================

def print_sample(df):

    print("\n" + "=" * 70)
    print("EXCEPTION SAMPLE")
    print("=" * 70)

    columns = [
        "transaction_id",
        "payment_id",
        "final_status",
        "date_diff",
        "exception_type",
        "date_severity",
        "risk_level",
        "recommended_action",
        "is_exception"
    ]

    available_columns = [
        column
        for column in columns
        if column in df.columns
    ]

    print(
        df[
            available_columns
        ]
        .head(20)
        .to_string(index=False)
    )


# ============================================================
# SAVE
# ============================================================

def save_results(df):

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("\n" + "=" * 70)
    print("RESULTS SAVED")
    print("=" * 70)

    print(
        f"\nOutput file:\n"
        f"{OUTPUT_FILE}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    df = load_reconciliation_data()

    df = prepare_data(
        df
    )

    df = classify_exceptions(
        df
    )

    print_summary(
        df
    )

    print_metrics(
        df
    )

    print_date_distribution(
        df
    )

    print_sample(
        df
    )

    save_results(
        df
    )

    print("\n" + "=" * 70)
    print("EXCEPTION CLASSIFICATION COMPLETED")
    print("=" * 70)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
