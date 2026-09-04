import os
import re
import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import AMOUNT_TOLERANCE


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

BANK_FILE = os.path.join(
    BASE_DIR, "data", "processed", "bank_transactions_processed.csv"
)

PAYMENT_FILE = os.path.join(
    BASE_DIR, "data", "processed", "payment_gateway_processed.csv"
)

OUTPUT_FILE = os.path.join(
    BASE_DIR, "data", "processed", "exact_match_results.csv"
)


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_reference(value):
    """
    Convert references into a common comparable form.

    Examples:
        CMS/GW-188297/STRIPE/CUST0322 -> GW-188297
        GW-188297                     -> GW-188297
        gw-188297                     -> GW-188297
    """

    if pd.isna(value):
        return None

    value = str(value).strip().upper()

    if not value:
        return None

    # Extract the gateway reference from a compound bank reference.
    # Supports:
    # GW-123456
    # GW-DUP-0001
    match = re.search(r"GW-[A-Z0-9]+(?:-[A-Z0-9]+)*", value)

    if match:
        return match.group(0)

    return None


def normalize_amount(value):
    """
    Normalize monetary values for exact comparison.
    """
    if pd.isna(value):
        return None

    try:
        return round(float(value), 2)
    except (ValueError, TypeError):
        return None


def extract_numeric_id(value):
    """
    Extract the numeric identity from IDs such as TXN0074 or PAY0074.
    Returns None when the value does not contain a numeric identity.
    """

    if pd.isna(value):
        return None

    match = re.search(r"\d+", str(value).strip())

    if not match:
        return None

    return int(match.group(0))


def amounts_match(left, right):
    """
    Compare currency amounts with the configured tolerance.
    """

    if left is None or right is None:
        return False

    try:
        return abs(float(left) - float(right)) <= AMOUNT_TOLERANCE
    except (TypeError, ValueError):
        return False


# ============================================================
# COLUMN DETECTION
# ============================================================

def find_column(df, possible_names, label):
    """
    Find a column using a list of possible names.
    """

    for name in possible_names:
        if name in df.columns:
            return name

    raise ValueError(
        f"{label} column not found.\n"
        f"Available columns: {list(df.columns)}"
    )


# ============================================================
# INPUT VALIDATION
# ============================================================

def validate_input_data(bank, payment,
                        bank_id_col,
                        bank_ref_col,
                        bank_amount_col,
                        payment_id_col,
                        payment_ref_col,
                        payment_amount_col):

    print("Validating input data...")

    required_bank = [
        bank_id_col,
        bank_ref_col,
        bank_amount_col
    ]

    required_payment = [
        payment_id_col,
        payment_ref_col,
        payment_amount_col
    ]

    for col in required_bank:
        if col not in bank.columns:
            raise ValueError(f"Missing bank column: {col}")

    for col in required_payment:
        if col not in payment.columns:
            raise ValueError(f"Missing payment column: {col}")

    if bank[bank_id_col].duplicated().any():
        raise ValueError("Duplicate transaction_id found in bank data.")

    if payment[payment_id_col].duplicated().any():
        raise ValueError("Duplicate payment_id found in payment data.")

    print("Input validation passed.")
    print()


# ============================================================
# MAIN EXACT MATCHING
# ============================================================

