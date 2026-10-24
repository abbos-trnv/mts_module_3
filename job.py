"""Spark on YARN -> partitioned Parquet on HDFS; Hive registration follows."""
import argparse

from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import StringType, StructField, StructType


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if not all(p.startswith('hdfs://') for p in (args.input, args.output)):
        raise ValueError('Both paths must use hdfs://')

    spark = SparkSession.builder.appName('Homework-Spark-YARN').getOrCreate()
    try:
        if spark.sparkContext.master != 'yarn':
            raise RuntimeError('Submit with --master yarn, not local mode')
        print('YARN application:', spark.sparkContext.applicationId)
        schema = StructType([StructField(c, StringType()) for c in
                             ['sale_id', 'product', 'quantity', 'price', 'sale_date']])
        raw = spark.read.schema(schema).option('header', True).option(
            'mode', 'FAILFAST').csv(args.input)
        typed = raw.select(
            F.col('sale_id').cast('long').alias('sale_id'),
            F.lower(F.trim('product')).alias('product'),
            F.col('quantity').cast('int').alias('quantity'),
            F.col('price').cast('decimal(10,2)').alias('price'),
            F.to_date('sale_date', 'yyyy-MM-dd').alias('dt'),
        )
        invalid = typed.filter(
            F.col('sale_id').isNull() | F.col('product').isNull() |
            (F.col('product') == '') | F.col('quantity').isNull() |
            (F.col('quantity') <= 0) | F.col('price').isNull() |
            (F.col('price') < 0) | F.col('dt').isNull())
        if invalid.limit(1).count():
            raise ValueError('Invalid row: check source types, dates and amounts')
        result = (typed.withColumn('amount', F.col('quantity') * F.col('price'))
                  .groupBy('dt', 'product')
                  .agg(F.sum('quantity').alias('total_quantity'),
                       F.sum('amount').cast('decimal(18,2)').alias('revenue'))
                  .select('product', 'total_quantity', 'revenue',
                          F.date_format('dt', 'yyyy-MM-dd').alias('dt')))
        result.show(truncate=False)
        # SQL/Hive partitions are directories dt=YYYY-MM-DD, not Spark tasks.
        result.write.mode('overwrite').partitionBy('dt').parquet(args.output)
        print('Written partitioned result:', args.output)
    finally:
        spark.stop()


if __name__ == '__main__':
    main()
