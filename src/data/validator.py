import pandas as pd
from pathlib import Path

try:
    from src.data.loader import load_datasets
except ModuleNotFoundError:
    from loader import load_datasets


# ============================================================
# REQUIRED COLUMNS
# ============================================================

REQUIRED_COLUMNS = {
    "customers": [
        "customer_id",
        "customer_name",
        "customer_email",
        "customer_phone",
        "company_name",
        "customer_type",
        "country",
        "currency",
        "account_status",
    ],

    "invoices": [
        "invoice_id",
        "customer_id",
        "invoice_date",
        "due_date",
        "invoice_amount",
        "currency",
        "description",
        "invoice_status",
    ],

    "payment_gateway": [
        "payment_id",
        "invoice_id",
        "customer_id",
        "payment_date",
        "amount",
        "currency",
        "gateway",
        "gateway_reference",
        "payment_method",
        "payment_status",
    ],

    "bank_transactions": [
        "transaction_id",
        "transaction_date",
        "value_date",
        "amount",
        "currency",
        "description",
        "reference",
        "account_id",
        "transaction_type",
    ],

    "ledger": [
        "ledger_id",
        "ledger_date",
        "invoice_id",
        "customer_id",
        "amount",
        "currency",
        "account_code",
        "entry_type",
        "description",
        "reference",
        "posting_status",
    ],
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def check_required_columns(name, df):
    """Check whether all required columns exist."""

    required = REQUIRED_COLUMNS[name]

    missing_columns = [
        column for column in required
        if column not in df.columns
    ]

    if missing_columns:
        print(f"❌ {name}: Missing columns -> {missing_columns}")
        return False

    print(f"✓ {name}: Required columns present")
    return True


def check_duplicate_ids(name, df, id_column):
    """Check duplicate values in the primary ID column."""

    duplicate_count = df[id_column].duplicated().sum()

    if duplicate_count > 0:
        print(
            f"❌ {name}: {duplicate_count} duplicate "
            f"{id_column} values found"
        )
        return False

    print(f"✓ {name}: No duplicate {id_column}")
    return True


def check_missing_ids(name, df, id_column):
    """Check missing values in the primary ID column."""

    missing_count = df[id_column].isna().sum()

    if missing_count > 0:
        print(
            f"❌ {name}: {missing_count} missing "
            f"{id_column} values"
        )
        return False

    print(f"✓ {name}: No missing {id_column}")
    return True


def check_foreign_key(
    child_name,
    child_df,
    child_column,
    parent_name,
    parent_df,
    parent_column,
):
    """Check whether child IDs exist in parent dataset."""

    invalid = (
        ~child_df[child_column].isin(
            parent_df[parent_column]
        )
        & child_df[child_column].notna()
    )

    invalid_count = invalid.sum()

    if invalid_count > 0:
        print(
            f"⚠ {child_name}: {invalid_count} invalid "
            f"{child_column} references"
        )
        return False

    print(
        f"✓ {child_name}: {child_column} references valid"
    )
    return True


# ============================================================
# MAIN VALIDATION
# ============================================================

def validate_datasets():

    datasets = load_datasets()

    print("\n")
    print("=" * 60)
    print("              DATA VALIDATION REPORT")
    print("=" * 60)

    validation_passed = True

    # --------------------------------------------------------
    # CUSTOMERS
    # --------------------------------------------------------

    print("\n[CUSTOMERS]")

    customers = datasets["customers"]

    if not check_required_columns(
        "customers",
        customers
    ):
        validation_passed = False

    if not check_duplicate_ids(
        "customers",
        customers,
        "customer_id"
    ):
        validation_passed = False

    if not check_missing_ids(
        "customers",
        customers,
        "customer_id"
    ):
        validation_passed = False

    # --------------------------------------------------------
    # INVOICES
    # --------------------------------------------------------

    print("\n[INVOICES]")

    invoices = datasets["invoices"]

    if not check_required_columns(
        "invoices",
        invoices
    ):
        validation_passed = False

    if not check_duplicate_ids(
        "invoices",
        invoices,
        "invoice_id"
    ):
        validation_passed = False

    if not check_missing_ids(
        "invoices",
        invoices,
        "invoice_id"
    ):
        validation_passed = False

    if not check_foreign_key(
        "invoices",
        invoices,
        "customer_id",
        "customers",
        customers,
        "customer_id"
    ):
        validation_passed = False

    # --------------------------------------------------------
    # PAYMENT GATEWAY
    # --------------------------------------------------------

    print("\n[PAYMENT GATEWAY]")

    payments = datasets["payment_gateway"]

    if not check_required_columns(
        "payment_gateway",
        payments
    ):
        validation_passed = False

    if not check_duplicate_ids(
        "payment_gateway",
        payments,
        "payment_id"
    ):
        validation_passed = False

    if not check_missing_ids(
        "payment_gateway",
        payments,
        "payment_id"
    ):
        validation_passed = False

    if not check_foreign_key(
        "payment_gateway",
        payments,
        "invoice_id",
        "invoices",
        invoices,
        "invoice_id"
    ):
        validation_passed = False

    if not check_foreign_key(
        "payment_gateway",
        payments,
        "customer_id",
        "customers",
        customers,
        "customer_id"
    ):
        validation_passed = False

    # --------------------------------------------------------
    # BANK TRANSACTIONS
    # --------------------------------------------------------

    print("\n[BANK TRANSACTIONS]")

    bank = datasets["bank_transactions"]

    if not check_required_columns(
        "bank_transactions",
        bank
    ):
        validation_passed = False

    if not check_duplicate_ids(
        "bank_transactions",
        bank,
        "transaction_id"
    ):
        validation_passed = False

    if not check_missing_ids(
        "bank_transactions",
        bank,
        "transaction_id"
    ):
        validation_passed = False

    # --------------------------------------------------------
    # LEDGER
    # --------------------------------------------------------

    print("\n[LEDGER]")

    ledger = datasets["ledger"]

    if not check_required_columns(
        "ledger",
        ledger
    ):
        validation_passed = False

    if not check_duplicate_ids(
        "ledger",
        ledger,
        "ledger_id"
    ):
        validation_passed = False

    if not check_missing_ids(
        "ledger",
        ledger,
        "ledger_id"
    ):
        validation_passed = False

    if not check_foreign_key(
        "ledger",
        ledger,
        "invoice_id",
        "invoices",
        invoices,
        "invoice_id"
    ):
        validation_passed = False

    if not check_foreign_key(
        "ledger",
        ledger,
        "customer_id",
        "customers",
        customers,
        "customer_id"
    ):
        validation_passed = False

    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    print("\n")
    print("=" * 60)

    if validation_passed:
        print("        ✅ DATA VALIDATION PASSED")
    else:
        print("        ⚠ DATA VALIDATION FOUND ISSUES")

    print("=" * 60)


if __name__ == "__main__":
    validate_datasets()
