"""Pure-Python scorer (no sklearn), shared by local demo and AWS Lambda."""
import math


def score(model: dict, app: dict) -> dict:
    z = model["intercept"]
    for i, f in enumerate(model["features"]):
        v = float(app.get(f, 0) or 0)
        if f in model["log_features"]:
            v = math.log(max(v, 1.0))
        z += model["coef"][i] * (v - model["scaler_mean"][i]) / model["scaler_scale"][i]
    pd_ = 1 / (1 + math.exp(-z))
    t = model["thresholds"]
    if pd_ < t["auto_approve_below"]:
        decision = "AUTO_APPROVE"
    elif pd_ < t["manual_review_below"]:
        decision = "MANUAL_REVIEW"
    else:
        decision = "MANUAL_REVIEW_HIGH_RISK"  # high risk always goes to a human; the model never auto-rejects
    contrib = {f: round(model["coef"][i], 3) for i, f in enumerate(model["features"])}
    top = sorted(contrib, key=lambda k: -abs(contrib[k]))[:3]
    return {"model_version": model["version"], "pd": round(pd_, 4), "decision": decision, "top_factors": top}
