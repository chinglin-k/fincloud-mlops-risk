"""Train a Logistic baseline (champion) and a GBM challenger, evaluate AUC/KS, append to models/registry.json.
Logistic coefficients are exported as JSON so the Lambda scorer needs no scikit-learn."""
import json, pickle, hashlib, datetime as dt
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.model_selection import train_test_split
from src.clean import FEATURES, TARGET

MODEL_FEATURES = FEATURES + ["annual_income_missing", "debt_ratio_missing"]


def ks_stat(y, p):
    fpr, tpr, _ = roc_curve(y, p)
    return float(np.max(tpr - fpr))


def prep(df):
    X = df[MODEL_FEATURES].astype(float).copy()
    X["annual_income"] = np.log(X["annual_income"])
    X["loan_amount"] = np.log(X["loan_amount"])
    return X


def train(curated="data/curated/features.csv", out="models", seed=42):
    df = pd.read_csv(curated)
    X, y = prep(df), df[TARGET].values
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, stratify=y, random_state=seed)
    sc = StandardScaler().fit(Xtr)
    lr = LogisticRegression(max_iter=1000).fit(sc.transform(Xtr), ytr)
    p_lr = lr.predict_proba(sc.transform(Xte))[:, 1]
    gbm = HistGradientBoostingClassifier(max_depth=4, learning_rate=0.05, max_iter=300, random_state=seed).fit(Xtr, ytr)
    p_gb = gbm.predict_proba(Xte)[:, 1]
    res = {
        "logistic": {"auc": round(roc_auc_score(yte, p_lr), 4), "ks": round(ks_stat(yte, p_lr), 4)},
        "gbm": {"auc": round(roc_auc_score(yte, p_gb), 4), "ks": round(ks_stat(yte, p_gb), 4)},
        "n_train": int(len(ytr)), "n_test": int(len(yte)),
    }
    Path(out).mkdir(exist_ok=True)
    version = dt.datetime.now(dt.timezone.utc).strftime("v%Y%m%d%H%M%S")
    artifact = {
        "version": version, "features": MODEL_FEATURES, "log_features": ["annual_income", "loan_amount"],
        "scaler_mean": sc.mean_.tolist(), "scaler_scale": sc.scale_.tolist(),
        "coef": lr.coef_[0].tolist(), "intercept": float(lr.intercept_[0]),
        "thresholds": {"auto_approve_below": 0.10, "manual_review_below": 0.35},
    }
    blob = json.dumps(artifact, indent=2)
    Path(out, "logistic_model.json").write_text(blob)
    with open(Path(out, "gbm.pkl"), "wb") as f:
        pickle.dump(gbm, f)
    reg_path = Path(out, "registry.json")
    reg = json.loads(reg_path.read_text()) if reg_path.exists() else []
    champion = "logistic"  # decision D3: explainability first; GBM is challenger
    reg.append({"version": version, "champion": champion, "metrics": res,
                "sha256": hashlib.sha256(blob.encode()).hexdigest()[:12],
                "status": "staging" if res["logistic"]["auc"] >= 0.70 else "rejected"})
    reg_path.write_text(json.dumps(reg, indent=2))
    Path("reports").mkdir(exist_ok=True)
    Path("reports/metrics.json").write_text(json.dumps(res, indent=2))
    np.save("reports/test_scores.npy", np.vstack([yte, p_lr, p_gb]))
    print(json.dumps(res))
    return res


if __name__ == "__main__":
    train()
