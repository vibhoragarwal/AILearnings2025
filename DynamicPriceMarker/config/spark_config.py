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
# 1. Setup the Builder with Small File Optimizations
# optimizeWrite.enabled small file +Delta 'Auto-Optimize' (Reduces fragmentation during write)
# autoCompact.enabled - small file
# output committe : # 2. Prevent the "Rename" bottleneck in S3 (Critical for speed)
#     # S3 isn't a real filesystem; renames are copy+delete. This bypasses that.
# num of partions 4 : # 3. Increase partition size to avoid "Tiny Partition" writes
#     # Default is 200; for local[*] or small data, lowering this prevents 200 tiny files
# s3 conn: # 4. S3 Performance Tuning (Speed up metadata & listing)
"""
Configuration,What it does,Impact
Optimize Write,Coalesces small chunks into larger files before writing to S3.,"Fewer files, faster RAG indexing."
Auto Compact,"After a write, it checks if there are too many small files and merges them.",Maintains healthy table state automatically.
Committer v2,"Changes how Spark ""commits"" files to S3 by reducing metadata operations.","Drastically reduces the ""falling behind"" warning."
Shuffle Partitions,"If you have 1MB of data, Spark normally splits it into 200 files. Changing this to 4 creates 4 files.","Prevents ""The Small File Problem"" at the source."
"""
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
    .config("spark.sql.warehouse.dir", "spark-warehouse") \
    .config("spark.databricks.delta.optimizeWrite.enabled", "true") \
    .config("spark.databricks.delta.autoCompact.enabled", "true") \
    .config("spark.hadoop.mapreduce.fileoutputcommitter.algorithm.version", "2") \
    .config("spark.hadoop.fs.s3a.committer.name", "directory") \
    .config("spark.hadoop.fs.s3a.committer.staging.conflict-mode", "append") \
    .config("spark.sql.shuffle.partitions", "4") \
    .config("spark.hadoop.fs.s3a.connection.maximum", "100") \
    .config("spark.hadoop.fs.s3a.fast.upload", "true")

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