def run_exact_matching():

    print("=" * 70)
    print("EXACT RECONCILIATION")
    print("=" * 70)
    print()

    # --------------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------------

    print("Loading processed data...")

    print(f"Bank file     : {BANK_FILE}")
    print(f"Payment file  : {PAYMENT_FILE}")
    print()

    if not os.path.exists(BANK_FILE):
        raise FileNotFoundError(
            f"Bank processed file not found:\n{BANK_FILE}"
        )

    if not os.path.exists(PAYMENT_FILE):
        raise FileNotFoundError(
            f"Payment processed file not found:\n{PAYMENT_FILE}"
        )

    bank = pd.read_csv(BANK_FILE)
    payment = pd.read_csv(PAYMENT_FILE)

    print(f"Bank transactions loaded : {len(bank)}")
    print(f"Payment records loaded    : {len(payment)}")
    print()

    # --------------------------------------------------------
    # DETECT COLUMNS
    # --------------------------------------------------------

    bank_id_col = find_column(
        bank,
        ["transaction_id", "bank_transaction_id"],
        "Bank ID"
    )

    bank_ref_col = find_column(
        bank,
        ["reference", "bank_reference", "transaction_reference"],
        "Bank reference"
    )

    bank_amount_col = find_column(
        bank,
        ["amount", "transaction_amount"],
        "Bank amount"
    )

    payment_id_col = find_column(
        payment,
        ["payment_id"],
        "Payment ID"
    )

    payment_ref_col = find_column(
        payment,
        ["gateway_reference", "reference", "payment_reference"],
        "Payment reference"
    )

    payment_amount_col = find_column(
        payment,
        ["amount", "payment_amount"],
        "Payment amount"
    )

    print("Detected columns:")
    print(f"Bank ID             : {bank_id_col}")
    print(f"Bank reference      : {bank_ref_col}")
    print(f"Bank amount         : {bank_amount_col}")
    print(f"Payment ID          : {payment_id_col}")
    print(f"Payment reference   : {payment_ref_col}")
    print(f"Payment amount      : {payment_amount_col}")
    print()

    # --------------------------------------------------------
    # VALIDATE
    # --------------------------------------------------------

    validate_input_data(
        bank,
        payment,
        bank_id_col,
        bank_ref_col,
        bank_amount_col,
        payment_id_col,
        payment_ref_col,
        payment_amount_col
    )

    # --------------------------------------------------------
    # NORMALIZE REFERENCES AND AMOUNTS
    # --------------------------------------------------------

    bank = bank.copy()
    payment = payment.copy()

    bank["normalized_reference"] = (
        bank[bank_ref_col].apply(normalize_reference)
    )

    payment["normalized_reference"] = (
        payment[payment_ref_col].apply(normalize_reference)
    )

    bank["normalized_amount"] = (
        bank[bank_amount_col].apply(normalize_amount)
    )

    payment["normalized_amount"] = (
        payment[payment_amount_col].apply(normalize_amount)
    )

    # --------------------------------------------------------
    # REFERENCE STATISTICS
    # --------------------------------------------------------

    total_bank = len(bank)

    unique_bank_refs = bank["normalized_reference"].nunique(
        dropna=True
    )

    missing_bank_refs = bank["normalized_reference"].isna().sum()

    duplicate_reference_mask = (
        bank["normalized_reference"].notna()
        &
        bank["normalized_reference"].duplicated(keep=False)
    )

    duplicate_reference_rows = duplicate_reference_mask.sum()

    print("Bank reference statistics:")
    print(f"Total bank rows             : {total_bank}")
    print(f"Unique normalized references: {unique_bank_refs}")
    print(f"Duplicate-reference rows    : {duplicate_reference_rows}")
    print(f"Missing bank references     : {missing_bank_refs}")
    print()

    # --------------------------------------------------------
    # DEBUG: COMMON REFERENCES
    # --------------------------------------------------------

    bank_refs = set(
        bank["normalized_reference"]
        .dropna()
    )

    payment_refs = set(
        payment["normalized_reference"]
        .dropna()
    )

    common_refs = bank_refs.intersection(payment_refs)

    print("Reference comparison:")
    print(f"Bank refs     : {len(bank_refs)}")
    print(f"Payment refs  : {len(payment_refs)}")
    print(f"Common refs   : {len(common_refs)}")
    print()

    # --------------------------------------------------------
    # PAYMENT LOOKUP
    # --------------------------------------------------------

    payment_lookup = {}

    for _, row in payment.iterrows():

        ref = row["normalized_reference"]

        if pd.isna(ref) or ref is None:
            continue

        # Payment references should normally be unique.
        # Keep the first occurrence.
        if ref not in payment_lookup:
            payment_lookup[ref] = row

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Duplicate bank references mean that two bank records
    # point to the same payment reference.
    #
    # We must use TRANSACTION ID MATCHING to determine the
    # legitimate assignment.
    #
    # The transaction whose NUMERIC ID matches the payment's
    # NUMERIC ID is the legitimate match.
    #
    # For example:
    # - TXN0074 should match PAY0074 (same number: 74)
    # - TXN0004 using same reference is DUPLICATE_PAYMENT
    #
    # This ensures one-to-one transaction-payment mapping.
    # --------------------------------------------------------

    duplicate_refs = set(
        bank.loc[
            duplicate_reference_mask,
            "normalized_reference"
        ].dropna()
    )

    # For every duplicated reference, determine which bank row
    # legitimately matches the payment by ID matching.
    legitimate_duplicate_rows = set()

    duplicate_payment_rows = set()

    for ref in duplicate_refs:

        candidates = bank[
            bank["normalized_reference"] == ref
        ]

        payment_row = payment_lookup.get(ref)

        if payment_row is None:
            continue

        # Extract numeric ID parts for matching:
        # TXN0004 -> 4, PAY0074 -> 74.
        payment_numeric = extract_numeric_id(
            payment_row[payment_id_col]
        )

        if payment_numeric is None:
            continue

        # Find which candidate transaction's ID matches the payment's numeric ID
        id_match_found = False

        for _, candidate in candidates.iterrows():

            candidate_numeric = extract_numeric_id(
                candidate[bank_id_col]
            )

            if candidate_numeric is None:
                continue

            if candidate_numeric == payment_numeric:
                # This is the legitimate match
                legitimate_id = candidate[bank_id_col]
                legitimate_duplicate_rows.add(legitimate_id)
                id_match_found = True
                break

        # If we found an ID match, mark others as duplicate
        if id_match_found:
            for _, candidate in candidates.iterrows():
                candidate_id = candidate[bank_id_col]
                if candidate_id != legitimate_id:
                    duplicate_payment_rows.add(candidate_id)
        else:
            # If no ID match found, fall back to amount matching
            # as a secondary strategy
            payment_amount = payment_row["normalized_amount"]
            amount_matches = candidates[
                candidates["normalized_amount"].apply(
                    lambda value: amounts_match(value, payment_amount)
                )
            ]

            if len(amount_matches) == 1:
                legitimate_id = amount_matches.iloc[0][bank_id_col]
                legitimate_duplicate_rows.add(legitimate_id)
                for _, candidate in candidates.iterrows():
                    candidate_id = candidate[bank_id_col]
                    if candidate_id != legitimate_id:
                        duplicate_payment_rows.add(candidate_id)

    # --------------------------------------------------------
    # EXACT MATCHING
    # --------------------------------------------------------

    print("Starting exact matching...")
    print()

    results = []

    used_payment_ids = set()

    for _, bank_row in bank.iterrows():

        transaction_id = bank_row[bank_id_col]
        bank_ref = bank_row["normalized_reference"]
        bank_amount = bank_row["normalized_amount"]

        payment_id = None
        payment_amount = None
        match_status = None
        reason = None

        # ----------------------------------------------------
        # CASE 1: Missing/invalid bank reference
        # ----------------------------------------------------

        if bank_ref is None or pd.isna(bank_ref):

            match_status = "NO_REFERENCE_MATCH"

            reason = "Bank reference could not be normalized."

        # ----------------------------------------------------
        # CASE 2: Duplicate payment
        # ----------------------------------------------------

        elif transaction_id in duplicate_payment_rows:

            payment_row = payment_lookup.get(bank_ref)

            if payment_row is not None:

                payment_id = payment_row[payment_id_col]
                payment_amount = payment_row["normalized_amount"]

            match_status = "DUPLICATE_PAYMENT"

            reason = (
                "Bank reference points to a payment already "
                "legitimately associated with another transaction."
            )

        # ----------------------------------------------------
        # CASE 3: No payment reference
        # ----------------------------------------------------

        elif bank_ref not in payment_lookup:

            match_status = "NO_REFERENCE_MATCH"

            reason = "No payment found for normalized reference."

        # ----------------------------------------------------
        # CASE 4: Payment found
        # ----------------------------------------------------

        else:

            payment_row = payment_lookup[bank_ref]

            candidate_payment_id = payment_row[payment_id_col]
            candidate_payment_amount = payment_row["normalized_amount"]

            payment_id = candidate_payment_id
            payment_amount = candidate_payment_amount

            # -----------------------------------------------
            # Amount comparison
            # -----------------------------------------------

            amount_match = amounts_match(
                bank_amount,
                payment_amount
            )

            if not amount_match:

                match_status = "AMOUNT_MISMATCH"

                reason = (
                    "Bank reference matched a payment candidate "
                    "but amounts differ."
                )

            else:

                # -------------------------------------------
                # Prevent assigning one payment to multiple
                # legitimate bank transactions.
                # -------------------------------------------

                if candidate_payment_id in used_payment_ids:

                    match_status = "DUPLICATE_PAYMENT"

                    reason = (
                        "Payment ID was already assigned to "
                        "another bank transaction."
                    )

                else:

                    match_status = "MATCHED"

                    reason = (
                        "Bank reference and amount matched "
                        "payment record."
                    )

                    used_payment_ids.add(candidate_payment_id)

        # ----------------------------------------------------
        # RESULT ROW
        # ----------------------------------------------------

        results.append({
            "transaction_id": transaction_id,
            "payment_id": payment_id,
            "bank_reference": bank_row[bank_ref_col],
            "normalized_reference": bank_ref,
            "bank_amount": bank_amount,
            "payment_amount": payment_amount,
            "match_status": match_status,
            "reason": reason
        })

    result_df = pd.DataFrame(results)

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print("=" * 70)
    print("EXACT MATCHING SUMMARY")
    print("=" * 70)
    print()

    print(f"Total bank transactions : {len(bank)}")
    print(f"Total results           : {len(result_df)}")
    print()

    print("Match status:")
    print(
        result_df["match_status"].value_counts()
    )
    print()

    # --------------------------------------------------------
    # PAYMENT ASSIGNMENT VALIDATION
    # --------------------------------------------------------

    matched_rows = result_df[
        result_df["match_status"] == "MATCHED"
    ]

    matched_payment_ids = matched_rows["payment_id"].dropna()

    duplicate_payment_count = (
        matched_payment_ids.duplicated().sum()
    )

    print("Payment assignment validation:")
    print(f"Matched rows          : {len(matched_rows)}")
    print(
        f"Unique payment IDs    : "
        f"{matched_payment_ids.nunique()}"
    )
    print(
        f"Duplicate payment rows: "
        f"{duplicate_payment_count}"
    )
    print()

    # --------------------------------------------------------
    # TRANSACTION VALIDATION
    # --------------------------------------------------------

    duplicate_transactions = (
        result_df["transaction_id"].duplicated().sum()
    )

    print(
        f"Duplicate transaction rows: "
        f"{duplicate_transactions}"
    )
    print()

    if duplicate_payment_count == 0:
        print(
            "PASS: No payment ID is assigned to more "
            "than one MATCHED bank transaction."
        )
    else:
        print(
            "WARNING: Duplicate payment assignments detected."
        )

    if duplicate_transactions == 0:
        print(
            "PASS: Every bank transaction appears only once."
        )
    else:
        print(
            "WARNING: Duplicate transaction IDs detected."
        )

    print()

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    os.makedirs(
        os.path.dirname(OUTPUT_FILE),
        exist_ok=True
    )

    result_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("Results saved to:")
    print(OUTPUT_FILE)
    print()

    print("Exact reconciliation completed.")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    run_exact_matching()
