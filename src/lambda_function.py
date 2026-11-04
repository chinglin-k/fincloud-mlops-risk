"""AWS Lambda: API/S3 trigger -> load model JSON from S3 -> return PD & decision, write audit record to DynamoDB."""
import json, os, time, uuid
import boto3
from score import score

s3 = boto3.client("s3")
ddb = boto3.resource("dynamodb")
_MODEL = None


def _model():
    global _MODEL
    if _MODEL is None:
        obj = s3.get_object(Bucket=os.environ["MODEL_BUCKET"], Key=os.environ.get("MODEL_KEY", "models/logistic_model.json"))
        _MODEL = json.loads(obj["Body"].read())
    return _MODEL


def handler(event, context):
    app = json.loads(event["body"]) if "body" in event else event
    result = score(_model(), app)
    item = {"request_id": str(uuid.uuid4()), "ts": int(time.time()), **result,
            "pd": str(result["pd"]), "top_factors": ",".join(result["top_factors"])}
    ddb.Table(os.environ.get("AUDIT_TABLE", "risk_score_audit")).put_item(Item=item)
    return {"statusCode": 200, "body": json.dumps(result)}
