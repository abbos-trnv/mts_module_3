#!/usr/bin/env bash
set -euo pipefail
python3 /opt/lab/configure.py
mkdir -p /data/tmp
case "${1:-}" in
  namenode)
    mkdir -p /data/name
    if [[ ! -f /data/name/current/VERSION ]]; then
      # Only an empty volume may be formatted. Never reformat existing metadata.
      if [[ -n "$(ls -A /data/name)" ]]; then
        echo 'NameNode volume is nonempty but VERSION is missing; inspect it manually' >&2
        exit 1
      fi
      hdfs namenode -format -nonInteractive -clusterid mts-lab
    fi
    exec hdfs namenode ;;
  datanode) exec hdfs datanode ;;
  secondary) exec hdfs secondarynamenode ;;
  resourcemanager) exec yarn resourcemanager ;;
  nodemanager) exec yarn nodemanager ;;
  historyserver) exec mapred historyserver ;;
  *) exec "$@" ;;
esac
