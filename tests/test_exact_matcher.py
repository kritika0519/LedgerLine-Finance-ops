import pandas as pd

from src.reconciliation.exact_matcher import (
    amounts_match,
    extract_numeric_id,
    normalize_reference,
)


def test_normalize_reference_extracts_gateway_reference():
    assert (
        normalize_reference("CMS/GW-188297/STRIPE/CUST0322")
        == "GW-188297"
    )


def test_normalize_reference_supports_duplicate_style_reference():
    assert normalize_reference("gw-dup-0001") == "GW-DUP-0001"


def test_extract_numeric_id_is_prefix_agnostic():
    assert extract_numeric_id("TXN0074") == 74
    assert extract_numeric_id("PAY0074") == 74
    assert extract_numeric_id("BANK-PAY-000074") == 74


def test_amounts_match_uses_currency_tolerance():
    assert amounts_match(100.00, 100.005)
    assert not amounts_match(100.00, 100.02)
    assert not amounts_match(pd.NA, 100.00)
