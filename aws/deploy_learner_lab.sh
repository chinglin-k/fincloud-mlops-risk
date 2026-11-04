#!/usr/bin/env bash
# Learner Lab (us-east-1) end-to-end slice: S3 (private, encrypted) -> Athena -> Lambda scoring -> DynamoDB audit
# Prereq: Start Lab, then either open CloudShell (uses LabRole, no keys needed) or paste AWS CLI
#         credentials into ~/.aws/credentials locally (NEVER commit them).
# In CloudShell run `python3 -m pip install -q numpy pandas scikit-learn && make all` first;
# `pip install --user` fails inside the CloudShell virtualenv.
set -euo pipefail
REGION=us-east-1
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
BUCKET=fincloud-mlops-risk-${ACCOUNT}
ROLE_ARN=arn:aws:iam::${ACCOUNT}:role/LabRole

# (1) private, encrypted, versioned S3 bucket
aws s3api create-bucket --bucket "$BUCKET" --region $REGION || true
aws s3api put-public-access-block --bucket "$BUCKET" --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-encryption --bucket "$BUCKET" --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api put-bucket-versioning --bucket "$BUCKET" --versioning-configuration Status=Enabled

# (2) layered upload: raw (read-only) -> processed -> curated; model artifacts
aws s3 cp data/raw/applications.csv          s3://$BUCKET/raw/applications/applications.csv
aws s3 cp data/processed/applications.csv    s3://$BUCKET/processed/applications/applications.csv
aws s3 cp data/curated/features.csv          s3://$BUCKET/curated/features/features.csv
aws s3 cp models/logistic_model.json         s3://$BUCKET/models/logistic_model.json
aws s3 cp models/registry.json               s3://$BUCKET/models/registry.json

# (3) Athena database, table, query
aws s3 mb s3://$BUCKET-athena-results --region $REGION || true
sed "s/__BUCKET__/$BUCKET/g" aws/athena/create_tables.sql > /tmp/ddl.sql
while IFS= read -r -d ';' q; do
  [ -z "$(echo "$q" | tr -d '[:space:]')" ] && continue
  aws athena start-query-execution --query-string "$q" --result-configuration OutputLocation=s3://$BUCKET-athena-results/ --region $REGION
  sleep 3
done < /tmp/ddl.sql

# (4) DynamoDB audit table (every score is logged)
aws dynamodb create-table --table-name risk_score_audit --attribute-definitions AttributeName=request_id,AttributeType=S \
  --key-schema AttributeName=request_id,KeyType=HASH --billing-mode PAY_PER_REQUEST --region $REGION || true

# (5) Lambda scoring service (LabRole)
rm -f /tmp/fn.zip && (cd src && zip -q /tmp/fn.zip lambda_function.py score.py)
aws lambda create-function --function-name risk-score --runtime python3.12 --handler lambda_function.handler \
  --role "$ROLE_ARN" --zip-file fileb:///tmp/fn.zip --timeout 10 --region $REGION \
  --environment "Variables={MODEL_BUCKET=$BUCKET,AUDIT_TABLE=risk_score_audit}" || \
aws lambda update-function-code --function-name risk-score --zip-file fileb:///tmp/fn.zip --region $REGION
sleep 5
aws lambda invoke --function-name risk-score --cli-binary-format raw-in-base64-out \
  --payload file://aws/sample_request.json /tmp/out.json --region $REGION && cat /tmp/out.json
