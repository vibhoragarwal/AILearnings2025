from delta import DeltaTable
from pyspark.sql import functions as F

from foundation.utils.featurebroker import FeatureBroker
from lambda_api.model.init_structures import init_table_structures
from lambda_api.model.model_config import get_spark, get_market_schema

from lambda_api.setup_env import update_environment
update_environment()

spark = get_spark()
market_schema = get_market_schema()
init_table_structures(spark, market_schema)



if FeatureBroker.DataBricks:
    print("Running in Databricks: Using Auto Loader (cloudFiles)")
    raw_data_stream = spark.readStream \
        .format("cloudFiles") \
        .option("cloudFiles.format", "json") \
        .option("cloudFiles.schemaLocation", FeatureBroker.bronze_checkpoint_path) \
        .schema(market_schema) \
        .load(FeatureBroker.raw_market_alerts_path)
else:
    print("Running Locally: Using standard JSON reader")
    raw_data_stream = spark.readStream \
        .format("json") \
        .schema(market_schema) \
        .load(FeatureBroker.raw_market_alerts_path)

# check the folder every 5 seconds.
bronze_stream = raw_data_stream.writeStream \
    .format("delta") \
    .option("checkpointLocation", FeatureBroker.bronze_checkpoint_path) \
    .outputMode("append") \
    .trigger(processingTime='5 seconds') \
    .start(FeatureBroker.bronze_market_history_path)



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
    silver_table = DeltaTable.forPath(spark, FeatureBroker.silver_market_prices_path)

    silver_table.alias("target").merge(
        deduped_df.alias("source"),
        "target.item_name = source.item_name AND target.competitor_name = source.competitor_name"
    ).whenMatchedUpdate(set={
        "competitor_price": "source.competitor_price",
        "timestamp": "source.timestamp"
    }).whenNotMatchedInsertAll() \
        .execute()

    silver_df = spark.read.format("delta").load(FeatureBroker.silver_market_prices_path)

    # 3. Sort by item and show the results
    print("--- Current Silver 'Master' Prices ---")
    silver_df.orderBy("item_name").show()


print(f"Starting Silver Stream reading from: {FeatureBroker.bronze_market_history_path}")
# 4. Start the Stream from Bronze to Silver
# We read FROM the Bronze Delta path
bronze_reader_stream = spark.readStream.format("delta").load(FeatureBroker.bronze_market_history_path)

silver_query = bronze_reader_stream.writeStream \
    .foreachBatch(upsert_to_silver) \
    .option("checkpointLocation", FeatureBroker.silver_checkpoint_path) \
    .start()

print(f"Streams started! Drop JSON files into {FeatureBroker.raw_market_alerts_path} to see the magic...")

# Keep the processes alive
spark.streams.awaitAnyTermination()
