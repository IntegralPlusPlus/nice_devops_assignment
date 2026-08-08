import json
import base64
import sys
import boto3
from pathlib import Path

FUNCTION_NAME = "s3_lister"
SCRIPT_DIR = Path(__file__).resolve().parent 
PROJECT_ROOT = SCRIPT_DIR.parent
EVENT_FILE = PROJECT_ROOT / "events" / "test-event.json"
LOG_FILE = Path("invoke.log")

payload = EVENT_FILE.read_text(encoding="utf-8")

print(f"Invoking {FUNCTION_NAME}...")
client = boto3.client("lambda")
response = client.invoke(FunctionName=FUNCTION_NAME, 
                         LogType="Tail", 
                         Payload=payload)

body = json.loads(response["Payload"].read())
logs = base64.b64decode(response["LogResult"]).decode("utf-8")

print("\nCloudWatch logs (last 4 KB):")
print(logs.rstrip())
print("------------------------------------------------")
LOG_FILE.write_text(logs, encoding="utf-8")
print(f"Logs saved to {LOG_FILE}\n")

print(json.dumps(body))

if "FunctionError" in response:
    sys.exit(f"Function error: {response['FunctionError']}")
elif body["object_count"] == 0:
    sys.exit("Bucket is empty — did BucketDeployment upload sample_files/?")

print(f"\nOK — {body['object_count']} object(s). Check your email")