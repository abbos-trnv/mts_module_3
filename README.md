# Задание 2. YARN и публикация веб-интерфейсов

Hadoop YARN 3.4.1 поверх HDFS из ветки `module-1-hdfs`: ResourceManager, три NodeManager и MapReduce JobHistory Server. ShuffleHandler включен в каждом NodeManager; агрегация логов и история MapReduce хранятся в существующем HDFS.

## Предпосылки

Docker с Linux containers, Compose v2.20+, Python 3.9+, работающий HDFS из задания 1 на **том же Docker-хосте**, сеть `mts-hadoop`. Для обоих заданий вместе рекомендуется 4 CPU, 12 ГБ RAM и 20 ГБ диска. Каждый NodeManager объявляет 3072 МБ и 2 vcore; это лимит планировщика, а не резервирование памяти Docker. Если ресурсов мало, увеличьте доступную Docker память либо уменьшите ресурсы заданий согласованно с YARN.

## Запуск двух заданий

Храните ветки в разных папках: так переключение ветки не изменит файлы уже запущенного Compose-проекта.

```sh
git clone --branch module-1-hdfs --single-branch https://github.com/abbos-trnv/mts_module_3.git hdfs-cluster
git clone --branch module-2-yarn --single-branch https://github.com/abbos-trnv/mts_module_3.git yarn-cluster
cd hdfs-cluster
python lab.py up
cd ../yarn-cluster
python lab.py up
```

На Linux при необходимости `python3`. Если HDFS уже запущен, нужны только последняя папка и команда. Сборка использует такой же Hadoop-образ и генератор конфигурации, как в задании 1. YARN подключается к существующему `hdfs://namenode:8020`, новый HDFS не создает. До запуска создаются каталоги истории и агрегированных логов HDFS. Веб-готовность каждого сервиса проверяется Compose.

`lab.py up` также выполняет автоматическую проверку: ожидает ровно три RUNNING NodeManager, загружает уникальный входной файл в HDFS, запускает пример wordcount через MapReduce **под YARN**, проверяет результат `hadoop=2, yarn=1` в HDFS и успешный статус приложения в ResourceManager. Проверяет доступность сервера истории. При ошибке команда возвращает ненулевой код; при успехе выводит PASS. Временные данные теста удаляются.

## Веб-интерфейсы

- ResourceManager — http://localhost:8088/ (приложения, очереди, NodeManager).
- NodeManager 1 — http://localhost:8042/.
- NodeManager 2 — http://localhost:8043/.
- NodeManager 3 — http://localhost:8044/.
- MapReduce JobHistory Server — http://localhost:19888/ (завершенные MapReduce jobs).
- NameNode — http://localhost:9870/, Secondary — http://localhost:9868/, DataNode — порты 9864, 9865, 9866 из задания 1.

JobHistory Server показывает историю MapReduce; это не Spark History Server. ResourceManager показывает приложения всех поддерживаемых типов. Вспомогательный ShuffleHandler — сетевой сервис переноса map-output, отдельной административной веб-страницы у него нет.

## Доступ с другого компьютера

1. Скопируйте `.env.example` в `.env` и задайте `BIND_IP` равным реальному LAN/VPN-IP Docker-хоста. При необходимости так же настройте HDFS-ветку.
2. Повторите `python lab.py up`. Compose опубликует порты демонов на выбранном интерфейсе хоста. По умолчанию используется 127.0.0.1, поэтому удаленный доступ без этого шага закрыт.
3. Разрешите TCP 8088, 8042–8044, 19888 в firewall для компьютера проверяющего. Для HDFS UI — также 9870, 9868, 9864–9866. В облаке настройте разрешения провайдера.
4. На внешнем клиенте добавьте в hosts запись, заменив IP на адрес Docker-хоста:

```text
192.168.1.10 namenode secondary datanode1 datanode2 datanode3 resourcemanager nodemanager1 nodemanager2 nodemanager3 historyserver
```

5. Откройте `http://resourcemanager:8088/`, `http://nodemanager1:8042/`, `http://nodemanager2:8043/`, `http://nodemanager3:8044/`, `http://historyserver:19888/`. Прямой доступ по IP и нужному порту тоже работает, но hosts нужен для внутренних ссылок UI. На Docker-хосте можно сопоставить эти имена с 127.0.0.1.

Работающий ApplicationMaster использует динамический порт; для активного приложения переходите через `/proxy/<application_id>/` ResourceManager. Прямой доступ к произвольному внутреннему адресу контейнера снаружи не гарантируется. Завершенный MapReduce job доступен через JobHistory Server и постоянный порт 19888.

Hadoop здесь без Kerberos и TLS. Публикуйте UI только в доверенную учебную LAN/VPN, ограничив источники firewall. Не открывайте административные интерфейсы в общедоступный Интернет. Репозиторий содержит автоматизацию публикации портов; публичный сервер и публичный IP он не создает.

## Проверка и диагностика

```sh
python lab.py verify
docker compose exec resourcemanager yarn node -list -all
docker compose exec resourcemanager yarn application -list -appStates ALL
python lab.py logs
```

В ResourceManager должно быть три здоровых RUNNING узла, приложение `word count` — FINISHED/SUCCEEDED. По application ID можно получить логи: `docker compose exec resourcemanager yarn logs -applicationId <ID>`. Если задача остается ACCEPTED, проверьте свободные ресурсы и настройки очереди. Если нет NodeManager, проверьте сеть `mts-hadoop`, журнал RM/NM и совпадение версии образа. Ошибки записи history/logs требуют проверки HDFS и прав каталогов.

## Остановка

```sh
python lab.py down
cd ../hdfs-cluster
python lab.py down
```

Останавливайте YARN раньше HDFS. Результаты и история в HDFS сохраняются в томах первого задания. После перезапуска RM список прежних приложений может не сохраниться: recovery RM здесь не настроен; история завершенных MapReduce jobs доступна отдельно в JobHistory Server.

## Сдача и статус

Сдайте ссылку на ветку `module-2-yarn`. Инструкция и скрипты подготовлены; полный запуск на текущем компьютере пока не подтвержден из-за недоступности Docker Linux Engine. Отдельно проверьте доступность UI именно с внешнего компьютера после настройки IP/firewall: локальная проверка этого не доказывает.

[Официальная установка Hadoop/YARN](https://hadoop.apache.org/docs/r3.4.1/hadoop-project-dist/hadoop-common/ClusterSetup.html), [документация YARN](https://hadoop.apache.org/docs/r3.4.1/hadoop-yarn/hadoop-yarn-site/YARN.html).
