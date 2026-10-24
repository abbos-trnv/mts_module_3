"""YARN on the HDFS network from module-1-hdfs. Python 3.9+, Compose v2."""
import argparse
import json
from pathlib import Path
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parent


def dc(*args, capture=False, timeout=600):
    return subprocess.run(['docker', 'compose', *args], cwd=ROOT, check=True,
                          text=True, capture_output=capture, timeout=timeout)


def remote(*args, capture=False, timeout=600):
    return dc('exec', '-T', 'resourcemanager', *args, capture=capture, timeout=timeout)


def nodes():
    raw = remote('curl', '-fsS', 'http://localhost:8088/ws/v1/cluster/nodes', capture=True).stdout
    return (json.loads(raw).get('nodes') or {}).get('node', [])


def verify():
    end = time.monotonic() + 180
    while True:
        current = nodes()
        if len(current) == 3 and all(n['state'] == 'RUNNING' for n in current):
            break
        if time.monotonic() > end:
            raise RuntimeError(f'Expected 3 RUNNING NodeManagers: {current}')
        time.sleep(3)
    remote('yarn', 'node', '-list', '-all')
    path = '/tmp/yarn-check-' + uuid.uuid4().hex
    remote('hdfs', 'dfs', '-mkdir', '-p', path + '/input')
    remote('bash', '-c', 'printf "hadoop yarn hadoop\\n" > /tmp/yarn-input.txt; '
           'hdfs dfs -put /tmp/yarn-input.txt "$1/input/text.txt"', 'bash', path)
    try:
        # Uses mapreduce.framework.name=yarn, not LocalJobRunner.
        remote('hadoop', 'jar', '/opt/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.4.1.jar',
               'wordcount', path + '/input', path + '/output')
        actual = remote('hdfs', 'dfs', '-cat', path + '/output/part-r-*', capture=True).stdout
        if actual.strip().splitlines() != ['hadoop\t2', 'yarn\t1']:
            raise RuntimeError(f'Unexpected MapReduce result: {actual!r}')
        print(actual)
        apps = json.loads(remote('curl', '-fsS',
                          'http://localhost:8088/ws/v1/cluster/apps', capture=True).stdout)
        completed = [a for a in (apps.get('apps') or {}).get('app', [])
                     if a.get('finalStatus') == 'SUCCEEDED' and a.get('name') == 'word count']
        if not completed:
            raise RuntimeError('No successful word count application registered by YARN')
        # Also verify the auxiliary history service endpoint.
        remote('curl', '-fsS', 'http://historyserver:19888/ws/v1/history/info')
    finally:
        remote('hdfs', 'dfs', '-rm', '-r', path)
    print('PASS: 3 RUNNING NodeManagers; MapReduce on YARN wrote expected HDFS output')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['up', 'verify', 'down', 'logs'])
    action = parser.parse_args().action
    if action == 'up':
        # HDFS must already be started; the external network must exist.
        dc('build', timeout=1800)
        dc('run', '--rm', '--no-deps', 'resourcemanager', 'hdfs', 'dfsadmin', '-safemode', 'wait')
        dc('run', '--rm', '--no-deps', 'resourcemanager', 'hdfs', 'dfs', '-mkdir', '-p',
           '/tmp/logs', '/mr-history/tmp', '/mr-history/done')
        dc('run', '--rm', '--no-deps', 'resourcemanager', 'hdfs', 'dfs', '-chmod', '1777',
           '/tmp/logs', '/mr-history/tmp')
        dc('up', '-d', '--wait', '--wait-timeout', '300')
        verify()
    elif action == 'verify':
        verify()
    elif action == 'down':
        dc('down')
    else:
        dc('logs', '--tail', '150')


if __name__ == '__main__':
    main()
