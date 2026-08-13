import boto3
import json

# MODEL_ID = "INSERT INFERENCE PROFILE ARN HERE"
GUARDRAIL_ID = "xnlg9ddiz850"
MODEL_ID = "us.anthropic.claude-sonnet-4-6"

bedrock = boto3.client(service_name="bedrock-runtime", region_name="us-east-1")


response = bedrock.converse(
    modelId=MODEL_ID,
    messages=[{"role": "user", "content": [{"text": "Are dogs better than cats?"}]}],
    guardrailConfig={
        "guardrailIdentifier": GUARDRAIL_ID,
        "guardrailVersion": "DRAFT",
        "trace": "enabled",
    },
)

print(json.dumps(response, indent=4, sort_keys=True))
