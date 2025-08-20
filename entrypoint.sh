#!/usr/bin/env bash
set -euo pipefail

: "${APP_PORT:=5012}"

echo "Waiting for Postgres at ${PGHOST}:${PGPORT}..."
python - <<'PY'
import os, time, psycopg2
for _ in range(60):
    try:
        psycopg2.connect(
            host=os.getenv("PGHOST","db"),
            port=int(os.getenv("PGPORT","5432")),
            user=os.getenv("PGUSER","trinkgelduser"),
            password=os.getenv("PGPASSWORD",""),
            dbname=os.getenv("PGDATABASE","trinkgeld"),
        ).close()
        break
    except Exception:
        time.sleep(1)
else:
    raise SystemExit("DB not reachable after 60s")
PY

echo "Running migrations..."
export FLASK_APP=run.py
flask db upgrade || true

echo "Starting Gunicorn on 0.0.0.0:${APP_PORT}..."
exec gunicorn -w 3 -b 0.0.0.0:${APP_PORT} run:app
