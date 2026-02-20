"""
Feature	Pandas	                                                                                        Spark (PySpark)
Execution	Single-node. It runs on one CPU/Laptop.	                                                    Distributed. It runs on a cluster (many CPUs).
Memory Limit	Limited by your RAM. If you have a 10GB file and 8GB RAM, Pandas crashes.	            Limited by the total RAM of the cluster. It handles Petabytes easily.
Evaluation	Eager. It does the math the second you hit Enter.	                                        Lazy. It waits until the last second to find the fastest way to work.
Data Format	Row-based (mostly).	                                                                        Columnar (highly optimized for big math).


# Pandas has 15+ years of specialized functions for visualization, finance, and deep statistics that Spark doesn't have yet.

Spark: Clean and aggregate 1 Terabyte of raw logs down to 10MB of summaries.
Pandas: Convert that 10MB summary into a Pandas DataFrame (df.toPandas()) to make a pretty chart or a machine learning model.

"""
from pyspark.sql import SparkSession

# 1. Initialize your "Local Cluster"
# .master("local[*]") tells Spark to use all available cores on your laptop
spark = SparkSession.builder \
    .appName("IndependentLearning") \
    .master("local[*]") \
    .getOrCreate()

# ee all 10 cores working at the same time (parallelism), you have to create at least 10 "buckets" (partitions).
# # Create a range of 1000 numbers and force them into 10 partitions
# df_parallel = spark.range(1000).repartition(10)
#
# # Now, when you run an action, watch the 'Active Tasks' in the UI
# df_parallel.count()

# 2. Create some sample data
data = [("Alice", 34, "Engineering"),
        ("Bob", 45, "Sales"),
        ("Head", 42, "Sales"),
        ("Charlie", 29, "Engineering")]

columns = ["Name", "Age", "Dept"]

# 3. Create a DataFrame
# . In Spark, something invisible happens: Partitioning.
# Spark takes your list of people (Alice, Bob, Charlie) and decides
# how to split them up among those CPU cores we talked about.
#
df = spark.createDataFrame(data, schema=columns)




# SHUFFLE##################

dept_data = [("Engineering", "Building A"),
             ("Sales", "Building B"),
             ("HR", "Building C")]

dept_columns = ["Dept", "Location"]

"""
If you have 10 DataFrames and you are joining them all together, and you have 10 cores available, yes, 
Spark will try to use all 10 cores to read those 10 files simultaneously. 
This is why Spark is so much faster than a standard Python script.
"""
df_depts = spark.createDataFrame(dept_data, schema=dept_columns)

# 2. Perform the JOIN (The Transformation)
# We are linking the 'Dept' column in both DataFrames
# Here is why 2 (or more) cores/stages came into play during the Join, even with your tiny data:

"""
1. The "Safety in Separation" Rule
Spark treats every DataFrame as a separate entity.

Core A is assigned to read df_employees.
Core B is assigned to read df_depts.

Even if Core A finishes in 0.0001 seconds, Spark's "Join Plan" dictates that these
 two streams of data must be pre-sorted and co-located before they can be merged. 
 Spark doesn't know that df_depts only has 3 rows until it actually reads it.

2. The Shuffle Trigger
The moment you say .join(..., on="Dept"), Spark triggers a Wide Transformation.
In Spark's "brain" (the Catalyst Optimizer), a Join looks like this:

Stage 1: Core 1 reads Partition A.
Stage 2: Core 2 reads Partition B.

The Shuffle: "Everyone with the 'Sales' key, go to Core 3. Everyone with 'Engineering', go to Core 4."
"""

df_joined = df.join(df_depts, on="Dept", how="inner")

# 3. The Action SUFFLE
# This is the most important part. To join "Alice" (Engineering) with "Building A" (Engineering),
# Spark has to make sure both records are on the same CPU core.
# It "shuffles" all Engineering records to one core and all Sales records to another.
# The final core performs the actual matching and produces the result.
df_joined.show()


# 4. Perform a transformation
# Spark does NOT actually filter the data.
# each CPU core works on its own piece of data. It doesn't need to talk to its neighbors.
# This is a Narrow Transformation.
df_filtered = df.filter(df.Age > 20)
print(df_filtered)
print(df_filtered.count())
# 5. Show the result (This is the "Action")
# it’s just a Transformation.
# multi-step discovery process. has 3 jobs internally
# job 1: Spark often runs a tiny job just to look at the data and confirm the data types (e.g., Is "Age" really an Integer? Is "Name" a String?). It needs to be 100% sure of the schema before it plans the heavy lifting.
# job 2: It runs a job to "peek" at the first partition to see if it can find 20 rows there., default to 20
# job3 : runs the final job to actually apply your filter(df.Age > 20) logic and format the nice ASCII table you see in your console.
#df_filtered.show()





#
# # 1. Group by Department and calculate average Age
# # This triggers a SHUFFLE
# # This movement of data across the network (or between CPU cores) is called The Shuffle.
# df_grouped = df.groupBy("Dept").avg("Age")
#
# # 2. Rename the column for clarity
# df_final = df_grouped.withColumnRenamed("avg(Age)", "Average_Age")
#
# # 3. Action
# # Since Spark is lazy, if you call .show() on the same DataFrame twice,
# # Spark will re-run the entire calculation from scratch both times.
# # so ask to cache
# df_final.cache()
#
# # First time: Spark runs the whole plan (Slow)
# df_final.show()
#
# # now cache comes
# df_final.count()
# df_final.show()
#
#
# print("========   showing a table  ======")
# # 1. Create a "Virtual Table"
# df.createOrReplaceTempView("employees")
#
# # 2. Run standard SQL
# sql_results = spark.sql("""
#     SELECT Dept, count(*) as total
#     FROM employees
#     WHERE Age > 25
#     GROUP BY Dept
# """)
#
# sql_results.show()





print("\nSpark is running. Open http://localhost:4040 in your browser.")
print("Press ENTER to stop the Spark session and exit...")
input()

# 6. Stop the session (Crucial for raw Python!)
spark.stop()