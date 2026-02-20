"""
Parquet = The best way to store data (Columnar + Compressed).

Parquet is "Columnar." It flips the data on its side.

Speed: If you only want the "Amount" column, Spark physically ignores the "Name" and "Date" columns on the disk. It only touches the data it needs.

Compression: Because a column often contains similar data (e.g., many "USA" entries in a Country column), Parquet can compress that data much better than a CSV. 1GB of CSV often turns into 100MB of Parquet.

"""
import pyarrow as pa
import pyarrow.parquet as pq

# 1. Create a PyArrow Table (No Pandas used!)
# Instead of a DataFrame, we create a Table from a dictionary of arrays
data = {
    'Name': ['Alice', 'Bob', 'Charlie', 'Dave'],
    'Amount': [101, 200, 300, 400],
    'City': ['NY', 'LDN', 'NY', 'TK']
}
pyarrow_table = pa.Table.from_pydict(data)

# 2. Write to Parquet
# pq.write_table handles the binary serialization to your disk
pq.write_table(pyarrow_table, 'my_data_arrow.parquet')
print("Parquet file created using PyArrow.")

# 3. Read from Parquet
# You can still use 'columns' to only pull what you need from the disk
read_table = pq.read_table('my_data_arrow.parquet', columns=['Name', 'Amount'])

print("\nRead from Parquet (PyArrow Table):")
print(read_table.to_string())