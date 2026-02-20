"""
You use PySpark to do the "heavy lifting"—filtering, joining, and calculating. But instead of saving the result as a regular
CSV or Parquet file (which are "dumb" files), you save it in Delta format.

PySpark: The "Engine" that processes the data.

Delta: The "Storage Layer" that manages how those files are written and tracked.



Frequent Updates: If you need to change data (e.g., "Update Alice's address"), standard Parquet is a
nightmare because you have to rewrite the whole table. Delta makes "Updates" and "Deletes" possible.

Concurrent Access: When one Spark job is writing to a table while another person is reading from it.
 Without Delta, the reader would see partial/corrupt data. With Delta, the reader sees the "old" version until the "new" version is 100% finished.

Audit Requirements Time Travel: In industries like Finance or Healthcare, you need to prove what the data looked like
 on a specific Tuesday three months ago. Time Travel makes this a one-line command.


"""

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
    data = [("Alice", 100), ("Bob", 201)]
    df = spark.createDataFrame(data, ["Name", "Amount"])

    # Define a local path
    path = "tmp/stable_delta_table"

    # Write the data

    """Spark has its own built-in Parquet reading and writing engine written in Java/Scala.
    When you run df.write.format("delta").save(path), Spark converts its internal "Safe" data directly into Parquet files.
     It bypasses Pandas entirely.
    This is why Spark can handle Petabytes of data—it doesn't have to "translate" the data into Python/Pandas format, 
    which would be very slow and memory-intensive.
    """
    print("Attempting to overwrite Delta table...")
    df.write.format("delta").mode("overwrite").save(path)

    # Read it back to prove it worked
    print("Write successful and overwrote from bob 200->201 ! Reading data back:")
    spark.read.format("delta").load(path).show()
    print("Reading data back from 0 version:")
    spark.read.format("delta").option("versionAsOf", 0).load(path).show()

    # Show history (The Delta magic)
    from delta.tables import DeltaTable

    dt = DeltaTable.forPath(spark, path)
    print("Table History:")
    dt.history().select("version", "timestamp", "operation").show()

    # 1. Access the table via its path
    dt = DeltaTable.forPath(spark, path)

    # 2. Perform the Update or say dt.delete("Name = 'Bob'")
    # Standard Spark (Without Delta): If you want to change 1 row in a 1TB table, you usually have to read the entire 1TB, change the row, and write a new 1TB.
    # Delta Lake: If that 1TB is split into 1,000 files (1GB each), and Alice is in "File #42," Delta only rewrites File #42. It ignores the other 999 files.

    """
    If you only have 100 rows, a SQL database (Postgres/MySQL) is better because it can update a single row on a disk page.

Delta is for when you have 100 Billion rows.

In a SQL DB, updating 10 million rows at once would lock the table and crash the system.

In Delta, it just writes some new Parquet files in the background while everyone else keeps reading the old ones. No locking, no crashing.
    """
    print("Updating Alice's amount to 50...")
    dt.update(
        condition="Name = 'Alice'",
        set={"Amount": "50"}
    )

    # Show current state
    print("Current Data after Update:")
    dt.toDF().show()
    print("Table History:")
    dt.history().select("version", "timestamp", "operation").show()

except Exception as e:
    print(f"Error: {e}")

finally:
    spark.stop()