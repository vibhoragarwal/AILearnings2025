
from pyspark.sql import SparkSession
from delta import configure_spark_with_delta_pip
from delta.tables import DeltaTable

# 1. Setup the Builder
builder = SparkSession.builder \
    .appName("StableDelta") \
    .master("local[*]") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.sql.warehouse.dir", "spark-warehouse")

# 2. Initialize with Delta support
spark = configure_spark_with_delta_pip(builder).getOrCreate()

# 3. Create a test DataFrame
try:
    # Alice is an update, Charlie is a new insert
    new_data = [("Alice", 75), ("Charlie", 300), ("Charlie", 301)]
    updates_df = spark.createDataFrame(new_data, ["Name", "Amount"])

    # Remove duplicates from the incoming data first
    clean_updates_df = updates_df.dropDuplicates(["Name"])



    # Define a local path
    path = "tmp/stable_delta_table"

    original_dt = DeltaTable.forPath(spark, path)
    #add data but completely ignore rows that already exist (to prevent duplicates in your master table), you just leave out the whenMatched part:
    # dt.alias("target").merge(
    #     updates_df.alias("source"),
    #     "target.Name = source.Name"
    # ).whenNotMatchedInsertAll() \
    #     .execute()


    original_dt.alias("target") \
        .merge(
        clean_updates_df.alias("source"),
        "target.Name = source.Name"  # The 'Join' condition
    ) \
        .whenMatchedUpdate(set={"Amount": "source.Amount"}) \
        .whenNotMatchedInsert(values={"Name": "source.Name", "Amount": "source.Amount"}) \
        .execute()

    print("Merge Complete!")
    original_dt.toDF().show()

    deduped_df = spark.read.format("delta").load(path).dropDuplicates(["Name", "Amount"])

    # 2. Overwrite the table with the clean data
    deduped_df.write.format("delta").mode("overwrite").save(path)

    print("Table cleaned! Only one Charlie remains.")
    spark.read.format("delta").load(path).show()

except Exception as e:
    print(f"Error: {e}")

finally:
    spark.stop()