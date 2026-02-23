"""
Gold is usually a "Batch" process, not a "Streaming" process.

Can you keep it running?
Technically, you could turn this into a stream, but in the real world, you usually don't want your Gold layer to be a continuous stream. Here is why:

Silver must be a stream because it needs to catch every alert immediately.

Gold is for business decisions. You don't want your store prices flickering every second. You usually run the Gold code on a schedule (e.g., every hour or every morning) to generate a "Fresh Report."
"""

from lambda_api.setup_env import update_environment
update_environment()
from pyspark.sql import functions as F
from config.spark_config import get_spark
from foundation.utils.featurebroker import FeatureBroker

spark = get_spark()

# 2. Mock "My Shop Prices"
# In a real app, this would be a table of what the SME is currently charging
my_shop_data = [
    ("MILK", 4.00),
    ("BREAD", 2.50)
]
my_shop_df = spark.createDataFrame(my_shop_data, ["item_name", "my_price"])

# 3. Load Silver (The Competitor Prices)
silver_df = spark.read.format("delta").load(FeatureBroker.silver_market_prices_path)

# 4. Create Gold: The Decision Table
# We join our prices with competitor prices and calculate the "GAP"
gold_df = silver_df.join(my_shop_df, on="item_name", how="inner") \
    .withColumn("price_gap", F.round((F.col("my_price") - F.col("competitor_price")), 2)) \
    .withColumn("action", F.when(F.col("price_gap") > 0.50, "DROP PRICE")
                .when(F.col("price_gap") < -0.20, "RAISE PRICE")
                .otherwise("KEEP PRICE"))

# 5. Save to Gold
gold_df.write.format("delta").mode("overwrite").save(FeatureBroker.gold_pricing_decisions_path)

print("--- GOLD LAYER: PRICING DECISIONS ---")
gold_df.show()