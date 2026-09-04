from pathlib import Path
import sys
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    AMOUNT_TOLERANCE,
    EXPECTED_BENCHMARK_COUNTS,
    STATUS_TO_GROUND_TRUTH,
    VALID_LEDGER_STATUS,
)


# ============================================================
# PROJECT PATHS
# ============================================================

RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

EXACT_FILE = PROCESSED_DIR / "exact_match_results.csv"

BANK_FILE = RAW_DIR / "bank_transactions.csv"
PAYMENT_FILE = RAW_DIR / "payment_gateway.csv"
LEDGER_FILE = RAW_DIR / "ledger.csv"
INVOICE_FILE = RAW_DIR / "invoices.csv"


# ============================================================
# LOAD DATA
# ============================================================

def load_data():

    print("=" * 70)
    print("LOADING RECONCILIATION DATA")
    print("=" * 70)

    required_files = [
        EXACT_FILE,
        BANK_FILE,
        PAYMENT_FILE,
        LEDGER_FILE,
        INVOICE_FILE,
    ]

    for file_path in required_files:
        if not file_path.exists():
            raise FileNotFoundError(
                f"Required file not found:\n{file_path}"
            )

    exact = pd.read_csv(EXACT_FILE)
    bank = pd.read_csv(BANK_FILE)
    payment = pd.read_csv(PAYMENT_FILE)
    ledger = pd.read_csv(LEDGER_FILE)
    invoices = pd.read_csv(INVOICE_FILE)

    print(f"Exact matches : {len(exact)}")
    print(f"Bank records  : {len(bank)}")
    print(f"Payments      : {len(payment)}")
    print(f"Ledger        : {len(ledger)}")
    print(f"Invoices      : {len(invoices)}")

    if len(exact) != len(bank):
        raise ValueError(
            f"Exact results ({len(exact)}) must contain "
            f"one row per bank transaction ({len(bank)})."
        )

    return exact, bank, payment, ledger, invoices


# ============================================================
# DATA PREPARATION
# ============================================================

def prepare_data(bank, payment, ledger, invoices):

    bank = bank.copy()
    payment = payment.copy()
    ledger = ledger.copy()
    invoices = invoices.copy()

    # --------------------------------------------------------
    # Amounts
    # --------------------------------------------------------

    for df in [bank, payment, ledger, invoices]:

        if "amount" in df.columns:
            df["amount"] = pd.to_numeric(
                df["amount"],
                errors="coerce"
            )

        if "invoice_amount" in df.columns:
            df["invoice_amount"] = pd.to_numeric(
                df["invoice_amount"],
                errors="coerce"
            )

    # --------------------------------------------------------
    # Dates
    # --------------------------------------------------------

    bank_date_columns = [
        "transaction_date",
        "value_date"
    ]

    payment_date_columns = [
        "payment_date"
    ]

    ledger_date_columns = [
        "ledger_date"
    ]

    invoice_date_columns = [
        "invoice_date",
        "due_date"
    ]

    for column in bank_date_columns:
        if column in bank.columns:
            bank[column] = pd.to_datetime(
                bank[column],
                errors="coerce"
            )

    for column in payment_date_columns:
        if column in payment.columns:
            payment[column] = pd.to_datetime(
                payment[column],
                errors="coerce"
            )

    for column in ledger_date_columns:
        if column in ledger.columns:
            ledger[column] = pd.to_datetime(
                ledger[column],
                errors="coerce"
            )

    for column in invoice_date_columns:
        if column in invoices.columns:
            invoices[column] = pd.to_datetime(
                invoices[column],
                errors="coerce"
            )

    return bank, payment, ledger, invoices


# ============================================================
# HELPERS
# ============================================================

def clean_id(value):

    if pd.isna(value):
        return None

    value = str(value).strip()

    if value == "":
        return None

    return value


# ============================================================
# AMOUNT COMPARISON
# ============================================================

def check_amount(bank_row, payment_row):

    bank_amount = bank_row.get("amount")
    payment_amount = payment_row.get("amount")

    if pd.isna(bank_amount) or pd.isna(payment_amount):
        return False

    return abs(
        float(bank_amount) - float(payment_amount)
    ) <= AMOUNT_TOLERANCE


def calculate_amount_difference(bank_row, payment_row):

    bank_amount = bank_row.get("amount")
    payment_amount = payment_row.get("amount")

    if pd.isna(bank_amount) or pd.isna(payment_amount):
        return None

    return round(float(bank_amount) - float(payment_amount), 2)


