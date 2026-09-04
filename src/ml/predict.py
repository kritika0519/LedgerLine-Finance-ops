from pathlib import Path
import sys

import joblib
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import ML_RISK_THRESHOLDS, PROCESSED_DIR  # noqa: E402
from src.ml.explain import (  # noqa: E402
    create_prediction_reason,
    risk_level_from_probability,
)
from src.ml.feature_engineering import (  # noqa: E402
    build_feature_frame,
    load_classified_data,
)
from src.ml.risk_scoring import add_unified_risk_columns  # noqa: E402
from src.ml.train import MODEL_FILE  # noqa: E402


OUTPUT_FILE = PROCESSED_DIR / "ml_risk_results.csv"


def predict_risk(df=None, model_file=MODEL_FILE):
    if df is None:
        df = load_classified_data()

    feature_frame, feature_columns = build_feature_frame(df)

    model = joblib.load(model_file)
    probabilities = model.predict_proba(
        feature_frame[feature_columns]
    )[:, 1]
    predictions = model.predict(feature_frame[feature_columns])

    output = feature_frame.copy()
    output["ml_risk_probability"] = probabilities.round(4)
    output["ml_prediction"] = predictions
    output["ml_risk_level"] = output["ml_risk_probability"].apply(
        lambda value: risk_level_from_probability(
            float(value),
            ML_RISK_THRESHOLDS,
        )
    )
    output["ml_reason"] = output.apply(
        create_prediction_reason,
        axis=1,
    )
    output = add_unified_risk_columns(output)
    output["top_risk_factors"] = output["ml_reason"]

    return output


def save_predictions(df, output_file=OUTPUT_FILE):
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, index=False)
    return output_file


def main():
    results = predict_risk()
    output_file = save_predictions(results)

    print("=" * 70)
    print("ML RISK PREDICTION")
    print("=" * 70)
    print(f"Rows: {len(results)}")
    print("\nML risk levels:")
    print(results["ml_risk_level"].value_counts().to_string())
    print("\nSample predictions:")
    columns = [
        "transaction_id",
        "payment_id",
        "final_status",
        "exception_type",
        "risk_level",
        "ml_risk_probability",
        "ml_risk_level",
        "ml_prediction",
        "ml_reason",
    ]
    columns = [column for column in columns if column in results.columns]
    print(results[columns].head(20).to_string(index=False))
    print(f"\nSaved predictions: {output_file}")


if __name__ == "__main__":
    main()
