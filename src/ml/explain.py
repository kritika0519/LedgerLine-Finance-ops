import pandas as pd


def risk_level_from_probability(probability, thresholds):
    if probability >= thresholds["HIGH"]:
        return "CRITICAL"

    if probability >= thresholds["MEDIUM"]:
        return "HIGH"

    if probability >= thresholds["LOW"]:
        return "MEDIUM"

    return "LOW"


def top_feature_importance(model, feature_names, limit=15):
    estimator = model.named_steps["model"]

    if hasattr(estimator, "feature_importances_"):
        values = estimator.feature_importances_
    elif hasattr(estimator, "coef_"):
        values = abs(estimator.coef_[0])
    else:
        return pd.DataFrame(
            columns=["feature", "importance"]
        )

    importance = pd.DataFrame(
        {
            "feature": feature_names,
            "importance": values,
        }
    )

    return importance.sort_values(
        "importance",
        ascending=False,
    ).head(limit)


def create_prediction_reason(row):
    reasons = []

    final_status = str(row.get("final_status", "")).upper()
    payment_status = str(row.get("payment_status", "")).upper()
    ledger_status = str(row.get("ledger_status", "")).upper()
    date_difference = row.get("date_difference", 0)
    amount_difference = row.get("absolute_amount_difference", 0)

    if final_status in {
        "AMOUNT_MISMATCH",
        "DUPLICATE_PAYMENT",
        "LEDGER_EXCEPTION",
        "PAYMENT_FAILED",
        "PAYMENT_REFUNDED",
    }:
        reasons.append(f"Final status is {final_status}")

    if payment_status in {"FAILED", "REFUNDED"}:
        reasons.append(f"Payment status is {payment_status}")

    if ledger_status and ledger_status not in {
        "POSTED",
        "UNKNOWN",
        "NAN",
        "NONE",
        "",
    }:
        reasons.append(f"Ledger status is {ledger_status}")

    try:
        if float(amount_difference) > 0:
            reasons.append(
                f"Amount difference is {float(amount_difference):.2f}"
            )
    except (TypeError, ValueError):
        pass

    try:
        if float(date_difference) > 7:
            reasons.append(
                f"Date difference is {int(float(date_difference))} days"
            )
    except (TypeError, ValueError):
        pass

    if not reasons:
        reasons.append("No major deterministic risk factor detected")

    return "; ".join(reasons)