# ============================================================
# DATE DIFFERENCE
#
# IMPORTANT:
# Ground truth uses:
#
# bank.transaction_date
#        vs
# payment.payment_date
#
# NOT value_date.
# ============================================================

def calculate_date_difference(bank_row, payment_row):

    bank_date = bank_row.get("transaction_date")
    payment_date = payment_row.get("payment_date")

    if pd.isna(bank_date) or pd.isna(payment_date):
        return None

    return abs(
        (bank_date - payment_date).days
    )


def check_date(bank_row, payment_row):

    difference = calculate_date_difference(
        bank_row,
        payment_row
    )

    if difference is None:
        return False

    return difference == 0


# ============================================================
# LEDGER LOOKUP
# ============================================================

def find_ledger_record(ledger, payment_row):

    if payment_row is None:
        return None

    invoice_id = clean_id(
        payment_row.get("invoice_id")
    )

    customer_id = clean_id(
        payment_row.get("customer_id")
    )

    candidates = ledger.copy()

    # --------------------------------------------------------
    # Match invoice
    # --------------------------------------------------------

    if (
        invoice_id is not None
        and "invoice_id" in candidates.columns
    ):

        candidates = candidates[
            candidates["invoice_id"]
            .astype(str)
            .str.strip()
            == invoice_id
        ]

    # --------------------------------------------------------
    # Match customer
    # --------------------------------------------------------

    if (
        customer_id is not None
        and "customer_id" in candidates.columns
    ):

        customer_candidates = candidates[
            candidates["customer_id"]
            .astype(str)
            .str.strip()
            == customer_id
        ]

        if not customer_candidates.empty:
            candidates = customer_candidates

    # --------------------------------------------------------
    # No ledger
    # --------------------------------------------------------

    if candidates.empty:
        return None

    return candidates.iloc[0]


# ============================================================
# BUILD LOOKUPS
# ============================================================

def build_lookups(bank, payment):

    if bank["transaction_id"].duplicated().any():
        raise ValueError(
            "Duplicate transaction_id found in bank data."
        )

    if payment["payment_id"].duplicated().any():
        raise ValueError(
            "Duplicate payment_id found in payment data."
        )

    bank_lookup = bank.set_index(
        "transaction_id",
        drop=False
    )

    payment_lookup = payment.set_index(
        "payment_id",
        drop=False
    )

    return bank_lookup, payment_lookup


# ============================================================
# RECONCILE ONE RECORD
# ============================================================

