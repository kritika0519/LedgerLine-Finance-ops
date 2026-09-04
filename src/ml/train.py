from pathlib import Path
import json
import sys

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import ML_RISK_THRESHOLDS  # noqa: E402
from src.ml.explain import top_feature_importance  # noqa: E402
from src.ml.feature_engineering import (  # noqa: E402
    BOOLEAN_FEATURES,
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    build_feature_frame,
    get_feature_documentation,
    load_classified_data,
)


MODEL_DIR = PROJECT_ROOT / "models"
MODEL_VERSION = "1.0.0"
MODEL_FILE = MODEL_DIR / "risk_model.joblib"
METRICS_FILE = MODEL_DIR / "risk_model_metrics.json"
METADATA_FILE = MODEL_DIR / "risk_model_metadata.json"
FEATURE_IMPORTANCE_FILE = MODEL_DIR / "feature_importance.csv"


def _make_preprocessor():
    numeric_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        [
            (
                "imputer",
                SimpleImputer(
                    strategy="constant",
                    fill_value="UNKNOWN",
                ),
            ),
            (
                "onehot",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=False,
                ),
            ),
        ]
    )

    return ColumnTransformer(
        [
            ("numeric", numeric_pipeline, NUMERIC_FEATURES),
            ("boolean", "passthrough", BOOLEAN_FEATURES),
            (
                "categorical",
                categorical_pipeline,
                CATEGORICAL_FEATURES,
            ),
        ]
    )


def _candidate_models():
    return {
        "logistic_regression": LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            random_state=42,
        ),
        "decision_tree": DecisionTreeClassifier(
            max_depth=5,
            min_samples_leaf=10,
            class_weight="balanced",
            random_state=42,
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=200,
            max_depth=6,
            min_samples_leaf=5,
            class_weight="balanced",
            random_state=42,
        ),
    }


def _metrics(model, x, y):
    predictions = model.predict(x)

    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(x)[:, 1]
    else:
        probabilities = predictions

    try:
        roc_auc = roc_auc_score(y, probabilities)
    except ValueError:
        roc_auc = None

    return {
        "accuracy": round(float(accuracy_score(y, predictions)), 4),
        "precision": round(
            float(precision_score(y, predictions, zero_division=0)),
            4,
        ),
        "recall": round(
            float(recall_score(y, predictions, zero_division=0)),
            4,
        ),
        "f1": round(float(f1_score(y, predictions, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc), 4)
        if roc_auc is not None
        else None,
        "confusion_matrix": confusion_matrix(y, predictions).tolist(),
    }


def _feature_names(model):
    preprocessor = model.named_steps["preprocessor"]
    return preprocessor.get_feature_names_out().tolist()


def train_models(df=None):
    if df is None:
        df = load_classified_data()

    feature_frame, feature_columns = build_feature_frame(df)
    x = feature_frame[feature_columns]
    y = feature_frame["high_attention"]

    if y.nunique() < 2:
        raise ValueError(
            "Target has fewer than two classes; supervised training "
            "is not meaningful."
        )

    x_train, x_temp, y_train, y_temp = train_test_split(
        x,
        y,
        test_size=0.30,
        stratify=y,
        random_state=42,
    )

    x_val, x_test, y_val, y_test = train_test_split(
        x_temp,
        y_temp,
        test_size=0.50,
        stratify=y_temp,
        random_state=42,
    )

    results = {}
    fitted_models = {}

    for name, estimator in _candidate_models().items():
        model = Pipeline(
            [
                ("preprocessor", _make_preprocessor()),
                ("model", estimator),
            ]
        )
        model.fit(x_train, y_train)
        fitted_models[name] = model
        results[name] = {
            "validation": _metrics(model, x_val, y_val),
            "test": _metrics(model, x_test, y_test),
        }

    selected_name = sorted(
        results,
        key=lambda name: (
            results[name]["validation"]["recall"],
            results[name]["validation"]["f1"],
            results[name]["validation"]["roc_auc"] or 0,
        ),
        reverse=True,
    )[0]

    selected_model = fitted_models[selected_name]
    feature_names = _feature_names(selected_model)
    importance = top_feature_importance(
        selected_model,
        feature_names,
    )

    metadata = {
        "model_version": MODEL_VERSION,
        "trained_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "selected_model": selected_name,
        "selection_rule": (
            "Highest validation recall for high_attention, then F1, "
            "then ROC-AUC."
        ),
        "rows": int(len(feature_frame)),
        "target_distribution": {
            str(key): int(value)
            for key, value in y.value_counts().sort_index().items()
        },
        "splits": {
            "train": int(len(x_train)),
            "validation": int(len(x_val)),
            "test": int(len(x_test)),
        },
        "thresholds": ML_RISK_THRESHOLDS,
        "feature_documentation": get_feature_documentation(),
        "feature_columns": feature_columns,
        "limitations": [
            "Only 500 records are available.",
            "Target is constructed from business rules, not from "
            "historical analyst resolution labels.",
            "Metrics are useful for development comparison, not a "
            "production performance claim.",
        ],
    }

    return selected_model, results, metadata, importance


def save_artifacts(model, metrics, metadata, importance):
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, MODEL_FILE)

    METRICS_FILE.write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )

    METADATA_FILE.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    importance.to_csv(FEATURE_IMPORTANCE_FILE, index=False)


def main():
    model, metrics, metadata, importance = train_models()
    save_artifacts(model, metrics, metadata, importance)

    print("=" * 70)
    print("ML RISK MODEL TRAINING")
    print("=" * 70)
    print(f"Selected model: {metadata['selected_model']}")
    print(f"Rows: {metadata['rows']}")
    print(f"Target distribution: {metadata['target_distribution']}")
    print("\nValidation/test metrics:")
    print(json.dumps(metrics, indent=2))
    print("\nTop feature importance:")
    print(importance.to_string(index=False))
    print(f"\nSaved model: {MODEL_FILE}")
    print(f"Saved metrics: {METRICS_FILE}")
    print(f"Saved metadata: {METADATA_FILE}")


if __name__ == "__main__":
    main()
