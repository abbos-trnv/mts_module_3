#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in
  schema)
    # An existing version must validate; a partially initialized DB must fail.
    if /opt/hive/bin/schematool -dbType postgres -info; then
      /opt/hive/bin/schematool -dbType postgres -validate
    else
      /opt/hive/bin/schematool -dbType postgres -initSchema
      /opt/hive/bin/schematool -dbType postgres -validate
    fi
    ;;
  metastore) exec /opt/hive/bin/hive --service metastore ;;
  hiveserver2) exec /opt/hive/bin/hive --service hiveserver2 ;;
  *) echo 'Expected schema, metastore or hiveserver2' >&2; exit 2 ;;
esac