def reconcile_record(
    exact_row,
    bank_row,
    payment_row,
    ledger
):

    transaction_id = clean_id(
        exact_row.get("transaction_id")
    )

    exact_payment_id = clean_id(
        exact_row.get("payment_id")
    )

    exact_status = str(
        exact_row.get("match_status", "")
    ).strip().upper()

    result = {

        "transaction_id":
            transaction_id,

        "payment_id":
            exact_payment_id,

        "final_status":
            None,

        "reason":
            None,

        "amount_match":
            None,

        "date_match":
            None,

        "ledger_found":
            False,

        "ledger_status":
            None,

        "payment_status":
            None,

        "date_difference":
            None,

        "amount_difference":
            None,

        "absolute_amount_difference":
            None,
    }

    # ========================================================
    # BANK RECORD MISSING
    # ========================================================

    if bank_row is None:

        result["final_status"] = "MISSING_BANK"

        result["reason"] = (
            "Bank transaction not found"
        )

        return result

    # ========================================================
    # DUPLICATE PAYMENT
    #
    # VERY IMPORTANT:
    # Exact matcher already detected this.
    # Do not try to reconcile it again.
    # ========================================================

    if exact_status == "DUPLICATE_PAYMENT":

        result["final_status"] = (
            "DUPLICATE_PAYMENT"
        )

        result["reason"] = (
            "Matching payment was already assigned "
            "to another bank transaction"
        )

        return result

    # ========================================================
    # AMOUNT MISMATCH
    #
    # Exact matcher has already identified it.
    # Preserve this status.
    # ========================================================

    if exact_status == "AMOUNT_MISMATCH":

        result["final_status"] = (
            "AMOUNT_MISMATCH"
        )

        result["reason"] = (
            "Bank reference matched a payment candidate "
            "but amounts differ"
        )

        result["amount_match"] = False

        return result

    # ========================================================
    # PAYMENT ID MISSING
    # ========================================================

    if exact_payment_id is None:

        result["final_status"] = "UNMATCHED"

        result["reason"] = (
            "No payment assigned during exact matching"
        )

        return result

    # ========================================================
    # PAYMENT RECORD
    # ========================================================

    if payment_row is None:

        result["final_status"] = "MISSING_PAYMENT"

        result["reason"] = (
            "Payment record not found"
        )

        return result

    # ========================================================
    # PAYMENT STATUS
    # ========================================================

    payment_status = str(
        payment_row.get("payment_status", "")
    ).strip().upper()

    result["payment_status"] = payment_status

    # ========================================================
    # AMOUNT
    # ========================================================

    amount_match = check_amount(
        bank_row,
        payment_row
    )

    result["amount_match"] = amount_match

    amount_difference = calculate_amount_difference(
        bank_row,
        payment_row
    )

    result["amount_difference"] = amount_difference

    result["absolute_amount_difference"] = (
        abs(amount_difference)
        if amount_difference is not None
        else None
    )

    # ========================================================
    # DATE
    #
    # transaction_date vs payment_date
    # ========================================================

    date_difference = calculate_date_difference(
        bank_row,
        payment_row
    )

    result["date_difference"] = date_difference

    date_match = (
        date_difference == 0
        if date_difference is not None
        else False
    )

    result["date_match"] = date_match

    # ========================================================
    # LEDGER
    # ========================================================

    ledger_row = find_ledger_record(
        ledger,
        payment_row
    )

    if ledger_row is not None:

        result["ledger_found"] = True

        result["ledger_status"] = str(
            ledger_row.get(
                "posting_status",
                ""
            )
        ).strip().upper()

    # ========================================================
    # BUSINESS RULE PRIORITY
    #
    # 1. PAYMENT FAILED
    # 2. PAYMENT REFUNDED
    # 3. LEDGER NOT POSTED
    # 4. AMOUNT MISMATCH
    # 5. SETTLEMENT DELAY
    # 6. CLEAN MATCH
    # ========================================================

    # --------------------------------------------------------
    # Payment failed
    # --------------------------------------------------------

    if payment_status == "FAILED":

        result["final_status"] = (
            "PAYMENT_FAILED"
        )

        result["reason"] = (
            "Payment gateway status is FAILED"
        )

        return result

    # --------------------------------------------------------
    # Payment refunded
    # --------------------------------------------------------

    if payment_status == "REFUNDED":

        result["final_status"] = (
            "PAYMENT_REFUNDED"
        )

        result["reason"] = (
            "Payment gateway status is REFUNDED"
        )

        return result

    # --------------------------------------------------------
    # Ledger posting exception
    # --------------------------------------------------------

    if (
        ledger_row is not None
        and result["ledger_status"] != VALID_LEDGER_STATUS
    ):

        result["final_status"] = (
            "LEDGER_EXCEPTION"
        )

        result["reason"] = (
            "Ledger entry exists but posting status "
            f"is {result['ledger_status']}"
        )

        return result

    # --------------------------------------------------------
    # Amount mismatch
    # --------------------------------------------------------

    if not amount_match:

        result["final_status"] = (
            "AMOUNT_MISMATCH"
        )

        result["reason"] = (
            "Bank amount differs from payment amount "
            f"by {result['absolute_amount_difference']}"
        )

        return result

    # --------------------------------------------------------
    # Settlement delay
    #
    # Any non-zero transaction/payment date difference.
    # --------------------------------------------------------

    if not date_match:

        result["final_status"] = (
            "DATE_MISMATCH"
        )

        result["reason"] = (
            "Bank transaction date differs "
            f"from payment date by {date_difference} days"
        )

        return result

    # ========================================================
    # CLEAN MATCH
    # ========================================================

    result["final_status"] = "MATCHED"

    result["reason"] = (
        "Amount, date, payment status and "
        "ledger validation passed"
    )

    return result


# ============================================================
# FULL RECONCILIATION
# ============================================================

def reconcile(
    exact,
    bank,
    payment,
    ledger,
    invoices
):

    bank, payment, ledger, invoices = prepare_data(
        bank,
        payment,
        ledger,
        invoices
    )

    bank_lookup, payment_lookup = build_lookups(
        bank,
        payment
    )

    results = []

    print("\nStarting reconciliation...")

    # ========================================================
    # PROCESS EVERY EXACT RESULT
    # ========================================================

    for _, exact_row in exact.iterrows():

        transaction_id = clean_id(
            exact_row.get("transaction_id")
        )

        # ----------------------------------------------------
        # Bank record
        # ----------------------------------------------------

        if transaction_id in bank_lookup.index:

            bank_row = bank_lookup.loc[
                transaction_id
            ]

        else:

            bank_row = None

        # ----------------------------------------------------
        # Payment record
        # ----------------------------------------------------

        payment_id = clean_id(
            exact_row.get("payment_id")
        )

        if (
            payment_id is not None
            and payment_id in payment_lookup.index
        ):

            payment_row = payment_lookup.loc[
                payment_id
            ]

        else:

            payment_row = None

        # ----------------------------------------------------
        # Reconcile
        # ----------------------------------------------------

        result = reconcile_record(
            exact_row,
            bank_row,
            payment_row,
            ledger
        )

        results.append(result)

    return pd.DataFrame(results)


