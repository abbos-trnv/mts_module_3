"""Generate the same Hadoop client configuration in every container."""
import os
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree


def write(name, values):
    root = Element('configuration')
    for key, value in values.items():
        prop = SubElement(root, 'property')
        SubElement(prop, 'name').text = key
        SubElement(prop, 'value').text = str(value)
    ElementTree(root).write(Path(os.environ['HADOOP_CONF_DIR']) / name,
                            encoding='utf-8', xml_declaration=True)


write('core-site.xml', {'fs.defaultFS': 'hdfs://namenode:8020',
                        'hadoop.tmp.dir': '/data/tmp'})
write('hdfs-site.xml', {
    'dfs.namenode.name.dir': 'file:///data/name',
    'dfs.datanode.data.dir': 'file:///data/datanode',
    'dfs.namenode.checkpoint.dir': 'file:///data/secondary',
    'dfs.namenode.rpc-address': 'namenode:8020',
    'dfs.namenode.http-address': 'namenode:9870',
    'dfs.namenode.secondary.http-address': 'secondary:9868',
    'dfs.datanode.http.address': '0.0.0.0:' + os.environ.get('WEB_PORT', '9864'),
    'dfs.replication': '3',
    'dfs.namenode.checkpoint.period': '30',
    'dfs.namenode.checkpoint.check.period': '10',
    'dfs.client.use.datanode.hostname': 'true',
    'dfs.datanode.use.datanode.hostname': 'true',
})
write('yarn-site.xml', {
    'yarn.resourcemanager.hostname': 'resourcemanager',
    'yarn.resourcemanager.webapp.address': 'resourcemanager:8088',
    'yarn.nodemanager.hostname': os.environ.get('HOSTNAME', 'localhost'),
    'yarn.nodemanager.webapp.address': '0.0.0.0:' + os.environ.get('NM_WEB_PORT', '8042'),
    'yarn.nodemanager.aux-services': 'mapreduce_shuffle',
    'yarn.nodemanager.aux-services.mapreduce_shuffle.class': 'org.apache.hadoop.mapred.ShuffleHandler',
    'yarn.nodemanager.resource.memory-mb': '3072',
    'yarn.nodemanager.resource.cpu-vcores': '2',
    'yarn.scheduler.minimum-allocation-mb': '256',
    'yarn.scheduler.maximum-allocation-mb': '3072',
    'yarn.nodemanager.vmem-check-enabled': 'false',
    'yarn.nodemanager.env-whitelist': 'JAVA_HOME,HADOOP_HOME,HADOOP_COMMON_HOME,HADOOP_HDFS_HOME,HADOOP_CONF_DIR,HADOOP_YARN_HOME,HADOOP_MAPRED_HOME,PATH,LANG,CLASSPATH_PREPEND_DISTCACHE',
    'yarn.log-aggregation-enable': 'true',
    'yarn.nodemanager.remote-app-log-dir': '/tmp/logs',
    'yarn.log.server.url': 'http://historyserver:19888/jobhistory/logs',
})
write('mapred-site.xml', {
    'mapreduce.framework.name': 'yarn',
    'mapreduce.application.classpath': '/opt/hadoop/share/hadoop/mapreduce/*,/opt/hadoop/share/hadoop/mapreduce/lib/*',
    'yarn.app.mapreduce.am.env': 'HADOOP_MAPRED_HOME=/opt/hadoop',
    'mapreduce.map.env': 'HADOOP_MAPRED_HOME=/opt/hadoop',
    'mapreduce.reduce.env': 'HADOOP_MAPRED_HOME=/opt/hadoop',
    'mapreduce.map.memory.mb': '512',
    'mapreduce.map.java.opts': '-Xmx384m',
    'mapreduce.reduce.memory.mb': '512',
    'mapreduce.reduce.java.opts': '-Xmx384m',
    'yarn.app.mapreduce.am.resource.mb': '512',
    'yarn.app.mapreduce.am.command-opts': '-Xmx384m',
    'mapreduce.jobhistory.address': 'historyserver:10020',
    'mapreduce.jobhistory.webapp.address': 'historyserver:19888',
    'mapreduce.jobhistory.intermediate-done-dir': '/mr-history/tmp',
    'mapreduce.jobhistory.done-dir': '/mr-history/done',
})
