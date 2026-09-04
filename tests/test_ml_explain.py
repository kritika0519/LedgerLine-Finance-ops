from src.ml.explain import risk_level_from_probability


def test_risk_level_thresholds_are_configurable():
    thresholds = {
        "LOW": 0.25,
        "MEDIUM": 0.50,
        "HIGH": 0.75,
    }

    assert risk_level_from_probability(0.10, thresholds) == "LOW"
    assert risk_level_from_probability(0.30, thresholds) == "MEDIUM"
    assert risk_level_from_probability(0.60, thresholds) == "HIGH"
    assert risk_level_from_probability(0.90, thresholds) == "CRITICAL"
