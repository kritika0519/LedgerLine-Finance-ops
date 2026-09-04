from pathlib import Path
import json
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ml.predict import OUTPUT_FILE, predict_risk, save_predictions  # noqa: E402


REPORT_FILE = PROJECT_ROOT / "models" / "risk_baseline_vs_ml.json"

BASELINE_HIGH_RISK_LEVELS = {
    "HIGH",
    "CRITICAL",
}


def compare_baseline_to_ml(df):
    result = df.copy()
    result["baseline_high_attention"] = (
        result["risk_level"].astype(str).str.upper().isin(
            BASELINE_HIGH_RISK_LEVELS
        )
    ).astype(int)

    result["ml_high_attention"] = (
        result["ml_prediction"].astype(int)
    )

    agree = result[
        result["baseline_high_attention"]
        == result["ml_high_attention"]
    ]
    disagree = result[
        result["baseline_high_attention"]
        != result["ml_high_attention"]
    ]

    false_positive = result[
        (result["baseline_high_attention"] == 0)
        & (result["ml_high_attention"] == 1)
    ]
    false_negative = result[
        (result["baseline_high_attention"] == 1)
        & (result["ml_high_attention"] == 0)
    ]

    report = {
        "rows": int(len(result)),
        "agree": int(len(agree)),
        "disagree": int(len(disagree)),
        "ml_high_attention": int(result["ml_high_attention"].sum()),
        "baseline_high_attention": int(
            result["baseline_high_attention"].sum()
        ),
        "false_positive_vs_baseline": int(len(false_positive)),
        "false_negative_vs_baseline": int(len(false_negative)),
        "note": (
            "Baseline comparison uses existing deterministic risk_level. "
            "Differences are review candidates, not proof that either "
            "method is wrong."
        ),
    }

    return report, disagree


def save_report(report, report_file=REPORT_FILE):
    report_file = Path(report_file)
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    return report_file


def main():
    if OUTPUT_FILE.exists():
        df = pd.read_csv(OUTPUT_FILE)
    else:
        df = predict_risk()
        save_predictions(df)

    report, disagree = compare_baseline_to_ml(df)
    report_file = save_report(report)

    print("=" * 70)
    print("BASELINE VS ML RISK COMPARISON")
    print("=" * 70)
    print(json.dumps(report, indent=2))

    if not disagree.empty:
        print("\nSample disagreements:")
        columns = [
            "transaction_id",
            "final_status",
            "risk_level",
            "ml_risk_probability",
            "ml_risk_level",
            "ml_prediction",
        ]
        print(disagree[columns].head(20).to_string(index=False))

    print(f"\nSaved report: {report_file}")


if __name__ == "__main__":
    main()
