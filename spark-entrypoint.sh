#!/usr/bin/env bash
set -euo pipefail
python3 /opt/lab/configure.py
exec "$@"
