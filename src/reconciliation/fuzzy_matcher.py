from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher
import re

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

DATE_FORMATS = [
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
]

# Maximum number of days used for date similarity.
DATE_WINDOW_DAYS = 30


# ============================================================
# BASIC HELPERS
# ============================================================

def safe_float(value):
    """
    Convert a value safely to float.
    Returns None if conversion is not possible.
    """
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_date(value):
    """
    Safely convert a single date value to datetime.

    IMPORTANT:
    We intentionally do NOT use pd.to_datetime() on scalar values.
    This avoids the pandas/numpy issue encountered in the project.
    """

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    if isinstance(value, datetime):
        return value

    # Handle pandas Timestamp without calling pd.to_datetime()
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    value = str(value).strip()

    if not value:
        return None

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    # Last fallback:
    # Handle values like "2026-08-30 00:00:00"
    if len(value) >= 10:
        date_part = value[:10]

        try:
            return datetime.strptime(date_part, "%Y-%m-%d")
        except ValueError:
            pass

    return None


# ============================================================
# DATE SIMILARITY
# ============================================================

def date_similarity(date1, date2):
    """
    Calculate similarity between two dates.

    Returns:
        1.0  -> same date
        0.0  -> very far apart / invalid

    Difference of one day gets a high score.
    """

    d1 = parse_date(date1)
    d2 = parse_date(date2)

    if d1 is None or d2 is None:
        return 0.0

    difference = abs((d1.date() - d2.date()).days)

    if difference == 0:
        return 1.0

    if difference >= DATE_WINDOW_DAYS:
        return 0.0

    # Linear decay
    return max(
        0.0,
        1.0 - (difference / DATE_WINDOW_DAYS)
    )


# ============================================================
# AMOUNT SIMILARITY
# ============================================================

def amount_similarity(amount1, amount2):
    """
    Compare transaction amounts.

    Exact amount = 1.0

    For different amounts, similarity decreases according
    to relative difference.
    """

    a1 = safe_float(amount1)
    a2 = safe_float(amount2)

    if a1 is None or a2 is None:
        return 0.0

    if a1 == a2:
        return 1.0

    denominator = max(abs(a1), abs(a2), 1.0)

    difference = abs(a1 - a2) / denominator

    return max(
        0.0,
        1.0 - difference
    )


# ============================================================
# TEXT SIMILARITY
# ============================================================

def text_similarity(text1, text2):
    """
    Calculate similarity between two text values.
    """

    if text1 is None or text2 is None:
        return 0.0

    try:
        if pd.isna(text1) or pd.isna(text2):
            return 0.0
    except Exception:
        pass

    s1 = str(text1).strip().lower()
    s2 = str(text2).strip().lower()

    if not s1 or not s2:
        return 0.0

    if s1 == s2:
        return 1.0

    return SequenceMatcher(None, s1, s2).ratio()


# ============================================================
# ID EXTRACTION
# ============================================================

def extract_customer_id(text):
    """
    Extract customer ID such as CUST0344 from text.
    """

    if text is None:
        return None

    try:
        if pd.isna(text):
            return None
    except Exception:
        pass

    match = re.search(
        r"\bCUST\d+\b",
        str(text),
        re.IGNORECASE
    )

    if match:
        return match.group(0).upper()

    return None


def extract_gateway_reference(text):
    """
    Extract gateway reference such as GW-330283.
    """

    if text is None:
        return None

    try:
        if pd.isna(text):
            return None
    except Exception:
        pass

    match = re.search(
        r"\bGW[-/]?\d+\b",
        str(text),
        re.IGNORECASE
    )

    if match:
        return match.group(0).upper().replace("/", "-")

    return None


# ============================================================
# ROW LEVEL SCORE
# ============================================================

def calculate_match_score(bank_row, payment_row):
    """
    Calculate fuzzy match score between one bank transaction
    and one payment gateway record.
    """

    # --------------------------------------------------------
    # Amount
    # --------------------------------------------------------

    amount_score = amount_similarity(
        bank_row.get("amount"),
        payment_row.get("amount")
    )

    # --------------------------------------------------------
    # Date
    # --------------------------------------------------------

    date_score = date_similarity(
        bank_row.get("transaction_date"),
        payment_row.get("payment_date")
    )

    # --------------------------------------------------------
    # Customer ID
    # --------------------------------------------------------

    bank_customer = extract_customer_id(
        bank_row.get("reference", "")
    )

    if bank_customer is None:
        bank_customer = extract_customer_id(
            bank_row.get("description", "")
        )

    payment_customer = payment_row.get("customer_id")

    if payment_customer is not None:
        payment_customer = str(payment_customer).strip().upper()

    if bank_customer and payment_customer:
        customer_score = (
            1.0
            if bank_customer == payment_customer
            else 0.0
        )
    else:
        customer_score = 0.0

    # --------------------------------------------------------
    # Gateway reference
    # --------------------------------------------------------

    bank_reference = extract_gateway_reference(
        bank_row.get("reference", "")
    )

    if bank_reference is None:
        bank_reference = extract_gateway_reference(
            bank_row.get("description", "")
        )

    payment_reference = payment_row.get(
        "gateway_reference"
    )

    if payment_reference is not None:
        payment_reference = extract_gateway_reference(
            payment_reference
        )

    if bank_reference and payment_reference:
        reference_score = (
            1.0
            if bank_reference == payment_reference
            else text_similarity(
                bank_reference,
                payment_reference
            )
        )
    else:
        reference_score = 0.0

    # --------------------------------------------------------
    # Currency
    # --------------------------------------------------------

    bank_currency = str(
        bank_row.get("currency", "")
    ).strip().upper()

    payment_currency = str(
        payment_row.get("currency", "")
    ).strip().upper()

    if bank_currency and payment_currency:
        currency_score = (
            1.0
            if bank_currency == payment_currency
            else 0.0
        )
    else:
        currency_score = 0.0

    # --------------------------------------------------------
    # Final weighted score
    # --------------------------------------------------------
    #
    # Amount       = 45%
    # Date         = 20%
    # Customer     = 15%
    # Reference    = 15%
    # Currency     = 5%
    #

    score = (
        0.45 * amount_score
        + 0.20 * date_score
        + 0.15 * customer_score
        + 0.15 * reference_score
        + 0.05 * currency_score
    )

    return round(float(score), 4)


