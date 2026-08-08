import os
import boto3
import logging
import json
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

s3 = boto3.client("s3")
sns = boto3.client("sns")

BUCKET_NAME = os.environ["BUCKET_NAME"]
TOPIC_ARN = os.environ["TOPIC_ARN"]

def get_data_from_s3() -> list:
    list_files = []
    
    panginator = s3.get_paginator('list_objects_v2').paginate(Bucket=BUCKET_NAME)
    size_sum = 0
        
    for page in panginator:
        for obj in page.get("Contents", []):
            size_sum += obj["Size"]
            list_files.append(f"{obj['Key']} ({obj['Size']} bytes)")

    return (list_files, size_sum)

def build_message(list_files: list, size_sum: int, context) -> str:
    jerusalem_time = datetime.now(ZoneInfo("Asia/Jerusalem"))
    time_now = jerusalem_time.strftime("%Y-%m-%d %H:%M:%S %Z%z")

    response = ("S3 Bucket Listing Report\n"
                f"Bucket name: {BUCKET_NAME}\n"
                f"Time: {time_now}\n"
                f"Number of files: {len(list_files)}\n"
                f"Total size: {size_sum} bytes\n"
                f"Function:   {context.function_name}\n"
                f"Request ID: {context.aws_request_id}\n"
                f"Files: \n")

    for obj in list_files:
        response += obj + '\n'

    return response

def handler(event, context):
    logger.info("Lambda function called")

    list_files_s3, size_sum = get_data_from_s3()
    logger.info("Found %d object(s) in bucket %s", len(list_files_s3), BUCKET_NAME)

    response = build_message(list_files_s3, size_sum, context)

    published = sns.publish(TopicArn=TOPIC_ARN, 
                            Subject = f"S3 notification from {BUCKET_NAME}"[:100], # added :100 because of 
                            Message=response)
    
    logger.info("Published to SNS, MessageId=%s", published["MessageId"])

    return {
        "bucket": BUCKET_NAME,
        "object_count": len(list_files_s3),
        "objects": list_files_s3,
        "sns_message_id": published["MessageId"],
    }