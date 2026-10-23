"""Cross-platform runner: Python 3.9+, Docker Compose v2; no pip dependencies."""
import argparse
import concurrent.futures
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def compose(*args, capture=False):
    return subprocess.run(
        ['docker', 'compose', *args], cwd=ROOT, check=True,
        text=True, stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def query(sql, user='hive'):
    return compose('exec', '-T', 'hiveserver2', 'beeline',
                   '-u', 'jdbc:hive2://localhost:10000/default', '-n', user,
                   '--silent=true', '--showHeader=false', '--outputformat=tsv2',
                   '-e', sql, capture=True).stdout


def load():
    compose('exec', '-T', 'hiveserver2', 'beeline',
            '-u', 'jdbc:hive2://localhost:10000/default', '-n', 'loader',
            '-f', '/sql/load.sql')


def verify():
    # Repeated loading must replace both partitions without multiplying rows.
    load()
    load()
    partitions = query('SHOW PARTITIONS homework.sales;')
    assert set(partitions.strip().splitlines()) == {
        'dt=2026-10-22', 'dt=2026-10-23'}, partitions
    sql = ('SELECT dt, COUNT(*), CAST(SUM(quantity * price) AS DECIMAL(10,2)) '
           'FROM homework.sales GROUP BY dt ORDER BY dt;')
    # Two independently launched Beeline processes use distinct JDBC sessions.
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(query, sql, name) for name in ('alice', 'bob')]
        for future in futures:
            result = future.result()
            assert result.strip().splitlines() == [
                '2026-10-22\t2\t1200.00', '2026-10-23\t2\t860.00'], result
            print(result)
    print('PASS: two clients, two partitions, four rows; reload is idempotent.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['up', 'load', 'verify', 'down', 'logs'])
    action = parser.parse_args().action
    if action == 'up':
        compose('up', '-d', '--build', '--wait', '--wait-timeout', '900')
    elif action == 'load':
        load()
    elif action == 'verify':
        verify()
    elif action == 'down':
        compose('down')
    else:
        compose('logs', '--tail', '150')


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(exc.stdout or '', file=sys.stderr)
        print(exc.stderr or '', file=sys.stderr)
        sys.exit(exc.returncode)
