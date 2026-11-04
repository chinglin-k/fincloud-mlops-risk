import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from score import score

M = {"version": "t", "features": ["debt_ratio"], "log_features": [], "scaler_mean": [0.3], "scaler_scale": [0.1],
     "coef": [1.0], "intercept": -2.0, "thresholds": {"auto_approve_below": 0.1, "manual_review_below": 0.35}}


def test_high_risk_goes_to_human():
    assert score(M, {"debt_ratio": 0.9})["decision"] == "MANUAL_REVIEW_HIGH_RISK"


def test_low_risk_auto():
    assert score(M, {"debt_ratio": 0.1})["decision"] == "AUTO_APPROVE"
