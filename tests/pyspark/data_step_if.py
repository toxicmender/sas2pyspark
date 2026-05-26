from pyspark.sql import functions as F
from pyspark.sql.window import Window

df = spark.table("sales_2024")
df = df.withColumn(
    "category",
    F.when((F.col("revenue") > F.lit(1000)), F.lit("HIGH")).otherwise(F.lit("LOW")),
)
df.write.saveAsTable("sales_final")
