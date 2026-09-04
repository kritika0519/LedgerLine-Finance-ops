import pandas as pd

# Load data
bank = pd.read_csv("data/raw/bank_transactions.csv")
pay = pd.read_csv("data/raw/payment_gateway.csv")
inv = pd.read_csv("data/raw/invoices.csv")
led = pd.read_csv("data/raw/ledger.csv")
gt = pd.read_csv("data/ground truth/ground_truth.csv")

# ---------------------------------------------------------
# 1. Select only AMOUNT_MISMATCH ground-truth records
# ---------------------------------------------------------

x = gt[gt["expected_status"] == "AMOUNT_MISMATCH"].copy()

# ---------------------------------------------------------
# 2. Get gateway amount
#    We DON'T take invoice_id/customer_id here because
#    ground_truth already contains them.
# ---------------------------------------------------------

m = x.merge(
    pay[["payment_id", "amount"]],
    on="payment_id",
    how="left"
)

m = m.rename(columns={
    "amount": "gateway_amount"
})

# ---------------------------------------------------------
# 3. Get bank amount
# ---------------------------------------------------------

m = m.merge(
    bank[["transaction_id", "amount"]],
    on="transaction_id",
    how="left"
)

m = m.rename(columns={
    "amount": "bank_amount"
})

# ---------------------------------------------------------
# 4. Get invoice amount
# ---------------------------------------------------------

m = m.merge(
    inv[["invoice_id", "invoice_amount"]],
    on="invoice_id",
    how="left"
)

# ---------------------------------------------------------
# 5. Get ledger amount
# ---------------------------------------------------------

m = m.merge(
    led[["invoice_id", "customer_id", "amount"]],
    on=["invoice_id", "customer_id"],
    how="left"
)

m = m.rename(columns={
    "amount": "ledger_amount"
})

# ---------------------------------------------------------
# 6. Display results
# ---------------------------------------------------------

print("\n")
print("=" * 100)
print("AMOUNT MISMATCH ANALYSIS")
print("=" * 100)

columns = [
    "transaction_id",
    "payment_id",
    "invoice_id",
    "bank_amount",
    "gateway_amount",
    "invoice_amount",
    "ledger_amount"
]

print(m[columns].to_string(index=False))

print("\n")
print("=" * 100)
print(f"TOTAL AMOUNT MISMATCH RECORDS: {len(m)}")
print("=" * 100)