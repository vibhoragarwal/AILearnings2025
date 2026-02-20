"""
Gold is usually a "Batch" process, not a "Streaming" process.

Can you keep it running?
Technically, you could turn this into a stream, but in the real world, you usually don't want your Gold layer to be a continuous stream. Here is why:

Silver must be a stream because it needs to catch every alert immediately.

Gold is for business decisions. You don't want your store prices flickering every second. You usually run the Gold code on a schedule (e.g., every hour or every morning) to generate a "Fresh Report."
"""
import os

from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, DoubleType

BASE_FOLDER = "../ingestion"
# 1. Paths
silver_path = os.path.join(BASE_FOLDER, "silver_market_prices")
gold_path = os.path.join(BASE_FOLDER, "gold_pricing_decisions")

# Create folders if they don't exist
for p in [gold_path]:
    os.makedirs(p, exist_ok=True)

# 1. Setup the Builder
builder = SparkSession.builder \
    .appName("StableDelta") \
    .master("local[*]") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.sql.warehouse.dir", "spark-warehouse")

# Define the schema for incoming market alerts
market_schema = StructType([
    StructField("item_name", StringType(), False),
    StructField("competitor_name", StringType(), False),
    StructField("competitor_price", DoubleType(), False),
    StructField("timestamp", StringType(), False)
])

spark = configure_spark_with_delta_pip(builder).getOrCreate()

# 2. Mock "My Shop Prices"
# In a real app, this would be a table of what the SME is currently charging
my_shop_data = [
    ("MILK", 4.00),
    ("BREAD", 2.50)
]
my_shop_df = spark.createDataFrame(my_shop_data, ["item_name", "my_price"])

# 3. Load Silver (The Competitor Prices)
silver_df = spark.read.format("delta").load(silver_path)

# 4. Create Gold: The Decision Table
# We join our prices with competitor prices and calculate the "GAP"
gold_df = silver_df.join(my_shop_df, on="item_name", how="inner") \
    .withColumn("price_gap", F.round((F.col("my_price") - F.col("competitor_price")), 2)) \
    .withColumn("action", F.when(F.col("price_gap") > 0.50, "DROP PRICE")
                .when(F.col("price_gap") < -0.20, "RAISE PRICE")
                .otherwise("KEEP PRICE"))

# 5. Save to Gold
gold_df.write.format("delta").mode("overwrite").save(gold_path)

print("--- GOLD LAYER: PRICING DECISIONS ---")
gold_df.show()