from DynamicPriceMarker.config.s3 import create_s3_folder, BUCKET_NAME
from DynamicPriceMarker.config.spark_config import get_spark, get_market_schema

S3_BUCKET = f"s3a://{BUCKET_NAME}"

# Define S3 Paths
# Notice we use 's3a://' instead of 'os.path.join' for local folders
input_path = f"{S3_BUCKET}/ingestion/raw_market_alerts/"
bronze_checkpoint_path = f"{S3_BUCKET}/ingestion/checkpoints/bronze/"
bronze_market_history = f"{S3_BUCKET}/ingestion/bronze_market_history/"

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


# 1. Read the Stream (Bronze)
raw_stream = get_spark().readStream \
    .schema(get_market_schema()) \
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
    .option("checkpointLocation", bronze_checkpoint_path) \
    .outputMode("append") \
    .trigger(processingTime='25 seconds') \
    .start(bronze_market_history)

print(f"Stream started! Drop JSON files into {input_path} to see the magic...")

# Keep the process alive
query.awaitTermination()
