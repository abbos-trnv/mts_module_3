# Задание 4. Apache Spark под управлением YARN

Автоматизированная цепочка: CSV → HDFS → Spark на YARN → преобразования и агрегация → Parquet с партициями → внешняя таблица Hive → проверка чтения Beeline.

Решение использует HDFS из ветки `module-1-hdfs` и YARN из `module-2-yarn` этого репозитория. Новые NameNode/DataNode/ResourceManager/NodeManager здесь не создаются. Spark 3.5.7 отправляет приложение в существующий YARN в режиме cluster. Hive 4.0.0-alpha-2 использует отдельный metastore и PostgreSQL.

## Требования

- Docker Desktop с Linux containers либо Docker Engine, Compose v2.20+.
- Python 3.9+ на компьютере запуска, без дополнительных pip-пакетов.
- Работающие задания 1 и 2 на том же Docker-хосте, общая сеть `mts-hadoop`, образ `mts-hadoop:3.4.1`.
- Для всех сервисов вместе рекомендуется выделить Docker 16 ГБ RAM, 4 CPU, 25 ГБ диска. Нужен Интернет для первоначальной сборки образов.

Java, Hadoop, Spark и Python внутри контейнера клиента устанавливаются Dockerfile. На NodeManager уже есть Java 11 и Python 3 из задания 2; Spark передает свои библиотеки и Python-приложение в YARN автоматически. Не требуется вручную ставить Spark на каждый узел. Архив Spark проверяется SHA-512 из Apache Archive.

## Полный запуск с нуля

Откройте терминал в папке для трех отдельных копий репозитория:

```sh
git clone --branch module-1-hdfs --single-branch https://github.com/abbos-trnv/mts_module_3.git hdfs-cluster
git clone --branch module-2-yarn --single-branch https://github.com/abbos-trnv/mts_module_3.git yarn-cluster
git clone --branch module-4-spark --single-branch https://github.com/abbos-trnv/mts_module_3.git spark-cluster

cd hdfs-cluster
python lab.py up
cd ../yarn-cluster
python lab.py up
cd ../spark-cluster
python lab.py up
```

На Linux при необходимости используйте `python3`. На Windows сначала запустите Docker Desktop. Если первые два задания уже работают, клонируйте только последнюю ветку, перейдите в ее папку и выполните `python lab.py up`.

Последняя команда создает случайный пароль PostgreSQL в локальном `.env` (он исключен из Git), собирает клиент Spark и Hive, проверяет три живых DataNode и три RUNNING NodeManager, создает HDFS warehouse, запускает PostgreSQL, схему metastore, отдельный metastore и HiveServer2. Затем автоматически загружает CSV, отправляет Spark-приложение, регистрирует таблицу и проверяет ее через Beeline. На каждом этапе ошибки приводят к ненулевому коду завершения. Не удаляйте `.env` при сохраненном томе PostgreSQL: новый пароль не изменит пароль уже созданной БД. На Windows ограничьте доступ к этому файлу средствами прав пользователя.

Первоначальный стенд Hive из `main` запускать не требуется: его `file:///warehouse` не связан с HDFS. Здесь тот же подход с отдельным metastore, но параметры Hive адаптированы к `hdfs://namenode:8020`. Новые имена сервисов `spark-postgres`, `spark-metastore`, `spark-hiveserver2` и внешние порты 10010/10012 исключают конфликт с третьим заданием. Метаданные четвертого задания хранятся в собственном томе PostgreSQL.

## Как выполнены семь требований

1. **Сессия Spark под YARN.** `lab.py` вызывает `spark-submit --master yarn --deploy-mode cluster`. `job.py` создает `SparkSession`, проверяет `sparkContext.master == 'yarn'` и выводит YARN application ID. Драйвер и два исполнителя работают в контейнерах YARN. Режим local не используется.
2. **Подключение к прежнему HDFS.** `configure.py` генерирует те же параметры Hadoop, что в заданиях 1–2. `HADOOP_CONF_DIR` и `YARN_CONF_DIR` указывают на конфигурацию с `fs.defaultFS=hdfs://namenode:8020` и `yarn.resourcemanager.hostname=resourcemanager`. Клиент находится в общей сети `mts-hadoop`; конфигурация передается YARN вместе с приложением.
3. **Чтение предварительно загруженных данных.** До отправки Spark `hdfs dfs -put -f` копирует `data/sales.csv` в `hdfs://namenode:8020/user/root/module4/input/sales.csv`. Созданная сессия выполняет `spark.read.csv()` по этому HDFS-пути.
4. **Преобразования.** Идентификатор приводится к BIGINT, количество — INT, цена — DECIMAL, дата — DATE. Названия товаров очищаются через trim/lower, некорректные строки вызывают ошибку. Вычисляется `quantity * price`, затем выполняются groupBy по дате/товару и sum количества/стоимости.
5. **Партиционирование при записи.** `result.write.mode('overwrite').partitionBy('dt').parquet(...)` сохраняет данные в HDFS. Возникают каталоги `output/dt=2026-10-22` и `output/dt=2026-10-23`. Число партиций Spark при вычислении и разделение таблицы по dt — разные настройки.
6. **Сохранение как таблицы.** После успешного завершения Spark скрипт выполняет `table.sql`: создает внешнюю Hive-таблицу `spark_hw.daily_sales` с форматом PARQUET и LOCATION в HDFS. `MSCK REPAIR TABLE` регистрирует каталоги партиций. Запись файлов и регистрация таблицы составляют два последовательных этапа автоматизации.
7. **Чтение стандартным клиентом Hive.** `lab.py verify` запускает настоящий Beeline через JDBC HiveServer2, проверяет точный список партиций и все строки результата. Spark SQL вместо Hive для этой проверки не используется.

