"""Local stand-in for the Lambda call: score sample applications with models/logistic_model.json."""
import json, sys
sys.path.insert(0, "src")
from score import score
m = json.load(open("models/logistic_model.json"))
for path in ["aws/sample_request.json"]:
    print(json.dumps(score(m, json.load(open(path))), ensure_ascii=False))
low = {"annual_income": 1500000, "employment_years": 12, "debt_ratio": 0.08, "credit_utilization": 0.1,
       "late_payments_12m": 0, "inquiries_6m": 0, "num_credit_lines": 5, "loan_amount": 200000, "loan_term_months": 24}
print(json.dumps(score(m, low), ensure_ascii=False))
