# MLOps in Finance: Credit-Risk Model from Development to Cloud Deployment

FCU 11501 Financial Cloud Practice (金融上雲實務) · **Group 13** · Cathay theme: MLOps

## Product Goal
> Enable the credit-risk team to deploy a validated risk model from development to the cloud **within one working day**, with every score traceable, explainable, and monitored for drift.

## Board
- GitHub Projects board: https://github.com/users/chinglin-k/projects/2 (user stories US1–US10 as issues; Todo / In Progress / Done)
- Backlog export & Sprint 1–2 burndown charts: [`docs/scrum/`](docs/scrum/)

## Team Roles
| Role | Member | Responsibility |
|---|---|---|
| Product Owner | 高慶霖 (Kao Ching-Lin) | Backlog ordering, stakeholder comms, submission |
| Scrum Master | 凃苙程 | Ceremonies, board hygiene, retro notes |
| Data Engineer | 陳堃益 | Synthetic data, data layers, Athena |
| ML Engineer | 林冠宇 | Training, validation, model registry |
| Cloud / DevOps | 賴政豪 | Lambda, CI, IAM & audit trail |

## Quick Start (fresh clone reproduces everything)
```bash
pip install -r requirements.txt
make all                         # generate -> clean & layer -> train & register -> drift check
python -m pytest -q              # 5 tests
python src/local_demo.py         # local stand-in for the Lambda scorer
bash aws/deploy_learner_lab.sh   # AWS Learner Lab (us-east-1) end-to-end slice
```
In Learner Lab CloudShell (credentials come from LabRole), install with `python3 -m pip install -q numpy pandas scikit-learn`; `pip install --user` fails inside the CloudShell virtualenv.
Expected (seed 42): 10,100 raw rows → 10,000 curated rows; Logistic AUC 0.764 / KS 0.397; GBM AUC 0.741; drift ALERT on 3 features.

## Architecture (MVP slice)
```
(1) make all / CI  ->  S3 raw (read-only) -> processed -> curated (tokenized, no sensitive attrs)
(2) Athena queries curated layer
(3) train.py -> models/logistic_model.json + registry.json -> S3 models/
(4) API call -> Lambda risk-score (LabRole) -> PD + decision
(5) every score -> DynamoDB risk_score_audit; high risk -> human review
(6) monitor.py PSI > 0.25 -> retrain alert
Governance: S3 SSE + Block Public Access + versioning, CloudTrail, least privilege, human-in-the-loop
```

## Repository Layout
```
data/generate_data.py    synthetic data generator (no real PII)
src/clean.py             raw -> processed -> curated, tokenization, sensitive-attr split
src/train.py             Logistic champion + GBM challenger, AUC/KS, model registry
src/score.py             pure-Python scorer (shared by Lambda & local demo)
src/lambda_function.py   Lambda handler + DynamoDB audit
src/monitor.py           PSI drift monitoring
src/make_figures.py      report figures
aws/                     Learner Lab deploy script, Athena DDL, sample request
.github/workflows/ci.yml tests + training + AUC gate (>= 0.70)
docs/                    figures, Scrum evidence, MVP screenshots
```

## Data Dictionary (`curated/features.csv`)
| Column | Type | Description |
|---|---|---|
| customer_token | string | SHA-256(salt + customer_id), first 16 hex |
| application_month | string | YYYY-MM |
| annual_income | double | annual income (TWD); missing → median |
| employment_years | double | years employed |
| debt_ratio | double | debt-to-income; 9.99 error code → missing → median |
| credit_utilization | double | revolving utilization |
| late_payments_12m | int | late payments, last 12 months |
| inquiries_6m | int | credit inquiries, last 6 months |
| num_credit_lines | int | number of credit lines |
| loan_amount | double | requested amount (TWD) |
| loan_term_months | int | term |
| *_missing | int | missing-value flags |
| default_12m | int | target: default within 12 months |

