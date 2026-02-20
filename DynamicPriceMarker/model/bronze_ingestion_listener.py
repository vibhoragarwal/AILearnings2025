from pyspark.sql.types import StructType, StructField, StringType, DoubleType

from pyspark.sql import SparkSession
from delta import configure_spark_with_delta_pip
import os
import boto3

BUCKET_NAME = "va-databricks-learn-bronze"
S3_BUCKET = f"s3a://{BUCKET_NAME}"
from dotenv import load_dotenv

# Load the variables from .env into the system environment
load_dotenv()

ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

if not ACCESS_KEY:
    raise ValueError("AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be set")
print(f"Access key: {ACCESS_KEY}")


# Define S3 Paths
# Notice we use 's3a://' instead of 'os.path.join' for local folders
input_path      = f"{S3_BUCKET}/ingestion/raw_market_alerts/"
checkpoint_path = f"{S3_BUCKET}/ingestion/checkpoints/bronze/"
delta_path      = f"{S3_BUCKET}/ingestion/bronze_market_history/"


s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY")
)

# Initialize the S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY")
)

def create_s3_folder(bucket, folder_name):
    # In S3, a folder is just an empty object ending with '/'
    if not folder_name.endswith('/'):
        folder_name += '/'
    s3_client.put_object(Bucket=bucket, Key=folder_name)
    print(f"Created prefix: {folder_name} in {bucket}")

# Usage
create_s3_folder(BUCKET_NAME, "ingestion/raw_market_alerts/")
create_s3_folder(BUCKET_NAME, "ingestion/checkpoints/bronze/")
create_s3_folder(BUCKET_NAME, "ingestion/bronze_market_history/")

#
# BASE_FOLDER = "../ingestion"
#
#
# # 2. Define Paths
# input_path = os.path.join(BASE_FOLDER, "raw_market_alerts")
# checkpoint_path = os.path.join(BASE_FOLDER, "checkpoints", "bronze")
# delta_path = os.path.join(BASE_FOLDER, "bronze_market_history")

# Create folders if they don't exist
# for p in [input_path, checkpoint_path, delta_path]:
#     os.makedirs(p, exist_ok=True)


# hadoop-aws allows Spark to use 's3a://'
# aws-java-sdk-bundle contains the actual AWS communication logic
packages = [
    "org.apache.hadoop:hadoop-aws:3.3.4",
    "com.amazonaws:aws-java-sdk-bundle:1.12.262",
    "org.apache.spark:spark-hadoop-cloud_2.12:3.5.0" # Adds extra cloud glue
]

# 1. Setup the Builder
builder = SparkSession.builder \
    .appName("StableDelta") \
    .master("local[*]") \
    .config("spark.hadoop.fs.s3a.access.key", ACCESS_KEY) \
    .config("spark.hadoop.fs.s3a.secret.key", SECRET_KEY) \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.jars.packages", ",".join(packages)) \
    .config("spark.sql.warehouse.dir", "spark-warehouse")


# Define the schema for incoming market alerts
market_schema = StructType([
    StructField("item_name", StringType(), False),
    StructField("competitor_name", StringType(), False),
    StructField("competitor_price", DoubleType(), False),
    StructField("timestamp", StringType(), False)
])
spark = configure_spark_with_delta_pip(builder, extra_packages=packages).getOrCreate()
# 1. Read the Stream (Bronze)
raw_stream = spark.readStream \
    .schema(market_schema) \
    .json(input_path)

# 2. Write to the Bronze Delta Table
# If your stream processes 10 files and then your Databricks cluster restarts,
# Spark looks at the checkpoint, sees it already finished those 10, and starts exactly at file #11.
# No data is lost, and no data is duplicated.

# In the Bronze layer, we never want to overwrite. We want a "History" of every alert ever received.
# This just keeps adding new rows to the bottom of the table.

# check the folder every 5 seconds.
query = raw_stream.writeStream \
    .format("delta") \
    .option("checkpointLocation",checkpoint_path) \
    .outputMode("append") \
    .trigger(processingTime='5 seconds') \
    .start(delta_path)


print(f"Stream started! Drop JSON files into {input_path} to see the magic...")

# Keep the process alive
query.awaitTermination()