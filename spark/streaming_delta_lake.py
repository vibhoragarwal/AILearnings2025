import os
from pyspark.sql import SparkSession
from delta import configure_spark_with_delta_pip
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

# 1. Setup Session
builder = SparkSession.builder \
    .appName("LocalDeltaStream") \
    .master("local[*]") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")

spark = configure_spark_with_delta_pip(builder).getOrCreate()

# 2. Define Paths
input_path = "tmp/input_json_folder"
checkpoint_path = "tmp/checkpoints"
delta_path = "tmp/delta_sink"

# Create folders if they don't exist
for p in [input_path, checkpoint_path, delta_path]:
    os.makedirs(p, exist_ok=True)

# 3. Define Schema (Streaming requires a pre-defined schema!)
user_schema = StructType([
    StructField("Name", StringType(), True),
    StructField("Amount", IntegerType(), True)
])

# 4. Read Stream
# 'maxFilesPerTrigger' makes it process 1 file at a time so you can watch it work
streaming_df = spark.readStream \
    .schema(user_schema) \
    .option("maxFilesPerTrigger", 1) \
    .json(input_path)

# 5. Write Stream
query = streaming_df.writeStream \
    .format("delta") \
    .outputMode("append") \
    .option("checkpointLocation", checkpoint_path) \
    .start(delta_path)

print(f"Stream started! Drop JSON files into {input_path} to see the magic...")

# Keep the process alive
query.awaitTermination()