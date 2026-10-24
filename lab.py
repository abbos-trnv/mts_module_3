"""Python 3.9+ and Docker Compose v2.20+, no pip dependencies."""
import argparse
import json
import pathlib
import subprocess
import time
import uuid

ROOT = pathlib.Path(__file__).resolve().parent


def dc(*args, capture=False, timeout=600):
    return subprocess.run(['docker', 'compose', *args], cwd=ROOT, check=True,
                          text=True, capture_output=capture, timeout=timeout)


def metrics():
    raw = dc('exec', '-T', 'namenode', 'curl', '-fsS',
             'http://localhost:9870/jmx?qry=Hadoop:service=NameNode,name=FSNamesystemState',
             capture=True).stdout
    return json.loads(raw)['beans'][0]


def verify():
    end = time.monotonic() + 180
    while True:
        state = metrics()
        if (state.get('NumLiveDataNodes') == 3 and
                state.get('NumDeadDataNodes') == 0 and
                state.get('NumStaleDataNodes') == 0):
            break
        if time.monotonic() > end:
            raise RuntimeError(f'Expected 3 live, 0 dead/stale DataNodes: {state}')
        time.sleep(3)
    dc('exec', '-T', 'namenode', 'hdfs', 'dfsadmin', '-safemode', 'wait', timeout=180)
    path = '/tmp/hdfs-check-' + uuid.uuid4().hex
    # Write a unique, nonempty file without overwriting user data.
    dc('exec', '-T', 'namenode', 'bash', '-c',
       'printf "hdfs replication test\\n" > /tmp/hdfs-check.txt; '
       'hdfs dfs -put /tmp/hdfs-check.txt "$1"', 'bash', path)
    try:
        dc('exec', '-T', 'namenode', 'hdfs', 'dfs', '-setrep', '-w', '3', path, timeout=180)
        content = dc('exec', '-T', 'namenode', 'hdfs', 'dfs', '-cat', path, capture=True).stdout
        if content != 'hdfs replication test\n':
            raise RuntimeError(f'Readback mismatch: {content!r}')
        result = dc('exec', '-T', 'namenode', 'hdfs', 'fsck', path,
                    '-files', '-blocks', '-locations', capture=True).stdout
        print(result)
        if 'Status: HEALTHY' not in result or 'Live_repl=3' not in result:
            raise RuntimeError('Expected a healthy block with three live replicas')
    finally:
        dc('exec', '-T', 'namenode', 'hdfs', 'dfs', '-rm', path)
    # Wait for the running Secondary NameNode; do not start a second daemon
    # against its locked checkpoint directory.
    end = time.monotonic() + 180
    while True:
        try:
            dc('exec', '-T', 'secondary', 'bash', '-c',
               'test -f /data/secondary/current/VERSION && ls /data/secondary/current/fsimage_*',
               capture=True)
            break
        except subprocess.CalledProcessError:
            if time.monotonic() > end:
                raise RuntimeError('Secondary NameNode did not create a checkpoint')
            time.sleep(3)
    dc('exec', '-T', 'namenode', 'hdfs', 'dfsadmin', '-report')
    print('PASS: 3 live DataNodes, replicated write/read, healthy block, checkpoint')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['up', 'verify', 'down', 'logs'])
    action = parser.parse_args().action
    if action == 'up':
        dc('up', '-d', '--build', '--wait', '--wait-timeout', '300', timeout=1800)
        verify()
    elif action == 'verify':
        verify()
    elif action == 'down':
        dc('down')
    else:
        dc('logs', '--tail', '150')


if __name__ == '__main__':
    main()
