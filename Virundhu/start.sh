#!/usr/bin/env bash
# ------------------------------------------------------------------
#  Virundhu: start everything with ONE command
#     bash start.sh
#  Starts Docker, the database, Redis, the API, the worker and the
#  website, then opens your browser. Press Ctrl + C to stop.
# ------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"
API_PORT=8450
WEB_PORT=5450

say()  { printf "\n\033[1;33m==>\033[0m \033[1m%s\033[0m\n" "$1"; }
ok()   { printf "    \033[1;32m✓\033[0m %s\n" "$1"; }
warn() { printf "\033[1;33m!\033[0m %s\n" "$1"; }
fail() { printf "\n\033[1;31mProblem:\033[0m %s\n\n" "$1"; exit 1; }

[ -f .env ] || fail ".env is missing. Run:  cp .env.example .env   then add your Claude key."

# ---------- 1. Docker ----------
say "1/6  Docker Desktop"
if ! docker info >/dev/null 2>&1; then
  echo "    Starting Docker Desktop (about 30 seconds)..."
  open -a Docker 2>/dev/null || fail "Docker Desktop isn't installed. Install it with:  brew install --cask docker"
  for _ in $(seq 1 60); do docker info >/dev/null 2>&1 && break; sleep 2; done
  docker info >/dev/null 2>&1 || fail "Docker didn't start. Open Docker Desktop yourself, wait for it, then run  bash start.sh  again."
fi
ok "Docker is running"

# ---------- AI key check (one provider only) ----------
envval() { grep -E "^$1=" .env | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'"; }
PROVIDER=$(envval LLM_PROVIDER); AKEY=$(envval ANTHROPIC_API_KEY); OKEY=$(envval OPENAI_API_KEY)
if [ "$PROVIDER" = "anthropic" ]; then
  case "$AKEY" in
    sk-ant-*) ok "AI: Claude key found" ;;
    "") warn "No Claude key in .env (ANTHROPIC_API_KEY). Reviews won't be read until you add one." ;;
    *) fail "ANTHROPIC_API_KEY in .env isn't a Claude key (Claude keys start with sk-ant-). If it's an OpenAI key, move it to OPENAI_API_KEY and set LLM_PROVIDER=openai." ;;
  esac
else
  case "$OKEY" in
    sk-*) ok "AI: OpenAI key found" ;;
    *) warn "No OpenAI key in .env (OPENAI_API_KEY). Reviews won't be read until you add one." ;;
  esac
fi



# ---------- 2. Database + Redis ----------
say "2/6  Database and Redis"
docker compose up -d db redis >/dev/null 2>&1 || fail "Couldn't start the database. Run  docker compose up -d db redis  to see why."
for _ in $(seq 1 40); do
  docker compose exec -T db pg_isready -U virundhu -d virundhu >/dev/null 2>&1 && break; sleep 1
done
docker compose exec -T db pg_isready -U virundhu -d virundhu >/dev/null 2>&1 || fail "The database didn't become ready."
ok "Database and Redis are ready"

# ---------- 3. Free our ports (only stops OLD Virundhu processes) ----------
say "3/6  Checking ports $API_PORT and $WEB_PORT"
for pid in $(pgrep -f "arq app.worker.settings.WorkerSettings" || true); do
  ps -p "$pid" -o command= | grep -qF "$ROOT" && kill "$pid" 2>/dev/null || true
done
for port in $API_PORT $WEB_PORT; do
  for pid in $(lsof -ti "tcp:$port" -sTCP:LISTEN 2>/dev/null || true); do
    cmd="$(ps -p "$pid" -o command= 2>/dev/null || true)"
    ppid="$(ps -p "$pid" -o ppid= 2>/dev/null | tr -d ' ' || true)"
    pcmd="$(ps -p "${ppid:-1}" -o command= 2>/dev/null || true)"
    cwd="$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' || true)"
    if printf "%s" "$cmd" | grep -qF "$ROOT" || printf "%s" "$cwd" | grep -qF "$ROOT"; then
      # An old Virundhu process (uvicorn's helper processes don't show the folder in their command,
      # so we also check their working folder and their parent).
      if printf "%s" "$pcmd" | grep -qF "$ROOT"; then kill "$ppid" 2>/dev/null || true; fi
      kill "$pid" 2>/dev/null || true
    elif printf "%s" "$cmd" | grep -q "com.docker"; then
      docker compose stop backend worker frontend >/dev/null 2>&1 || true
    else
      fail "Port $port is used by another app:  $cmd
         Stop that app, or change the port in .env and start.sh."
    fi
  done
