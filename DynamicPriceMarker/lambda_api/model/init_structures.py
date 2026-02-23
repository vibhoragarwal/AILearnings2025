from delta import DeltaTable

from foundation.utils.featurebroker import FeatureBroker


def init_table_structures(spark, market_schema):

    # Keep this for Bronze ONLY if the table doesn't exist yet
    try:
        if not DeltaTable.isDeltaTable(spark, FeatureBroker.bronze_market_history_path):
            print("Initializing Bronze Delta Table structure...")
            # We create a 0-row DataFrame with your schema to 'register' the columns
            spark.createDataFrame(spark.sparkContext.emptyRDD(), market_schema) \
                 .write.format("delta") \
                 .mode("overwrite") \
                 .save(FeatureBroker.bronze_market_history_path)
    except Exception as e:
        print(f"Bronze check skipped or failed: {e}")

    # --- SILVER: Pre-create is REQUIRED for Merge ---
    try:
        if not DeltaTable.isDeltaTable(spark, FeatureBroker.silver_market_prices_path):
            print("Initializing empty Silver table for Upsert logic...")
            spark.createDataFrame([], market_schema) \
                 .write.format("delta") \
                 .save(FeatureBroker.silver_market_prices_path)
    except Exception as e:
        print(f"Checking Silver table: {e}")
