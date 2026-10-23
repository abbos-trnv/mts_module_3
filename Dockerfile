FROM apache/hive:4.0.0-alpha-2
USER root
ADD https://repo.maven.apache.org/maven2/org/postgresql/postgresql/42.5.1/postgresql-42.5.1.jar /opt/hive/lib/postgresql.jar
RUN chmod 644 /opt/hive/lib/postgresql.jar && mkdir -p /warehouse /tmp/hive && chmod 1777 /warehouse /tmp/hive
COPY conf/hive-site.xml /opt/hive/conf/hive-site.xml
COPY scripts/start.sh /opt/hive/start.sh
RUN sed -i 's/\r$//' /opt/hive/start.sh && chmod 755 /opt/hive/start.sh
USER hive
ENTRYPOINT ["bash", "/opt/hive/start.sh"]
