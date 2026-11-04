import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from data.generate_data import generate
from src.clean import to_processed, to_curated, SENSITIVE
from src.monitor import psi
import numpy as np


def test_no_sensitive_in_curated():
    cur, fair = to_curated(to_processed(generate(500, 1)))
    assert not set(SENSITIVE) & set(cur.columns)
    assert "customer_id" not in cur.columns


def test_cleaning_fixes_quality():
    proc = to_processed(generate(2000, 2))
    assert proc.duplicated().sum() == 0
    assert proc["annual_income"].isna().sum() == 0
    assert proc["debt_ratio"].max() <= 1.5


def test_psi_detects_drift():
    rng = np.random.default_rng(0)
    a = rng.normal(0, 1, 5000)
    assert psi(a, rng.normal(0, 1, 5000)) < 0.1
    assert psi(a, rng.normal(1, 1, 5000)) > 0.25
