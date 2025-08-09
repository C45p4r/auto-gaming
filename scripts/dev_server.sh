#!/usr/bin/env bash
set -euo pipefail

export PYTHONUNBUFFERED=1

if ! command -v uvicorn >/dev/null 2>&1; then
  echo "uvicorn not found. Install dependencies first." >&2
  exit 1
fi

exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000


