import os
from types import SimpleNamespace
from unittest.mock import patch
import boto3
from moto import mock_aws
# Mocking AWS services to prevent real S3 requests and SNS email deliveries
from index import build_message, handler, get_data_from_s3

ctx = SimpleNamespace(function_name="s3_lister", aws_request_id="local-test")
BUCKET = os.environ["BUCKET_NAME"]

def test_build_message():
    list_of_files = ["a.txt (1 bytes)", "b.cpp (2 bytes)"]
    message = build_message(list_of_files, 3, ctx)

    assert "Number of files: 2" in message
    assert "Total size:      3 bytes" in message
    assert "a.txt (1 bytes)" in message and "b.cpp (2 bytes)" in message

def make_bucket_and_topic():
    s3 = boto3.client("s3")
    s3.create_bucket(Bucket=BUCKET,
                     CreateBucketConfiguration={"LocationConstraint": "eu-central-1"})
    topic = boto3.client("sns").create_topic(Name="test-topic")

    assert topic["TopicArn"] == os.environ["TOPIC_ARN"]
    return s3

@mock_aws
def test_sums_file_sizes():
    s3 = make_bucket_and_topic()
    s3.put_object(Bucket=BUCKET, Key="a.txt", Body=b"hello")            # 5 bytes
    s3.put_object(Bucket=BUCKET, Key="b.txt", Body=b"Hello to NiCE!")   # 14 bytes

    files, total = get_data_from_s3()

    assert total == 19
    assert sorted(files) == ["a.txt (5 bytes)", "b.txt (14 bytes)"]

@mock_aws
def test_handler_counts_objects():
    s3 = make_bucket_and_topic()
    s3.put_object(Bucket=BUCKET, Key="a.txt", Body="hello")
    s3.put_object(Bucket=BUCKET, Key="b.txt", Body="Hello to NiCE from BGU!")
    s3.put_object(Bucket=BUCKET, Key="c.cpp", Body="#include <iostream>")
    response = handler({}, ctx)

    assert response["object_count"] == 3

@mock_aws
def test_empty_bucket_is_not_an_error():
    make_bucket_and_topic()

    assert get_data_from_s3() == ([], 0)
    assert handler({}, ctx)["object_count"] == 0

@mock_aws
def test_pagination_returns_every_object():
    s3 = make_bucket_and_topic()
    for i in range(1005):
        s3.put_object(Bucket=BUCKET, Key=f"random{i}.txt", Body="1")

    files, total = get_data_from_s3()

    assert len(files) == 1005
    assert total == 1005

@mock_aws
def test_handler_publishes_to_sns():
    s3 = make_bucket_and_topic()
    s3.put_object(Bucket=BUCKET, Key="a.txt", Body="hello")

    with patch("index.sns.publish", return_value={"MessageId": "fake-id"}) as publish:
        handler({}, ctx)

    publish.assert_called_once()
    assert "a.txt" in publish.call_args.kwargs["Message"]
    assert publish.call_args.kwargs["TopicArn"] == os.environ["TOPIC_ARN"]