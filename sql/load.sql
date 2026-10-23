CREATE DATABASE IF NOT EXISTS homework;
CREATE TABLE IF NOT EXISTS homework.sales (
  sale_id BIGINT, product STRING, quantity INT, price DECIMAL(10,2)
)
PARTITIONED BY (dt STRING)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
STORED AS TEXTFILE
TBLPROPERTIES ('transactional'='false');

LOAD DATA LOCAL INPATH '/input/sales-2026-10-22.csv'
OVERWRITE INTO TABLE homework.sales PARTITION (dt='2026-10-22');
LOAD DATA LOCAL INPATH '/input/sales-2026-10-23.csv'
OVERWRITE INTO TABLE homework.sales PARTITION (dt='2026-10-23');
SHOW PARTITIONS homework.sales;
SELECT dt, COUNT(*) AS rows_count, SUM(quantity * price) AS revenue
FROM homework.sales GROUP BY dt ORDER BY dt;
