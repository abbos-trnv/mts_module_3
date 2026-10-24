# Задание 1. Автоматизированное развертывание HDFS

Hadoop 3.4.1: отдельные NameNode, Secondary NameNode и **три DataNode**. Сервисы работают в пяти контейнерах на одном Docker-хосте. Это учебный кластер; контейнеры не обеспечивают отказоустойчивость при отказе самого хоста. Secondary NameNode создает контрольные точки метаданных, а не заменяет NameNode при аварии.

## Требования

Docker с Linux containers, Docker Compose v2.20+, Python 3.9+. На Windows запустите Docker Desktop. Рекомендуется выделить Docker 4 CPU, 6 ГБ RAM и 12 ГБ диска. Нужен Интернет для скачивания Java-образа и Hadoop; архив Hadoop проверяется по SHA-512 из Apache Archive. Дополнительные библиотеки Python не нужны.

## Запуск

```sh
git clone --branch module-1-hdfs --single-branch https://github.com/abbos-trnv/mts_module_3.git hdfs-cluster
cd hdfs-cluster
python lab.py up
```

Linux: при необходимости используйте `python3`. Первый запуск собирает образ `mts-hadoop:3.4.1`, создает сеть `mts-hadoop`, отдельные тома метаданных и данных, форматирует **только пустой** каталог NameNode и запускает сервисы. Повторный запуск использует существующий VERSION и не форматирует NameNode. Непустой каталог без VERSION вызывает ошибку, чтобы избежать потери метаданных.

Compose ожидает HTTP-доступность каждого демона, затем `lab.py` ожидает регистрации трех живых DataNode без dead/stale узлов и выхода NameNode из safe mode. Выполняются запись уникального тестового файла, ожидание трех реплик, чтение с проверкой содержимого, `fsck`, проверка checkpoint Secondary NameNode и `dfsadmin -report`. Тестовый файл удаляется. Ошибка любого шага завершает команду с ненулевым кодом. При успехе выводится PASS.

## Проверка целостности

```sh
python lab.py verify
docker compose exec namenode hdfs dfsadmin -report
docker compose exec namenode hdfs fsck /
python lab.py logs
```

В отчете ожидаются Live datanodes (3), Dead datanodes (0), отсутствие failed volumes и блоков с повреждениями. В NameNode UI откройте Datanodes: три In service / Live, без dead/decommissioned/stale узлов. Автотест проверяет репликацию тестового файла, а `fsck /` позволяет проверить все данные кластера. В логах после стабилизации не должно быть FATAL, повторяющихся ошибок дисков или связи с NameNode. Первоначальные сообщения ожидания NameNode и safe mode сами по себе не означают повреждение.

Веб-интерфейсы на Docker-хосте:

- NameNode: http://localhost:9870/
- Secondary NameNode: http://localhost:9868/
- DataNode 1: http://localhost:9864/
- DataNode 2: http://localhost:9865/
- DataNode 3: http://localhost:9866/

По умолчанию порты доступны только на этом компьютере. Для доступа с другого компьютера скопируйте `.env.example` в `.env`, задайте `BIND_IP` равным LAN/VPN-адресу Docker-хоста и повторите `python lab.py up`. Разрешите эти TCP-порты в firewall только для нужной учебной сети. Открывайте `http://<LAN-IP>:9870/` и соответствующие остальные порты. Это публикация из контейнера наружу, а не размещение в Интернете. В облаке дополнительно нужны правила доступа провайдера; сам репозиторий сервер не предоставляет.

Для переходов по ссылкам между демонами добавьте в hosts клиентского компьютера строку, заменив IP на реальный адрес хоста:

```text
192.168.1.10 namenode secondary datanode1 datanode2 datanode3 resourcemanager nodemanager1 nodemanager2 nodemanager3 historyserver
```

На самом Docker-хосте можно использовать 127.0.0.1 вместо LAN-IP. Порты интерфейсов DataNode различаются и снаружи, и внутри, поэтому ссылки ведут на правильный сервис. HDFS RPC и DataNode transfer-порты наружу не публикуются: Hadoop-клиенты запускаются внутри общей Docker-сети.

## Хранение и остановка

```sh
python lab.py down
python lab.py up
```

Именованные тома сохраняют NameNode, checkpoint и все три DataNode. Конфигурация генерируется `configure.py`; стандартная репликация равна 3, адрес HDFS внутри сети — `hdfs://namenode:8020`. Не удаляйте только том NameNode при сохраненных DataNode: это уничтожает согласованность namespace.

Полный сброс **всех данных этого учебного HDFS**, только если они больше не нужны:

```sh
docker compose down -v
```

Сначала остановите YARN, если он подключен: иначе общая сеть остается занятой. Не запускайте две копии HDFS с одним именем сети одновременно. Режим Hadoop — simple, сервисы в контейнерах запускаются как root для учебного примера; доступа к Docker socket у них нет. Для производственной эксплуатации нужны другие настройки безопасности и отказоустойчивости.

## Сдача и статус

Ссылка для сдачи — ветка `module-1-hdfs` с этим README и скриптами. Полный запуск в среде подготовки пока не подтвержден: Docker Linux Engine недоступен. Успешная проверка — фактический PASS и три живых DataNode в UI, а не само наличие скрипта.

[Официальная документация HDFS](https://hadoop.apache.org/docs/r3.4.1/hadoop-project-dist/hadoop-hdfs/HdfsUserGuide.html), [установка кластера Hadoop](https://hadoop.apache.org/docs/r3.4.1/hadoop-project-dist/hadoop-common/ClusterSetup.html).
