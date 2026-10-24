FROM eclipse-temurin:11-jre-jammy
ARG HADOOP_VERSION=3.4.1
RUN apt-get update && apt-get install -y --no-install-recommends curl python3 procps ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN set -eux; \
    url="https://archive.apache.org/dist/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz"; \
    curl -fSL --retry 3 "$url" -o /tmp/hadoop.tar.gz; \
    curl -fSL --retry 3 "$url.sha512" -o /tmp/hadoop.sha512; \
    python3 -c 'import hashlib,re; expected=re.search(r"\b[0-9a-fA-F]{128}\b",open("/tmp/hadoop.sha512").read()).group().lower(); actual=hashlib.sha512(open("/tmp/hadoop.tar.gz","rb").read()).hexdigest(); assert actual==expected,"Hadoop SHA512 mismatch"'; \
    tar -xzf /tmp/hadoop.tar.gz -C /opt; \
    mv "/opt/hadoop-${HADOOP_VERSION}" /opt/hadoop; \
    rm /tmp/hadoop.tar.gz /tmp/hadoop.sha512
ENV HADOOP_HOME=/opt/hadoop HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop
ENV PATH=/opt/hadoop/bin:/opt/hadoop/sbin:$PATH
ENV HADOOP_MAPRED_HOME=/opt/hadoop HADOOP_HEAPSIZE_MAX=512
COPY configure.py entrypoint.sh /opt/lab/
RUN sed -i 's/\r$//' /opt/lab/entrypoint.sh
ENTRYPOINT ["bash", "/opt/lab/entrypoint.sh"]