# ============================================================
# VALIDATION
# ============================================================

def validate_results(results, expected_total=None):

    print("\n" + "=" * 70)
    print("VALIDATION")
    print("=" * 70)

    # --------------------------------------------------------
    # Row count
    # --------------------------------------------------------

    if expected_total is not None and len(results) != expected_total:

        raise ValueError(
            f"Expected {expected_total} reconciliation rows, "
            f"got {len(results)}."
        )

    if expected_total is not None:
        print(
            f"PASS: Exactly {expected_total} reconciliation rows."
        )
    else:
        print(
            f"PASS: Reconciliation rows generated: {len(results)}."
        )

    # --------------------------------------------------------
    # Unique transactions
    # --------------------------------------------------------

    duplicate_transactions = (
        results["transaction_id"]
        .duplicated()
        .sum()
    )

    if duplicate_transactions:

        raise ValueError(
            f"Duplicate transaction rows found: "
            f"{duplicate_transactions}"
        )

    print(
        "PASS: Every transaction_id appears once."
    )

    # --------------------------------------------------------
    # Status counts
    # --------------------------------------------------------

    print("\nFinal status counts:")

    counts = (
        results["final_status"]
        .value_counts()
        .sort_index()
    )

    print(
        counts.to_string()
    )

    # --------------------------------------------------------
    # Benchmark counts are informational here. Transaction-level
    # validation against ground truth lives in src/evaluation.
    # --------------------------------------------------------

    print("\nBenchmark comparison:")

    for status, expected_count in (
        EXPECTED_BENCHMARK_COUNTS.items()
    ):

        actual_count = int(
            (
                results["final_status"]
                == status
            ).sum()
        )

        state = (
            "PASS"
            if actual_count == expected_count
            else "CHECK"
        )

        print(
            f"{state}: "
            f"{status:<20} "
            f"benchmark={STATUS_TO_GROUND_TRUTH[status]:<18} "
            f"expected={expected_count:<3} "
            f"actual={actual_count:<3}"
        )


# ============================================================
# SUMMARY
# ============================================================

def print_summary(results):

    print("\n" + "=" * 70)
    print("RECONCILIATION SUMMARY")
    print("=" * 70)

    print(
        f"\nTotal records processed: "
        f"{len(results)}"
    )

    print("\nFinal statuses:")

    print(
        results["final_status"]
        .value_counts()
        .to_string()
    )

    # --------------------------------------------------------
    # Date difference
    # --------------------------------------------------------

    if "date_difference" in results.columns:

        print(
            "\nDate difference distribution:"
        )

        print(
            results["date_difference"]
            .value_counts(
                dropna=False
            )
            .sort_index()
            .to_string()
        )

    # --------------------------------------------------------
    # Detailed sample
    # --------------------------------------------------------

    print("\nDetailed sample:")

    sample_columns = [

        "transaction_id",

        "payment_id",

        "final_status",

        "reason",

        "amount_match",

        "date_match",

        "ledger_found",

        "ledger_status",

        "payment_status",

        "date_difference",

        "amount_difference",

        "absolute_amount_difference"
    ]

    existing_columns = [
        column
        for column in sample_columns
        if column in results.columns
    ]

    print(
        results[
            existing_columns
        ]
        .head(20)
        .to_string(index=False)
    )


# ============================================================
# SAVE RESULTS
# ============================================================

def save_results(results):

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = (
        PROCESSED_DIR
        / "reconciliation_results.csv"
    )

    results.to_csv(
        output_file,
        index=False
    )

    print(
        f"\nResults saved to:\n"
        f"{output_file}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    exact, bank, payment, ledger, invoices = (
        load_data()
    )

    results = reconcile(
        exact,
        bank,
        payment,
        ledger,
        invoices
    )

    print_summary(
        results
    )

    validate_results(
        results,
        expected_total=len(bank)
    )

    save_results(
        results
    )

    print(
        "\n" + "=" * 70
    )

    print(
        "RECONCILIATION COMPLETED"
    )

    print(
        "=" * 70
    )


if __name__ == "__main__":
    main()
