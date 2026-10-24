FROM apache/hive:4.0.0-alpha-2
USER root
ADD https://repo.maven.apache.org/maven2/org/postgresql/postgresql/42.5.1/postgresql-42.5.1.jar /opt/hive/lib/postgresql.jar
RUN chmod 644 /opt/hive/lib/postgresql.jar
COPY core-site.xml hdfs-site.xml /opt/hive/conf/
COPY hive-site.xml /opt/hive/conf/hive-site.xml.template
COPY start.sh /opt/hive/start.sh
RUN sed -i 's/\r$//' /opt/hive/start.sh
# Same HDFS identity as the existing teaching cluster (root, simple auth).
ENTRYPOINT ["bash", "/opt/hive/start.sh"]
