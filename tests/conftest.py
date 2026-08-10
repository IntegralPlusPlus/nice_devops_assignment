import os
import sys
from pathlib import Path

# For import lambda function in tests
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "lambda"))

os.environ.setdefault("AWS_DEFAULT_REGION", "eu-central-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("BUCKET_NAME", "test-bucket")
os.environ.setdefault("TOPIC_ARN", "arn:aws:sns:eu-central-1:123456789012:test-topic")