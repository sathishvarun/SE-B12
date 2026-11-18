#!/usr/bin/env bash
# Stops every Virundhu process and the database/Redis containers.   bash stop.sh
cd "$(dirname "$0")"
ROOT="$(pwd)"
for port in 8450 5450; do
  for pid in $(lsof -ti "tcp:$port" -sTCP:LISTEN 2>/dev/null || true); do
    ps -p "$pid" -o command= | grep -qF "$ROOT" && kill "$pid" 2>/dev/null
  done
done
for pid in $(pgrep -f "arq app.worker.settings.WorkerSettings" || true); do
  ps -p "$pid" -o command= | grep -qF "$ROOT" && kill "$pid" 2>/dev/null
done
docker compose stop >/dev/null 2>&1 || true
echo "Virundhu stopped. Your data is kept. Start again with:  bash start.sh"
