import pandas as pd

bank = pd.read_csv("data/raw/bank_transactions.csv")
pay = pd.read_csv("data/raw/payment_gateway.csv")
inv = pd.read_csv("data/raw/invoices.csv")
led = pd.read_csv("data/raw/ledger.csv")
gt = pd.read_csv("data/ground truth/ground_truth.csv")

# Get MATCHED records
x = gt[gt["expected_status"] == "MATCHED"].copy()

# Payment
m = x.merge(
    pay[["payment_id", "payment_date"]],
    on="payment_id",
    how="left"
)

# Bank
m = m.merge(
    bank[["transaction_id", "transaction_date", "value_date"]],
    on="transaction_id",
    how="left"
)

# Ledger
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
    "ledger_date"
]

for col in date_columns:
    m[col] = pd.to_datetime(m[col])

# Differences
m["bank_vs_payment_days"] = (
    m["transaction_date"] - m["payment_date"]
).dt.days

m["value_vs_payment_days"] = (
    m["value_date"] - m["payment_date"]
).dt.days

m["ledger_vs_payment_days"] = (
    m["ledger_date"] - m["payment_date"]
).dt.days

print("\n")
print("=" * 110)
print("MATCHED DATE ANALYSIS")
print("=" * 110)

columns = [
    "transaction_id",
    "payment_date",
    "transaction_date",
    "value_date",
    "ledger_date",
    "bank_vs_payment_days",
    "value_vs_payment_days",
    "ledger_vs_payment_days"
]

print(m[columns].to_string(index=False))

print("\n")
print("=" * 110)
print("MATCHED DATE DIFFERENCE SUMMARY")
print("=" * 110)

print("\nBank transaction vs Payment:")
print(m["bank_vs_payment_days"].describe())

print("\nBank value vs Payment:")
print(m["value_vs_payment_days"].describe())

print("\nLedger vs Payment:")
print(m["ledger_vs_payment_days"].describe())

print("\n")
print("=" * 110)
print(f"TOTAL MATCHED RECORDS ANALYZED: {len(m)}")
print("=" * 110)