# ============================================================
# CONFIDENCE
# ============================================================

def get_confidence(score):
    """
    Convert numeric score into confidence level.
    """

    if score >= 0.85:
        return "HIGH_CONFIDENCE"

    if score >= 0.70:
        return "MEDIUM_CONFIDENCE"

    return "LOW_CONFIDENCE"


# ============================================================
# FUZZY MATCHING
# ============================================================

def fuzzy_match(bank, payment):
    """
    Match bank transactions against payment gateway records.

    Parameters
    ----------
    bank : pandas.DataFrame
        Bank transaction data.

    payment : pandas.DataFrame
        Payment gateway data.

    Returns
    -------
    pandas.DataFrame
        Fuzzy reconciliation results.
    """

    print("Starting fuzzy reconciliation...")

    # --------------------------------------------------------
    # Validate inputs
    # --------------------------------------------------------

    if not isinstance(bank, pd.DataFrame):
        raise TypeError("bank must be a pandas DataFrame")

    if not isinstance(payment, pd.DataFrame):
        raise TypeError("payment must be a pandas DataFrame")

    required_bank_columns = [
        "transaction_id",
        "transaction_date",
        "amount",
        "currency",
    ]

    required_payment_columns = [
        "payment_id",
        "payment_date",
        "amount",
        "currency",
    ]

    missing_bank = [
        col
        for col in required_bank_columns
        if col not in bank.columns
    ]

    missing_payment = [
        col
        for col in required_payment_columns
        if col not in payment.columns
    ]

    if missing_bank:
        raise ValueError(
            f"Missing bank columns: {missing_bank}"
        )

    if missing_payment:
        raise ValueError(
            f"Missing payment columns: {missing_payment}"
        )

    # --------------------------------------------------------
    # Reset indexes
    # --------------------------------------------------------

    bank = bank.copy().reset_index(drop=True)
    payment = payment.copy().reset_index(drop=True)

    results = []

    # Payments already assigned
    used_payment_indexes = set()

    # --------------------------------------------------------
    # Match every bank transaction
    # --------------------------------------------------------

    for bank_index, bank_row in bank.iterrows():

        best_score = -1.0
        best_payment_index = None

        for payment_index, payment_row in payment.iterrows():

            # Do not reuse the same payment
            if payment_index in used_payment_indexes:
                continue

            score = calculate_match_score(
                bank_row,
                payment_row
            )

            if score > best_score:
                best_score = score
                best_payment_index = payment_index

        # ----------------------------------------------------
        # No candidate
        # ----------------------------------------------------

        if best_payment_index is None:

            results.append({
                "transaction_id": bank_row.get(
                    "transaction_id"
                ),
                "payment_id": None,
                "invoice_id": None,
                "bank_amount": bank_row.get("amount"),
                "payment_amount": None,
                "bank_date": bank_row.get(
                    "transaction_date"
                ),
                "payment_date": None,
                "match_score": 0.0,
                "match_confidence": "LOW_CONFIDENCE",
                "match_status": "NO_MATCH",
            })

            continue

        # ----------------------------------------------------
        # Get matched payment
        # ----------------------------------------------------

        payment_row = payment.iloc[
            best_payment_index
        ]

        used_payment_indexes.add(
            best_payment_index
        )

        confidence = get_confidence(
            best_score
        )

        # ----------------------------------------------------
        # Result
        # ----------------------------------------------------

        results.append({
            "transaction_id": bank_row.get(
                "transaction_id"
            ),

            "payment_id": payment_row.get(
                "payment_id"
            ),

            "invoice_id": payment_row.get(
                "invoice_id"
            ),

            "bank_amount": bank_row.get(
                "amount"
            ),

            "payment_amount": payment_row.get(
                "amount"
            ),

            "bank_date": bank_row.get(
                "transaction_date"
            ),

            "payment_date": payment_row.get(
                "payment_date"
            ),

            "match_score": best_score,

            "match_confidence": confidence,

            "match_status": "FUZZY_MATCH",
        })

    # --------------------------------------------------------
    # Convert to DataFrame
    # --------------------------------------------------------

    results_df = pd.DataFrame(results)

    return results_df


# ============================================================
# SAVE RESULTS
# ============================================================

def save_results(results, output_path=None):
    """
    Save fuzzy matching results to CSV.
    """

    if output_path is None:
        project_root = Path(__file__).resolve().parents[2]

        output_path = (
            project_root
            / "data"
            / "processed"
            / "fuzzy_match_results.csv"
        )

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    results.to_csv(
        output_path,
        index=False
    )

    return output_path