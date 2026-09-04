import pandas as pd
from pathlib import Path


# Project root directory
BASE_DIR = Path(__file__).resolve().parents[2]

# Raw data directory
RAW_DATA_DIR = BASE_DIR / "data" / "raw"


def load_datasets():
    """
    Load all raw financial datasets.
    """

    datasets = {
        "customers": pd.read_csv(
            RAW_DATA_DIR / "customers.csv"
        ),

        "invoices": pd.read_csv(
            RAW_DATA_DIR / "invoices.csv"
        ),

        "payment_gateway": pd.read_csv(
            RAW_DATA_DIR / "payment_gateway.csv"
        ),

        "bank_transactions": pd.read_csv(
            RAW_DATA_DIR / "bank_transactions.csv"
        ),

        "ledger": pd.read_csv(
            RAW_DATA_DIR / "ledger.csv"
        ),
    }

    return datasets


if __name__ == "__main__":

    data = load_datasets()

    print("\nDataset Loading Successful!\n")

    for name, df in data.items():
        print(f"{name}: {df.shape[0]} rows, {df.shape[1]} columns")