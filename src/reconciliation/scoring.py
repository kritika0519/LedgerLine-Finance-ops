import pandas as pd
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"

EXACT_FILE = PROCESSED_DIR / "exact_match_results.csv"
FUZZY_FILE = PROCESSED_DIR / "fuzzy_match_results.csv"
RECON_FILE = PROCESSED_DIR / "reconciliation_results.csv"

OUTPUT_FILE = PROCESSED_DIR / "scored_reconciliation_results.csv"


# ============================================================
# CONFIGURATION
# ============================================================

# Weights used for the final reconciliation score
AMOUNT_WEIGHT = 0.40
DATE_WEIGHT = 0.30
LEDGER_WEIGHT = 0.20
FUZZY_WEIGHT = 0.10


# Decision thresholds
AUTO_MATCH_THRESHOLD = 0.90
REVIEW_THRESHOLD = 0.70


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_bool(value):
    """
    Convert different representations of True/False
    into a proper boolean.
    """
    if pd.isna(value):
        return False

    if isinstance(value, bool):
        return value

    value = str(value).strip().lower()

    return value in {
        "true",
        "1",
        "yes",
        "y",
        "matched"
    }


def classify_confidence(score):
    """
    Convert numerical score into confidence level.
    """

    if score >= 0.90:
        return "HIGH_CONFIDENCE"

    elif score >= 0.70:
        return "MEDIUM_CONFIDENCE"

    else:
        return "LOW_CONFIDENCE"


def classify_decision(row):
    """
    Final business decision.

    Important:
    DATE_MISMATCH should NOT become AUTO_MATCH
    even if the fuzzy score is high.
    """

    if row["final_status"] == "MATCHED":

        if row["final_score"] >= AUTO_MATCH_THRESHOLD:
            return "AUTO_MATCH"

        elif row["final_score"] >= REVIEW_THRESHOLD:
            return "REVIEW"

        else:
            return "EXCEPTION"

    elif row["final_status"] == "DATE_MISMATCH":

        return "REVIEW"

    else:

        return "EXCEPTION"


# ============================================================
# MAIN
# ============================================================

print("=" * 70)
print("RECONCILIATION SCORING")
print("=" * 70)

print("\nLoading reconciliation data...")


# ------------------------------------------------------------
# Load files
# ------------------------------------------------------------

if not EXACT_FILE.exists():
    raise FileNotFoundError(
        f"Exact match file not found:\n{EXACT_FILE}"
    )

if not FUZZY_FILE.exists():
    raise FileNotFoundError(
        f"Fuzzy match file not found:\n{FUZZY_FILE}"
    )

if not RECON_FILE.exists():
    raise FileNotFoundError(
        f"Reconciliation file not found:\n{RECON_FILE}"
    )


exact = pd.read_csv(EXACT_FILE)
fuzzy = pd.read_csv(FUZZY_FILE)
recon = pd.read_csv(RECON_FILE)


print(f"Exact results loaded : {len(exact)} rows")
print(f"Fuzzy results loaded : {len(fuzzy)} rows")
print(f"Reconciliation rows  : {len(recon)} rows")


# ============================================================
# VALIDATE REQUIRED COLUMNS
# ============================================================

required_recon_columns = [
    "transaction_id",
    "payment_id",
    "final_status",
    "amount_match",
    "date_match",
    "ledger_found"
]

for column in required_recon_columns:

    if column not in recon.columns:
        raise ValueError(
            f"Required column '{column}' missing "
            f"from reconciliation_results.csv"
        )


required_fuzzy_columns = [
    "transaction_id",
    "payment_id",
    "match_score"
]

for column in required_fuzzy_columns:

    if column not in fuzzy.columns:
        raise ValueError(
            f"Required column '{column}' missing "
            f"from fuzzy_match_results.csv"
        )


# ============================================================
# PREPARE FUZZY DATA
# ============================================================

print("\nPreparing fuzzy scores...")

fuzzy_small = fuzzy[
    [
        "transaction_id",
        "payment_id",
        "match_score",
        "match_confidence",
        "match_status"
    ]
].copy()


# Prevent duplicate transaction IDs from creating
# duplicate rows during merge.

fuzzy_small = fuzzy_small.drop_duplicates(
    subset=["transaction_id"],
    keep="first"
)


# ============================================================
# PREPARE RECONCILIATION DATA
# ============================================================

print("Preparing reconciliation results...")

result = recon.copy()


# Convert validation columns to boolean

result["amount_match"] = result["amount_match"].apply(
    safe_bool
)

result["date_match"] = result["date_match"].apply(
    safe_bool
)

result["ledger_found"] = result["ledger_found"].apply(
    safe_bool
)


# ============================================================
# MERGE FUZZY SCORE
# ============================================================

print("Combining reconciliation and fuzzy results...")

result = result.merge(
    fuzzy_small,
    on=["transaction_id", "payment_id"],
    how="left",
    suffixes=("", "_fuzzy")
)


# Missing fuzzy score should be zero

result["match_score"] = pd.to_numeric(
    result["match_score"],
    errors="coerce"
).fillna(0.0)


# ============================================================
# CALCULATE COMPONENT SCORES
# ============================================================

