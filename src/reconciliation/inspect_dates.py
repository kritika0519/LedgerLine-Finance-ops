import pandas as pd

bank = pd.read_csv("data/raw/bank_transactions.csv")
pay = pd.read_csv("data/raw/payment_gateway.csv")
inv = pd.read_csv("data/raw/invoices.csv")
led = pd.read_csv("data/raw/ledger.csv")
gt = pd.read_csv("data/ground truth/ground_truth.csv")

# Only DATE_MISMATCH cases
x = gt[gt["expected_status"] == "DATE_MISMATCH"].copy()

# Merge payment
m = x.merge(
    pay[["payment_id", "payment_date"]],
    on="payment_id",
    how="left"
)

# Merge bank
m = m.merge(
    bank[["transaction_id", "transaction_date", "value_date"]],
    on="transaction_id",
    how="left"
)

# Merge invoice
m = m.merge(
    inv[["invoice_id", "invoice_date", "due_date"]],
    on="invoice_id",
    how="left"
)

# Merge ledger
m = m.merge(
    led[["invoice_id", "customer_id", "ledger_date"]],
    on=["invoice_id", "customer_id"],
    how="left"
)

# Convert dates
date_columns = [
    "payment_date",
    "transaction_date",
    "value_date",
    "invoice_date",
    "due_date",
    "ledger_date"
]

for col in date_columns:
    m[col] = pd.to_datetime(m[col])

# Calculate differences
m["bank_vs_payment_days"] = (
    m["transaction_date"] - m["payment_date"]
).dt.days

m["value_vs_payment_days"] = (
    m["value_date"] - m["payment_date"]
).dt.days

m["ledger_vs_payment_days"] = (
    m["ledger_date"] - m["payment_date"]
).dt.days

m["ledger_vs_bank_value_days"] = (
    m["ledger_date"] - m["value_date"]
).dt.days

print("\n")
print("=" * 130)
print("DATE MISMATCH ANALYSIS")
print("=" * 130)

columns = [
    "transaction_id",
    "payment_date",
    "transaction_date",
    "value_date",
    "invoice_date",
    "due_date",
    "ledger_date",
    "bank_vs_payment_days",
    "value_vs_payment_days",
    "ledger_vs_payment_days",
    "ledger_vs_bank_value_days"
]

print(m[columns].to_string(index=False))

print("\n")
print("=" * 130)
print("DATE DIFFERENCE SUMMARY")
print("=" * 130)

print("\nBank transaction vs Payment:")
print(m["bank_vs_payment_days"].describe())

print("\nBank value vs Payment:")
print(m["value_vs_payment_days"].describe())

print("\nLedger vs Payment:")
print(m["ledger_vs_payment_days"].describe())

print("\n")
print("=" * 130)
print(f"TOTAL DATE MISMATCH RECORDS: {len(m)}")
print("=" * 130)