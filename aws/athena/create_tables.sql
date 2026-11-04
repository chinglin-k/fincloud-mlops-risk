CREATE DATABASE IF NOT EXISTS fincloud_risk;
CREATE EXTERNAL TABLE IF NOT EXISTS fincloud_risk.features (
  customer_token string, application_month string, annual_income double, employment_years double,
  debt_ratio double, credit_utilization double, late_payments_12m int, inquiries_6m int,
  num_credit_lines int, loan_amount double, loan_term_months int,
  annual_income_missing int, debt_ratio_missing int, default_12m int)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
LOCATION 's3://__BUCKET__/curated/features/'
TBLPROPERTIES ('skip.header.line.count'='1');
SELECT application_month, COUNT(*) AS n, ROUND(AVG(default_12m)*100,2) AS default_rate_pct
FROM fincloud_risk.features GROUP BY application_month ORDER BY application_month;
