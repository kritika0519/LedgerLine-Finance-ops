import re
import pandas as pd

try:
    from src.data.loader import load_datasets
except ModuleNotFoundError:
    from loader import load_datasets


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(value):
    """
    Normalize text for comparison.
    """

    if pd.isna(value):
        return ""

    value = str(value).strip().upper()

    # Replace multiple spaces with one space
    value = re.sub(r"\s+", " ", value)

    return value


# ============================================================
# REFERENCE NORMALIZATION
# ============================================================

def extract_gateway_reference(value):
    """
    Extract gateway reference such as GW-126225
    from a longer bank reference.
    """

    if pd.isna(value):
        return ""

    value = str(value).upper()

    match = re.search(r"GW-\d+", value)

    if match:
        return match.group(0)

    return ""


# ============================================================
# AMOUNT NORMALIZATION
# ============================================================

def normalize_amount(value):
    """
    Convert financial amount into numeric format.
    """

    if pd.isna(value):
        return None

    value = str(value)

    # Remove currency symbols and commas
    value = re.sub(r"[₹,$]", "", value)
    value = value.replace(",", "").strip()

    try:
        return round(float(value), 2)
    except ValueError:
        return None


# ============================================================
# DATE NORMALIZATION
# ============================================================

def normalize_date(value):
    """
    Convert date into YYYY-MM-DD format.
    """

    if pd.isna(value):
        return pd.NaT

    return pd.to_datetime(
        value,
        errors="coerce"
    ).normalize()


# ============================================================
# BANK NORMALIZATION
# ============================================================

def normalize_bank_data(df):

    df = df.copy()

    df["normalized_reference"] = (
        df["reference"]
        .apply(extract_gateway_reference)
    )

    df["normalized_amount"] = (
        df["amount"]
        .apply(normalize_amount)
    )

    df["normalized_transaction_date"] = (
        df["transaction_date"]
        .apply(normalize_date)
    )

    df["normalized_description"] = (
        df["description"]
        .apply(normalize_text)
    )

    return df


# ============================================================
# PAYMENT GATEWAY NORMALIZATION
# ============================================================

def normalize_payment_data(df):

    df = df.copy()

    df["normalized_reference"] = (
        df["gateway_reference"]
        .apply(normalize_text)
    )

    df["normalized_amount"] = (
        df["amount"]
        .apply(normalize_amount)
    )

    df["normalized_payment_date"] = (
        df["payment_date"]
        .apply(normalize_date)
    )

    return df


# ============================================================
# INVOICE NORMALIZATION
# ============================================================

def normalize_invoice_data(df):

    df = df.copy()

    df["normalized_invoice_amount"] = (
        df["invoice_amount"]
        .apply(normalize_amount)
    )

    df["normalized_invoice_date"] = (
        df["invoice_date"]
        .apply(normalize_date)
    )

    df["normalized_due_date"] = (
        df["due_date"]
        .apply(normalize_date)
    )

    return df


# ============================================================
# LEDGER NORMALIZATION
# ============================================================

def normalize_ledger_data(df):

    df = df.copy()

    df["normalized_amount"] = (
        df["amount"]
        .apply(normalize_amount)
    )

    df["normalized_ledger_date"] = (
        df["ledger_date"]
        .apply(normalize_date)
    )

    return df


# ============================================================
# MAIN
# ============================================================

def normalize_datasets():

    datasets = load_datasets()

    print("\nStarting data normalization...\n")

    bank = normalize_bank_data(
        datasets["bank_transactions"]
    )

    payments = normalize_payment_data(
        datasets["payment_gateway"]
    )

    invoices = normalize_invoice_data(
        datasets["invoices"]
    )

    ledger = normalize_ledger_data(
        datasets["ledger"]
    )

    customers = datasets["customers"].copy()

    # --------------------------------------------------------
    # Save processed datasets
    # --------------------------------------------------------

    bank.to_csv(
        "data/processed/bank_transactions_processed.csv",
        index=False
    )

    payments.to_csv(
        "data/processed/payment_gateway_processed.csv",
        index=False
    )

    invoices.to_csv(
        "data/processed/invoices_processed.csv",
        index=False
    )

    ledger.to_csv(
        "data/processed/ledger_processed.csv",
        index=False
    )

    customers.to_csv(
        "data/processed/customers_processed.csv",
        index=False
    )

    print("✓ Bank transactions normalized")
    print("✓ Payment gateway normalized")
    print("✓ Invoices normalized")
    print("✓ Ledger normalized")
    print("✓ Customers copied")

    print("\nNormalization completed successfully.")


if __name__ == "__main__":
    normalize_datasets()
