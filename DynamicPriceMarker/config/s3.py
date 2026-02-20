import os

import boto3
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---

BUCKET_NAME = "va-databricks-learn-bronze"

# The prefix (folder) inside your bucket
RAW_MARKET_ALERTS_PREFIX = "ingestion/raw_market_alerts"


ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

if not ACCESS_KEY:
    raise ValueError("AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be set")
print(f"Access key: {ACCESS_KEY}")

# Initialize S3 Client
s3_client = boto3.client(
    's3',
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY
)


def get_s3_client():
    return s3_client


def create_s3_folder(bucket, folder_name):
    # In S3, a folder is just an empty object ending with '/'
    if not folder_name.endswith('/'):
        folder_name += '/'
    s3_client.put_object(Bucket=bucket, Key=folder_name)
    print(f"Created prefix: {folder_name} in {bucket}")
