import os

from delta import configure_spark_with_delta_pip
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, DoubleType

load_dotenv()

ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# hadoop-aws allows Spark to use 's3a://'
# aws-java-sdk-bundle contains the actual AWS communication logic
packages = [
    "org.apache.hadoop:hadoop-aws:3.3.4",
    "com.amazonaws:aws-java-sdk-bundle:1.12.262",
    "org.apache.spark:spark-hadoop-cloud_2.12:3.5.0"  # Adds extra cloud glue
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


def get_spark():
    return spark


def get_market_schema():
    return market_schema
