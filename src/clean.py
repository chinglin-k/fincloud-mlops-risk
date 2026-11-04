"""raw -> processed -> curated. processed: dedupe & fix; curated: drop sensitive attrs, tokenize customer id."""
import hashlib, json, os, sys
from pathlib import Path
import pandas as pd

FEATURES = ["annual_income", "employment_years", "debt_ratio", "credit_utilization",
            "late_payments_12m", "inquiries_6m", "num_credit_lines", "loan_amount", "loan_term_months"]
SENSITIVE = ["gender", "age_band"]  # fairness monitoring only, never model features
TARGET = "default_12m"


def quality_report(df: pd.DataFrame) -> dict:
    return {
        "rows": int(len(df)),
        "duplicates": int(df.duplicated().sum()),
        "missing_income": int(df["annual_income"].isna().sum()),
        "invalid_debt_ratio": int((df["debt_ratio"] > 1.5).sum()),
        "default_rate": round(float(df[TARGET].mean()), 4),
    }


def to_processed(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.drop_duplicates().copy()
    df.loc[df["debt_ratio"] > 1.5, "debt_ratio"] = pd.NA  # 9.99 is a system error value -> treat as missing
    for c in ["annual_income", "debt_ratio"]:
        df[c + "_missing"] = df[c].isna().astype(int)
        df[c] = df[c].fillna(df[c].median())
    return df


def tokenize(cid: str, salt: str) -> str:
    return hashlib.sha256((salt + cid).encode()).hexdigest()[:16]


def to_curated(proc: pd.DataFrame, salt: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    salt = salt or os.environ.get("TOKEN_SALT", "demo-salt-change-me")
    df = proc.copy()
    df["customer_token"] = df["customer_id"].map(lambda x: tokenize(x, salt))
    fairness = df[["customer_token"] + SENSITIVE]
    cols = ["customer_token", "application_month"] + FEATURES + ["annual_income_missing", "debt_ratio_missing", TARGET]
    return df[cols], fairness


def main(raw_path="data/raw/applications.csv", base="data"):
    raw = pd.read_csv(raw_path)
    q = quality_report(raw)
    proc = to_processed(raw)
    cur, fair = to_curated(proc)
    for layer, d in [("processed", proc), ("curated", cur)]:
        Path(f"{base}/{layer}").mkdir(parents=True, exist_ok=True)
    proc.to_csv(f"{base}/processed/applications.csv", index=False)
    cur.to_csv(f"{base}/curated/features.csv", index=False)
    fair.to_csv(f"{base}/curated/fairness_attrs.csv", index=False)
    Path("reports").mkdir(exist_ok=True)
    q["rows_after_clean"] = int(len(cur))
    Path("reports/data_quality.json").write_text(json.dumps(q, indent=2))
    print(json.dumps(q, ensure_ascii=False))


if __name__ == "__main__":
    main(*sys.argv[1:])
