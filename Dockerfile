# Built by module-1-hdfs / module-2-yarn before this project.
FROM mts-hadoop:3.4.1
ARG SPARK_VERSION=3.5.7
RUN set -eux; \
    url="https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop3.tgz"; \
    curl -fSL --retry 3 "$url" -o /tmp/spark.tgz; \
    curl -fSL --retry 3 "$url.sha512" -o /tmp/spark.sha512; \
    python3 -c 'import hashlib,re; expected=re.search(r"\b[0-9a-fA-F]{128}\b",open("/tmp/spark.sha512").read()).group().lower(); actual=hashlib.sha512(open("/tmp/spark.tgz","rb").read()).hexdigest(); assert actual==expected,"Spark SHA512 mismatch"'; \
    tar -xzf /tmp/spark.tgz -C /opt; \
    mv "/opt/spark-${SPARK_VERSION}-bin-hadoop3" /opt/spark; \
    rm /tmp/spark.tgz /tmp/spark.sha512
ENV SPARK_HOME=/opt/spark YARN_CONF_DIR=/opt/hadoop/etc/hadoop PYSPARK_PYTHON=python3
ENV PATH=/opt/spark/bin:$PATH
COPY configure.py /opt/lab/configure.py
COPY spark-entrypoint.sh /opt/lab/spark-entrypoint.sh
COPY job.py /app/job.py
COPY data /app/data
RUN sed -i 's/\r$//' /opt/lab/spark-entrypoint.sh
WORKDIR /app
ENTRYPOINT ["bash", "/opt/lab/spark-entrypoint.sh"]
