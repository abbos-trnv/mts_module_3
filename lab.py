"""Python 3.9+, Docker Compose v2; runs on Windows and Linux."""
import argparse
import json
from pathlib import Path
import subprocess
import secrets

ROOT = Path(__file__).resolve().parent
BASE = 'hdfs://namenode:8020/user/root/module4'


def dc(*args, capture=False, timeout=1800):
    return subprocess.run(['docker', 'compose', *args], cwd=ROOT, check=True,
                          capture_output=capture, text=True, timeout=timeout)


def spark(*args, capture=False):
    return dc('run', '--rm', '--no-deps', 'spark', *args, capture=capture)


def beeline(sql, capture=False):
    return dc('exec', '-T', 'spark-hiveserver2', 'beeline',
              '-u', 'jdbc:hive2://localhost:10000/default', '-n', 'root',
              '--silent=true', '--showHeader=false', '--outputformat=tsv2',
              '-e', sql, capture=capture)


def check_cluster():
    state = json.loads(spark('curl', '-fsS',
        'http://namenode:9870/jmx?qry=Hadoop:service=NameNode,name=FSNamesystemState',
        capture=True).stdout)['beans'][0]
    if state.get('NumLiveDataNodes') != 3 or state.get('NumDeadDataNodes') != 0:
        raise RuntimeError('Start and verify module-1-hdfs: expected 3 live DataNodes')
    raw = spark('curl', '-fsS', 'http://resourcemanager:8088/ws/v1/cluster/nodes', capture=True).stdout
    nodes = (json.loads(raw).get('nodes') or {}).get('node', [])
    if len(nodes) != 3 or any(n['state'] != 'RUNNING' for n in nodes):
        raise RuntimeError('Start and verify module-2-yarn: expected 3 RUNNING NodeManagers')


def verify():
    parts = beeline('SHOW PARTITIONS spark_hw.daily_sales;', capture=True).stdout
    if set(parts.strip().splitlines()) != {'dt=2026-10-22', 'dt=2026-10-23'}:
        raise RuntimeError(f'Unexpected partitions: {parts}')
    rows = beeline('SELECT dt, product, total_quantity, revenue '
                   'FROM spark_hw.daily_sales ORDER BY dt, product;', capture=True).stdout
    expected = ['2026-10-22\tbook\t2\t1000.00', '2026-10-22\tpen\t5\t200.00',
                '2026-10-23\tbook\t1\t500.00', '2026-10-23\tnotebook\t3\t360.00']
    if rows.strip().splitlines() != expected:
        raise RuntimeError(f'Unexpected Hive rows: {rows}')
    print(rows)
    print('PASS: standard Hive Beeline reads four expected rows in two HDFS partitions')


def run():
    check_cluster()
    spark('hdfs', 'dfs', '-mkdir', '-p', BASE + '/input')
    spark('hdfs', 'dfs', '-put', '-f', '/app/data/sales.csv', BASE + '/input/sales.csv')
    spark('hdfs', 'dfs', '-ls', BASE + '/input')
    spark('spark-submit', '--master', 'yarn', '--deploy-mode', 'cluster',
          '--num-executors', '2', '--executor-cores', '1',
          '--executor-memory', '1g', '--driver-memory', '1g',
          '--conf', 'spark.yarn.submit.waitAppCompletion=true',
          '--conf', 'spark.dynamicAllocation.enabled=false',
          '--conf', 'spark.yarn.appMasterEnv.PYSPARK_PYTHON=python3',
          '--conf', 'spark.executorEnv.PYSPARK_PYTHON=python3',
          '--conf', 'spark.sql.shuffle.partitions=2',
          '/app/job.py', '--input', BASE + '/input/sales.csv', '--output', BASE + '/output')
    # Only register the table after spark-submit reports successful completion.
    beeline((ROOT / 'table.sql').read_text(encoding='utf-8'))
    verify()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['up', 'run', 'verify', 'down', 'logs'])
    action = parser.parse_args().action
    if action == 'up':
        # Never commit this file: PostgreSQL and Hive use the same local secret.
        env_path = ROOT / '.env'
        if not env_path.exists():
            with env_path.open('x', encoding='utf-8') as handle:
                handle.write('METASTORE_PASSWORD=' + secrets.token_urlsafe(32) + '\n')
            env_path.chmod(0o600)
        dc('--profile', 'tools', 'build')
        check_cluster()
        spark('hdfs', 'dfsadmin', '-safemode', 'wait')
        spark('hdfs', 'dfs', '-mkdir', '-p', '/user/hive/warehouse', '/tmp')
        dc('up', '-d', '--wait', '--wait-timeout', '600')
        run()
    elif action == 'run':
        run()
    elif action == 'verify':
        verify()
    elif action == 'down':
        dc('down')
    else:
        dc('logs', '--tail', '150')


if __name__ == '__main__':
    main()
