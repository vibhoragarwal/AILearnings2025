from delta import DeltaTable
from pyspark.sql import functions as F

from DynamicPriceMarker.config.s3 import create_s3_folder, BUCKET_NAME
from DynamicPriceMarker.config.spark_config import get_market_schema, get_spark

from lambda_api.setup_env import update_environment
update_environment()


S3_BUCKET = f"s3a://{BUCKET_NAME}"

# Define S3 Paths
# Notice we use 's3a://' instead of 'os.path.join' for local folders
raw_market_alerts = f"{S3_BUCKET}/ingestion/raw_market_alerts/"
bronze_checkpoint_path = f"{S3_BUCKET}/ingestion/checkpoints/bronze/"
bronze_market_history = f"{S3_BUCKET}/ingestion/bronze_market_history/"
silver_path = f"{S3_BUCKET}/ingestion/silver_market_prices/"
silver_checkpoint = f"{S3_BUCKET}/ingestion/checkpoints/silver"

create_s3_folder(BUCKET_NAME, "ingestion/silver_market_prices/")
create_s3_folder(BUCKET_NAME, "ingestion/checkpoints/silver")
create_s3_folder(BUCKET_NAME, "ingestion/raw_market_alerts/")
create_s3_folder(BUCKET_NAME, "ingestion/checkpoints/bronze/")
create_s3_folder(BUCKET_NAME, "ingestion/bronze_market_history/")

spark = get_spark()
market_schema = get_market_schema()

# 1. Read the Raw Data
raw_data_stream = spark.readStream \
    .schema(market_schema) \
    .json(raw_market_alerts)

# check the folder every 5 seconds.
bronze_stream = raw_data_stream.writeStream \
    .format("delta") \
    .option("checkpointLocation", bronze_checkpoint_path) \
    .outputMode("append") \
    .trigger(processingTime='25 seconds') \
    .start(bronze_market_history)



if not DeltaTable.isDeltaTable(spark, silver_path):
    spark.createDataFrame([], market_schema).write.format("delta").save(silver_path)


# 3. The Upsert Function
def upsert_to_silver(batch_df, batch_id):
    print(f"processing batch {batch_id}")

    # 1. CLEANING & CONFORMING (Standardization)
    cleaned_df = batch_df \
        .filter(F.col("competitor_price") > 0) \
        .filter(F.col("item_name").isNotNull()) \
        .withColumn("item_name", F.trim(F.upper(F.col("item_name")))) \
        .withColumn("competitor_name", F.trim(F.upper(F.col("competitor_name")))) \
        .withColumn("timestamp", F.to_timestamp(F.col("timestamp")))  # Convert string to real Date type

    # --- ADDED THIS LINE ---
    # In case the same item appears twice in one batch, keep only the latest one
    # Note: This assumes your timestamp is a string/date we can sort
    deduped_df = cleaned_df.orderBy("timestamp", ascending=False) \
        .dropDuplicates(["item_name", "competitor_name"])

    # This function runs for every micro-batch
    silver_table = DeltaTable.forPath(spark, silver_path)

    silver_table.alias("target").merge(
        deduped_df.alias("source"),
        "target.item_name = source.item_name AND target.competitor_name = source.competitor_name"
    ).whenMatchedUpdate(set={
        "competitor_price": "source.competitor_price",
        "timestamp": "source.timestamp"
    }).whenNotMatchedInsertAll() \
        .execute()

    silver_df = spark.read.format("delta").load(silver_path)

    # 3. Sort by item and show the results
    print("--- Current Silver 'Master' Prices ---")
    silver_df.orderBy("item_name").show()


print(f"Starting Silver Stream reading from: {bronze_market_history}")
# 4. Start the Stream from Bronze to Silver
# We read FROM the Bronze Delta path
bronze_stream = spark.readStream.format("delta").load(bronze_market_history)

silver_query = bronze_stream.writeStream \
    .foreachBatch(upsert_to_silver) \
    .option("checkpointLocation", silver_checkpoint) \
    .start()

print(f"Streams started! Drop JSON files into {raw_market_alerts} to see the magic...")

# Keep the processes alive
spark.streams.awaitAnyTermination()