`gender` and `age_band` live in `curated/fairness_attrs.csv` and are used **only for fairness monitoring, never as features**.

## Learner Lab Results (2026-11-04, us-east-1)
Full run in CloudShell took about 3 minutes, from package install to the Lambda response.

| Step | Result |
|---|---|
| Data | 10,100 raw rows → 10,000 curated rows |
| Training | Logistic AUC 0.7638 / KS 0.397 (champion); GBM AUC 0.7411 |
| S3 | `raw/`, `processed/`, `curated/`, `models/`; SSE-S3, Block Public Access, versioning |
| Athena | `fincloud_risk.features`: 10,000 rows, default rate 21.59% |
| Lambda `risk-score` | PD 0.7957 → `MANUAL_REVIEW_HIGH_RISK`, model version recorded |
| DynamoDB `risk_score_audit` | audit item written for the call |

Screenshots: [`docs/mvp/learnerlab/`](docs/mvp/learnerlab/) (CloudShell, S3, Lambda, DynamoDB, Athena, Pricing Calculator).

Demo video (73 s, captioned walkthrough of the actual run): [`docs/demo/11501_FinCloud_13_MLOps_Demo.mp4`](docs/demo/11501_FinCloud_13_MLOps_Demo.mp4)

## Cost Estimate (AWS Pricing Calculator, us-east-1, no free tier)
Assumed production-year volume: 1M scoring calls/month.

| Service | Assumption (per month) | USD / month |
|---|---|---|
| Lambda (x86, 128 MB) | 1M requests × 200 ms | 0.62 |
| S3 Standard | 100 GB; 100k PUT, 1M GET | 3.20 |
| DynamoDB on-demand | 5 GB; 1M writes, 100k reads | 1.89 |
| Athena | 20 queries/day × 1 GB scanned | 2.97 |
| **Total** | 12 months: **104.16**; 3 years ≈ 312.48 | **8.68** |

Estimate link: https://calculator.aws/#/estimate?id=1e824c1048f35dd28db3850e7d57fe6ced01304c  
Not included: CloudWatch, CloudTrail, KMS CMK, VPC endpoints and monthly retraining compute (production only). The Learner Lab run itself costs close to zero; always press End Lab.

## Decision Log
| # | Date | Decision | Why | Alternative |
|---|---|---|---|---|
| D1 | 10/08 | Synthetic data only | No real PII allowed; fully reproducible | Public datasets (schema mismatch) |
| D2 | 10/15 | raw / processed / curated layers | raw stays immutable for audit; de-identify at curated | single layer |
| D3 | 10/22 | Logistic = champion, GBM = challenger | Explainability (FSC AI guideline); AUC gap small | GBM only |
| D4 | 10/24 | Lambda + JSON model instead of SageMaker endpoint | Learner Lab limits; pay-per-call | SageMaker (production) |
| D5 | 10/30 | Add PSI drift monitoring (mentor feedback, issue `mentor`) | Post-deployment monitoring matters most | periodic retrain only |
| D6 | 10/30 | High risk never auto-rejected → human review | Human-centric, accountable decisions | auto-reject |

## Retrospectives
**Sprint 1 (10/08–10/21)** — Went well: data generator & data dictionary fixed early. To improve: tasks too large, burndown flat for 4 days. Action: split stories into 2–4 tasks; daily board update.

**Sprint 2 (10/22–11/04)** — Went well: CI AUC gate gives an objective quality bar. To improve: mentor feedback on 10/29 added monitoring scope mid-sprint, burndown flat for 3 days. Action: keep 15% buffer in Sprint 3; new requests go to the backlog first.

## AI Usage Statement
We used Claude (Anthropic) for code scaffolding, the synthetic-data script, document drafts, and figures. All output was reviewed, executed, and edited by team members; all reported metrics come from actual runs. All data is synthetic, no real personal data. No credentials are stored in this repository.