done
sleep 2
for port in $API_PORT $WEB_PORT; do
  lsof -ti "tcp:$port" -sTCP:LISTEN >/dev/null 2>&1 && fail "Port $port is still busy. Run:  kill \$(lsof -ti :$port)   then  bash start.sh  again."
done
ok "Ports are free"

# ---------- 4. Python environment ----------
say "4/6  Python packages"
if [ ! -x backend/.venv/bin/python ]; then
  command -v python3 >/dev/null || fail "Python 3 isn't installed. Install it with:  brew install python@3.12"
  python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' || fail "Python 3.11 or newer is needed. Install it with:  brew install python@3.12"
  echo "    Creating the virtual environment (first time only)..."
  python3 -m venv backend/.venv
fi
REQ_HASH="$(shasum backend/requirements.txt | cut -d' ' -f1)"
if [ "$(cat backend/.venv/.req-hash 2>/dev/null || true)" != "$REQ_HASH" ]; then
  echo "    Installing packages (1-2 minutes the first time)..."
  backend/.venv/bin/pip install -q --upgrade pip
  backend/.venv/bin/pip install -q -r backend/requirements.txt
  echo "$REQ_HASH" > backend/.venv/.req-hash
fi
ok "Python packages ready"
# Daily safety backup of the database (kept in ./backups, newest 30)
if [ -z "$(find backups -name 'virundhu-*.sql.gz' -mtime -1 2>/dev/null | head -1)" ]; then
  bash tools/backup/backup.sh >/dev/null 2>&1 && echo "    Database backed up to the backups folder." || echo "    (Backup skipped: run  bash tools/backup/backup.sh  to see why.)"
fi
(cd backend && .venv/bin/alembic upgrade head >/dev/null && .venv/bin/python -m app.seed >/dev/null) \
  || fail "Database setup failed. Run  cd backend && .venv/bin/alembic upgrade head  to see why."
ok "Tables and admin login are ready"

# ---------- 5. Website packages ----------
say "5/6  Website packages"
if [ ! -d frontend/node_modules ] || [ frontend/package-lock.json -nt frontend/node_modules/.package-lock.json ]; then
  command -v npm >/dev/null || fail "Node.js isn't installed. Install it with:  brew install node"
  echo "    Installing website packages (first time only)..."
  (cd frontend && npm install --silent)
fi
ok "Website packages ready"

# ---------- 6. Start everything ----------
say "6/6  Starting Virundhu"
prefix() { while IFS= read -r line; do printf "%s %s\n" "$1" "$line"; done; }
cleanup() {
  trap - INT TERM
  printf "\n\033[1;33m==>\033[0m Stopping Virundhu (the database keeps running; use  bash stop.sh  to stop it too)\n"
  kill 0 2>/dev/null || true
}
trap cleanup INT TERM

(cd backend && exec .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port $API_PORT 2>&1) | prefix "[api]   " &
(cd backend && exec .venv/bin/arq app.worker.settings.WorkerSettings 2>&1) | prefix "[worker]" &
(cd frontend && exec npm run dev -- --host 2>&1) | prefix "[web]   " &

for _ in $(seq 1 40); do curl -fs "http://localhost:$API_PORT/health" >/dev/null 2>&1 && break; sleep 1; done
for _ in $(seq 1 40); do curl -fs "http://localhost:$WEB_PORT" >/dev/null 2>&1 && break; sleep 1; done

LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || true)"
printf "\n\033[1;32m  Virundhu is running\033[0m\n"
printf "  ----------------------------------------------------\n"
printf "  Website       http://localhost:%s\n" "$WEB_PORT"
[ -n "$LAN_IP" ] && printf "  On your phone http://%s:%s   (same Wi-Fi)\n" "$LAN_IP" "$WEB_PORT"
printf "  API health    http://localhost:%s/health\n" "$API_PORT"
printf "  Admin login   %s  /  %s\n" "$(grep '^SUPERADMIN_EMAIL=' .env | cut -d= -f2)" "$(grep '^SUPERADMIN_PASSWORD=' .env | cut -d= -f2)"
printf "  New owner     click \"Start free trial\" (use a private window)\n"
printf "  Stop          press Ctrl + C\n"
printf "  ----------------------------------------------------\n\n"
open "http://localhost:$WEB_PORT" 2>/dev/null || true
wait
