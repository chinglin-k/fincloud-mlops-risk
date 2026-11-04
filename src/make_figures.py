"""Build figures for the proposal & slides (charts keep Chinese labels for the report)."""
import json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve
from matplotlib import font_manager as fm
for _f in ["/usr/share/fonts/truetype/arphic/ukai.ttc", "C:/Windows/Fonts/kaiu.ttf"]:
    try:
        fm.fontManager.addfont(_f)
    except (FileNotFoundError, RuntimeError):
        pass
plt.rcParams["font.family"] = ["Times New Roman", "Liberation Serif", "DFKai-SB", "AR PL UKai TW", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False
C1, C2, C3 = "#1f4e79", "#e8a33d", "#4a8c5c"
out = "docs/img/"
cur = pd.read_csv("data/curated/features.csv"); n = len(cur)

def save(fig, name):
    fig.tight_layout(); fig.savefig(out + name, dpi=160); plt.close(fig)

# insight 1
cur["dr_bin"] = pd.cut(cur["debt_ratio"], [0, .1, .2, .3, .4, .5, 1.5], labels=["<10%", "10-20%", "20-30%", "30-40%", "40-50%", ">50%"])
g = cur.groupby("dr_bin", observed=True)["default_12m"].mean() * 100
fig, ax = plt.subplots(figsize=(6, 3.4)); ax.bar(g.index.astype(str), g.values, color=C1)
ax.set_title(f"圖1 負債比分組之 12 個月違約率（n={n:,}）"); ax.set_ylabel("違約率（%）"); ax.set_xlabel("負債比")
for i, v in enumerate(g.values): ax.text(i, v + .5, f"{v:.0f}", ha="center", fontsize=8)
save(fig, "fig1_debt_ratio.png")
# insight 2
g2 = cur.assign(l=cur["late_payments_12m"].clip(upper=3)).groupby("l")["default_12m"].agg(["mean", "size"])
fig, ax = plt.subplots(figsize=(6, 3.4)); ax.bar(["0", "1", "2", "3+"], g2["mean"] * 100, color=C2)
ax.set_title(f"圖2 近 12 個月遲繳次數與違約率（n={n:,}）"); ax.set_ylabel("違約率（%）"); ax.set_xlabel("遲繳次數")
for i, (m, s) in enumerate(g2.values): ax.text(i, m * 100 + .5, f"n={int(s)}", ha="center", fontsize=8)
save(fig, "fig2_late_payments.png")
# insight 3: drift
d = json.load(open("reports/drift.json"))["psi"]
fig, ax = plt.subplots(figsize=(6, 3.4)); ks = list(d); vs = [d[k] for k in ks]
ax.barh(ks, vs, color=[("#c0392b" if v > .25 else C3) for v in vs]); ax.axvline(.25, ls="--", c="gray"); ax.axvline(.1, ls=":", c="gray")
ax.set_title("圖3 2026Q1 模擬資料 vs 訓練資料 PSI（n=3,000 vs 10,000）"); ax.set_xlabel("PSI（>0.25 告警）")
save(fig, "fig3_drift_psi.png")
# ROC
y, plr, pgb = np.load("reports/test_scores.npy"); m = json.load(open("reports/metrics.json"))
fig, ax = plt.subplots(figsize=(4.6, 3.8))
for p, lab, c in [(plr, f"Logistic AUC={m['logistic']['auc']}", C1), (pgb, f"GBM AUC={m['gbm']['auc']}", C2)]:
    f, t, _ = roc_curve(y, p); ax.plot(f, t, label=lab, c=c)
ax.plot([0, 1], [0, 1], "--", c="gray"); ax.legend(); ax.set_xlabel("偽陽性率"); ax.set_ylabel("真陽性率")
ax.set_title(f"圖4 測試集 ROC（n={len(y):,}）"); save(fig, "fig4_roc.png")
# burndown
for sp, total, actual, note in [
    (1, 18, [18, 18, 16, 16, 13, 11, 11, 8, 5, 3, 0], "Sprint 1（10/08–10/21）"),
    (2, 26, [26, 26, 24, 23, 23, 23, 19, 14, 10, 5, 0], "Sprint 2（10/22–11/04）")]:
    fig, ax = plt.subplots(figsize=(6, 3.2)); days = range(len(actual))
    ax.plot(days, np.linspace(total, 0, len(actual)), "--", c="gray", label="理想線")
    ax.plot(days, actual, "-o", c=C1, label="實際剩餘點數")
    ax.set_title(f"Sprint {sp} 燃盡圖 {note}"); ax.set_xlabel("工作天"); ax.set_ylabel("剩餘故事點"); ax.legend()
    if sp == 2: ax.annotate("10/29 業師回饋\n新增監控需求", (5, 23), (6.3, 25), arrowprops=dict(arrowstyle="->"), fontsize=8)
    save(fig, f"burndown_sprint{sp}.png")
print("figures ok")
