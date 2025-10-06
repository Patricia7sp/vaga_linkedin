#!/usr/bin/env bash
set -euo pipefail

CMD="${1:-run}"
shift || true

# Ensure the working directory is the project root (mounted at /app)
cd /app

exec python main_production.py "${CMD}" "$@"
