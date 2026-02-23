from delta.tables import DeltaTable
from pyspark.sql import functions as F

from DynamicPriceMarker.config.s3 import BUCKET_NAME, create_s3_folder
from DynamicPriceMarker.config.utils import get_spark, get_market_schema

#
#
# BASE_FOLDER = "../ingestion"
#
# # 1. Define Silver Path
# bronze_path = os.path.join(BASE_FOLDER, "bronze_market_history")
# silver_path = os.path.join(BASE_FOLDER, "silver_market_prices")
# silver_checkpoint = os.path.join(BASE_FOLDER, "checkpoints", "silver")
#
# # Create folders if they don't exist
# for p in [silver_path, silver_checkpoint]:
#     os.makedirs(p, exist_ok=True)


S3_BUCKET = f"s3a://{BUCKET_NAME}"

silver_path = f"{S3_BUCKET}/ingestion/silver_market_prices/"
silver_checkpoint = f"{S3_BUCKET}/ingestion/checkpoints/silver"

# Usage
create_s3_folder(BUCKET_NAME, "ingestion/silver_market_prices/")
create_s3_folder(BUCKET_NAME, "ingestion/checkpoints/silver")

# Define S3 Paths
# Notice we use 's3a://' instead of 'os.path.join' for local folders

# 2. Create the Silver Table if it doesn't exist
# We need an empty table to "Merge" into the first time
spark = get_spark()
market_schema = get_market_schema()
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

    """Bronze is the Ledger: It records every single transaction. If you spend $10 at Starbucks 5 times, there are 5 lines in the ledger.

Silver is the Balance: It only shows you one line: your current total. It "collapses" all those transactions into a single, clean status.
    
    The 3 Big Things Silver Does:
1. Deduplication (The "Latest Version" Only)
In Bronze, if a competitor updates the price of Milk three times today ($3.50, $3.40, then $3.30), you have 3 rows.
In Silver, the MERGE command looks at the item_name and says: "I already have Milk. Instead of adding a 4th row, I will just update the existing row to $3.30."
Result: Your AI model doesn't get confused by old prices; it only sees the current one.

2. Data Cleaning (The "Quality Filter")
Bronze takes everything, even if it's "trash" (like a price of -$500.00 by mistake). In the Silver step, we can add a line of code to filter out that trash.
Result: Silver is "Trusted." You know the data there is accurate.

3. Conforming (Standardization)
In Bronze, one source might send "Milk" and another might send "milk ". In Silver, we can run .trim() or .lower() to make sure they match perfectly.

    """

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


bronze_market_history = f"{S3_BUCKET}/ingestion/bronze_market_history/"

print(f"Starting Silver Stream reading from: {bronze_market_history}")
# 4. Start the Stream from Bronze to Silver
# We read FROM the Bronze Delta path
bronze_stream = spark.readStream.format("delta").load(bronze_market_history)

silver_query = bronze_stream.writeStream \
    .foreachBatch(upsert_to_silver) \
    .option("checkpointLocation", silver_checkpoint) \
    .start()

# Keep it running
silver_query.awaitTermination()
