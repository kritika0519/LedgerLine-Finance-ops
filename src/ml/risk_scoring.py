import pandas as pd

from src.config import RISK_WEIGHTS


def deterministic_risk_score(row):
    status = str(row.get("final_status", "MATCHED")).upper()
    score = float(RISK_WEIGHTS["severity"].get(status, 0))

    amount = abs(float(row.get("absolute_amount_difference", 0) or 0))
    score += min(
        amount / RISK_WEIGHTS["amount_high_watermark"],
        1,
    ) * RISK_WEIGHTS["amount_weight"]

    date_days = abs(float(row.get("date_difference", 0) or 0))
    score += min(date_days / 30, 1) * RISK_WEIGHTS["date_weight"]
    return min(score, 100.0)


def add_unified_risk_columns(df, probability_column="ml_risk_probability"):
    result = df.copy()
    result["deterministic_risk_score"] = result.apply(
        deterministic_risk_score,
        axis=1,
    ).round(2)
    result["risk_score"] = (
        result["deterministic_risk_score"] * 0.6
        + result[probability_column].astype(float) * 100 * 0.4
    ).round(2)
    result["risk_level"] = pd.cut(
        result["risk_score"],
        bins=[-1, 24.99, 49.99, 74.99, 100],
        labels=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
    ).astype(str)
    return result