Прямое подключение Spark к metastore Hive 4 alpha здесь не требуется: Spark пишет совместимые Parquet-файлы, а таблицу регистрирует HiveServer2. Поэтому нет зависимости от совместимости клиента metastore Spark 3.5 с Hive 4 и не создается embedded Derby. Требование «сохранить как таблицу» выполняется SQL-регистрацией внешней таблицы; `saveAsTable()` в формулировке задания не указан как обязательный метод.

Hive использует MR/local для собственных SQL-проверок, но читает файлы с HDFS. Это не меняет режим приложения Spark: оно выполняется именно под YARN.

## Ожидаемый результат

Исходные данные: четыре продажи за два дня. Проверка должна вывести строки (разделитель — табуляция):

```text
2026-10-22  book      2  1000.00
2026-10-22  pen       5   200.00
2026-10-23  book      1   500.00
2026-10-23  notebook  3   360.00
PASS: standard Hive Beeline reads four expected rows in two HDFS partitions
```

Схема таблицы: `product STRING, total_quantity BIGINT, revenue DECIMAL(18,2)`, ключ партиции `dt STRING`. Строка даты хранится в имени каталога. Типы Parquet совпадают с объявлением Hive.

## Повторный запуск и ручная проверка

```sh
python lab.py run
python lab.py verify
```

`run` повторяет загрузку, Spark-обработку, регистрацию и проверку. `verify` только читает готовую таблицу. Повторный run заменяет CSV и **весь** `/user/root/module4/output`, пересоздает только таблицу `spark_hw.daily_sales` в отдельном metastore. Используйте эти пути только для учебного задания. Не запускайте несколько копий одновременно: публикация результата не атомарная, во время обновления таблица может временно быть недоступна. Изменяя CSV, скорректируйте ожидаемые строки проверки.

Подключение стандартным клиентом:

```sh
docker compose exec spark-hiveserver2 beeline -u jdbc:hive2://localhost:10000/default -n root
```

Далее:

```sql
SHOW PARTITIONS spark_hw.daily_sales;
DESCRIBE FORMATTED spark_hw.daily_sales;
SELECT * FROM spark_hw.daily_sales WHERE dt='2026-10-23';
```

В DESCRIBE FORMATTED проверьте EXTERNAL_TABLE, Parquet и HDFS Location. Внешний JDBC-клиент на Docker-хосте: `jdbc:hive2://localhost:10010/default`. Hive UI: http://localhost:10012/.

## Доказательство работы под YARN

В ResourceManager http://localhost:8088/ найдите `Homework-Spark-YARN`. В журнале spark-submit отображается ID `application_...`; итоговый статус должен быть FINISHED/SUCCEEDED. Команды из папки задания 2:

```sh
docker compose exec resourcemanager yarn application -list -appStates ALL
docker compose exec resourcemanager yarn logs -applicationId <application_id>
```

JobHistory Server из задания 2 хранит историю MapReduce, а не историю Spark. Статус Spark смотрите в YARN; Spark History Server для требований этого задания не нужен.

## Диагностика и остановка

```sh
python lab.py logs
python lab.py down
```

Сначала остановите четвертое задание, затем YARN, затем HDFS. Метаданные PostgreSQL и данные HDFS сохраняются. `down` не удаляет тома. Если приложение зависает в ACCEPTED, проверьте память/CPU очереди YARN. Ошибка имени узла означает, что контейнеры не находятся в общей сети или первые задания не запущены. Ошибки HDFS требуют проверки NameNode и трех DataNode. Если Beeline не видит партиции — проверьте LOCATION, HDFS-каталоги и MSCK REPAIR.

Контейнеры используют учебную simple-аутентификацию и HDFS-пользователя root; это согласовано с заданиями 1–2 и позволяет Hive читать результат Spark. Пароль PostgreSQL генерируется локально и в репозиторий не попадает. PostgreSQL и metastore не публикуются на хост; JDBC и Hive UI опубликованы только на 127.0.0.1. Внутри контейнера Hive слушает сетевой интерфейс для доступа из общей Docker-сети. Этот стенд не предназначен для общедоступного сервера.

## Проверка артефактов и сдача

Ветка содержит инструкцию и скрипты автоматического выполнения. Проверены синтаксис Python, XML и конфигурация Compose. Полный запуск в среде подготовки пока не подтвержден: Docker Linux Engine недоступен. Фактическое подтверждение выполнения — SUCCEEDED в YARN и PASS проверки через Beeline; наличие скриптов само по себе этого не доказывает.

Ссылка для сдачи: https://github.com/abbos-trnv/mts_module_3/tree/module-4-spark

## Источники

- [Официальная документация Spark 3.5.7: запуск на YARN](https://spark.apache.org/docs/3.5.7/running-on-yarn.html).
- [Отправка Spark-приложений](https://spark.apache.org/docs/3.5.7/submitting-applications.html).
- [DataFrameWriter: запись и partitionBy](https://spark.apache.org/docs/3.5.7/api/scala/org/apache/spark/sql/DataFrameWriter.html).