print("Calculating component scores...")


# Amount score

result["amount_score"] = result["amount_match"].astype(float)


# Date score

result["date_score"] = result["date_match"].astype(float)


# Ledger score

result["ledger_score"] = result["ledger_found"].astype(float)


# Fuzzy score

result["fuzzy_score"] = result["match_score"].clip(
    lower=0,
    upper=1
)


# ============================================================
# FINAL SCORE
# ============================================================

result["final_score"] = (
    result["amount_score"] * AMOUNT_WEIGHT
    +
    result["date_score"] * DATE_WEIGHT
    +
    result["ledger_score"] * LEDGER_WEIGHT
    +
    result["fuzzy_score"] * FUZZY_WEIGHT
)


# ============================================================
# IMPORTANT BUSINESS RULE
# ============================================================

# If the reconciliation engine says DATE_MISMATCH,
# do not allow the record to be treated as a fully
# reconciled transaction.

date_mismatch_mask = (
    result["final_status"] == "DATE_MISMATCH"
)

# Cap score for date mismatches so they cannot become
# HIGH_CONFIDENCE AUTO_MATCH records.

result.loc[
    date_mismatch_mask,
    "final_score"
] = result.loc[
    date_mismatch_mask,
    "final_score"
].clip(upper=0.69)


# Round score

result["final_score"] = result["final_score"].round(4)


# ============================================================
# FINAL MATCH TYPE
# ============================================================

def determine_match_type(row):

    if row["final_status"] == "MATCHED":

        # If reconciliation validation passed,
        # use the exact matching information.

        if (
            row["amount_match"]
            and row["date_match"]
            and row["ledger_found"]
        ):
            return "EXACT_MATCH"

        return "FUZZY_MATCH"

    elif row["final_status"] == "DATE_MISMATCH":

        return "FUZZY_MATCH"

    else:

        return "NO_MATCH"


result["final_match_type"] = result.apply(
    determine_match_type,
    axis=1
)


# ============================================================
# CONFIDENCE
# ============================================================

result["final_confidence"] = result[
    "final_score"
].apply(
    classify_confidence
)


# ============================================================
# FINAL DECISION
# ============================================================

result["final_decision"] = result.apply(
    classify_decision,
    axis=1
)


# ============================================================
# REASON
# ============================================================

def generate_reason(row):

    if row["final_status"] == "MATCHED":

        return (
            "Amount, date and ledger validation passed"
        )

    elif row["final_status"] == "DATE_MISMATCH":

        return (
            "Amount matched but bank transaction date "
            "differs from payment date; manual review required"
        )

    else:

        return "Reconciliation exception requires review"


result["scoring_reason"] = result.apply(
    generate_reason,
    axis=1
)


# ============================================================
# SELECT OUTPUT COLUMNS
# ============================================================

output_columns = [
    "transaction_id",
    "payment_id",

    "final_status",
    "final_match_type",

    "amount_match",
    "date_match",
    "ledger_found",

    "amount_score",
    "date_score",
    "ledger_score",
    "fuzzy_score",

    "final_score",
    "final_confidence",
    "final_decision",

    "reason",
    "scoring_reason"
]


# Only keep columns that actually exist

output_columns = [
    column
    for column in output_columns
    if column in result.columns
]


result = result[output_columns]


# ============================================================
# SAVE RESULTS
# ============================================================

result.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("SCORING SUMMARY")
print("=" * 70)

print(
    f"\nTotal reconciliation records: {len(result)}"
)


print("\nOriginal reconciliation status:")
print(
    result["final_status"].value_counts()
)


print("\nFinal match type:")
print(
    result["final_match_type"].value_counts()
)


print("\nFinal confidence:")
print(
    result["final_confidence"].value_counts()
)


print("\nFinal decision:")
print(
    result["final_decision"].value_counts()
)


print("\nScore statistics:")

print(
    result["final_score"].describe()
)


# ============================================================
# IMPORTANT VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("VALIDATION")
print("=" * 70)


date_mismatches = (
    result["final_status"] == "DATE_MISMATCH"
).sum()

matched = (
    result["final_status"] == "MATCHED"
).sum()

auto_matches = (
    result["final_decision"] == "AUTO_MATCH"
).sum()

reviews = (
    result["final_decision"] == "REVIEW"
).sum()

exceptions = (
    result["final_decision"] == "EXCEPTION"
).sum()


print(f"\nMatched records       : {matched}")
print(f"Date mismatch records : {date_mismatches}")
print(f"Auto match            : {auto_matches}")
print(f"Manual review         : {reviews}")
print(f"Exceptions            : {exceptions}")


# ============================================================
# SAMPLE
# ============================================================

print("\n" + "=" * 70)
print("SAMPLE RESULTS")
print("=" * 70)

print(
    result.head(20).to_string(index=False)
)


# ============================================================
# OUTPUT
# ============================================================

print("\n" + "=" * 70)
print("RESULTS SAVED")
print("=" * 70)

print(f"\nOutput file:")
print(OUTPUT_FILE)

print("\n" + "=" * 70)
print("SCORING COMPLETED SUCCESSFULLY")
print("=" * 70)