"""Model monitoring: feature drift via PSI; PSI > 0.25 raises a retrain alert."""
import json, sys
import numpy as np
import pandas as pd
from src.clean import FEATURES


def psi(expected, actual, bins=10):
    qs = np.unique(np.quantile(expected, np.linspace(0, 1, bins + 1)))
    e = np.histogram(expected, qs)[0] / len(expected) + 1e-6
    a = np.histogram(np.clip(actual, qs[0], qs[-1]), qs)[0] / len(actual) + 1e-6
    return float(np.sum((a - e) * np.log(a / e)))


def report(base_csv, new_csv):
    b, n = pd.read_csv(base_csv), pd.read_csv(new_csv)
    out = {f: round(psi(b[f].values, n[f].values), 4) for f in FEATURES}
    status = {k: ("ALERT" if v > 0.25 else "WATCH" if v > 0.10 else "OK") for k, v in out.items()}
    res = {"psi": out, "status": status, "retrain": any(s == "ALERT" for s in status.values())}
    print(json.dumps(res, indent=2))
    return res


if __name__ == "__main__":
    r = report(*sys.argv[1:3])
    open("reports/drift.json", "w").write(json.dumps(r, indent=2))
