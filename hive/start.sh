#!/usr/bin/env bash
set -euo pipefail
: "${METASTORE_PASSWORD:?Password must be supplied through the local .env file}"
[[ "$METASTORE_PASSWORD" =~ ^[a-zA-Z0-9_-]+$ ]] || { echo 'Invalid password format' >&2; exit 1; }
template=$(cat /opt/hive/conf/hive-site.xml.template)
printf '%s\n' "${template//__METASTORE_PASSWORD__/$METASTORE_PASSWORD}" > /opt/hive/conf/hive-site.xml
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
