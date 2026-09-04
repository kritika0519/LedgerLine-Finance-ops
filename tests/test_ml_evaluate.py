import pandas as pd

from src.ml.evaluate import compare_baseline_to_ml


def test_compare_baseline_to_ml_reports_agreement_counts():
    df = pd.DataFrame(
        [
            {
                "risk_level": "HIGH",
                "ml_prediction": 1,
            },
            {
                "risk_level": "LOW",
                "ml_prediction": 1,
            },
            {
                "risk_level": "LOW",
                "ml_prediction": 0,
            },
        ]
    )

    report, disagree = compare_baseline_to_ml(df)

    assert report["rows"] == 3
    assert report["agree"] == 2
    assert report["disagree"] == 1
    assert len(disagree) == 1
