CREATE DATABASE IF NOT EXISTS spark_hw;
DROP TABLE IF EXISTS spark_hw.daily_sales;
CREATE EXTERNAL TABLE spark_hw.daily_sales (
  product STRING,
  total_quantity BIGINT,
  revenue DECIMAL(18,2)
)
PARTITIONED BY (dt STRING)
STORED AS PARQUET
LOCATION 'hdfs://namenode:8020/user/root/module4/output'
TBLPROPERTIES ('external.table.purge'='false');
MSCK REPAIR TABLE spark_hw.daily_sales;
SHOW PARTITIONS spark_hw.daily_sales;
