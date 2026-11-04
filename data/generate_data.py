"""Generate SYNTHETIC credit-application data. No real personal data.

Usage: python data/generate_data.py --n 10000 --seed 42 --out data/raw/applications.csv
- customer_id is a random UUID, not linked to any real person
- gender / age_band are kept for fairness monitoring only, never used as model features
- Quality issues (missing values, invalid values, duplicates) are injected on purpose
"""
import argparse, uuid
from pathlib import Path
import numpy as np
import pandas as pd


def generate(n: int = 10000, seed: int = 42, drift: float = 0.0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    income = rng.lognormal(mean=13.3 - drift * 0.15, sigma=0.45, size=n).round(0)  # annual income (TWD)
    employment_years = np.clip(rng.gamma(2.0, 3.0, n), 0, 40).round(1)
    debt_ratio = np.clip(rng.beta(2, 5, n) + drift * 0.08, 0, 1.5).round(3)
    credit_util = np.clip(rng.beta(2, 3, n) + drift * 0.10, 0, 1.2).round(3)
    late_12m = rng.poisson(0.4 + drift * 0.5, n)
    inquiries_6m = rng.poisson(1.2, n)
    num_lines = rng.integers(1, 15, n)
    loan_amount = (rng.lognormal(12.3, 0.6, n) / 1000).round(0) * 1000
    loan_term = rng.choice([12, 24, 36, 60, 84], n, p=[0.1, 0.2, 0.35, 0.25, 0.1])
    gender = rng.choice(["F", "M"], n)
    age_band = rng.choice(["20-29", "30-39", "40-49", "50-59", "60+"], n, p=[0.2, 0.3, 0.25, 0.15, 0.1])

    z = (-4.2 + 3.4 * debt_ratio + 2.8 * credit_util + 0.85 * late_12m + 0.12 * inquiries_6m
         - 0.6 * (np.log(income) - 13.3) - 0.04 * employment_years
         + 0.25 * (loan_amount / income) + 0.004 * loan_term + rng.normal(0, 0.3, n))
    default = (rng.random(n) < 1 / (1 + np.exp(-z))).astype(int)

    df = pd.DataFrame({
        "customer_id": [str(uuid.UUID(int=int(rng.integers(0, 2**63)) << 64 | i)) for i in range(n)],
        "application_month": rng.choice(pd.period_range("2025-01", "2025-12", freq="M").astype(str), n),
        "annual_income": income, "employment_years": employment_years, "debt_ratio": debt_ratio,
        "credit_utilization": credit_util, "late_payments_12m": late_12m, "inquiries_6m": inquiries_6m,
        "num_credit_lines": num_lines, "loan_amount": loan_amount, "loan_term_months": loan_term,
        "gender": gender, "age_band": age_band, "default_12m": default,
    })
    # inject data-quality issues
    miss = rng.random(n) < 0.03
    df.loc[miss, "annual_income"] = np.nan
    out = rng.random(n) < 0.005
    df.loc[out, "debt_ratio"] = 9.99  # system default error value
    dup = df.sample(frac=0.01, random_state=seed)
    return pd.concat([df, dup], ignore_index=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--drift", type=float, default=0.0, help="strength of simulated distribution drift")
    ap.add_argument("--out", default="data/raw/applications.csv")
    a = ap.parse_args()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    d = generate(a.n, a.seed, a.drift)
    d.to_csv(a.out, index=False)
    print(f"wrote {len(d)} rows -> {a.out}")
