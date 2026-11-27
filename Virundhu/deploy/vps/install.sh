#!/usr/bin/env bash
# One-command install / update of Virundhu on the VPS.
#   curl -fsSL https://raw.githubusercontent.com/sathishvarun/SE-B12/main/Virundhu/deploy/vps/install.sh | bash
# First run: makes /opt/virundhu/.env with fresh random secrets (never stored in Git).
# Later runs: pulls the newest code and restarts. Your .env and database are kept.
set -euo pipefail
command -v rsync >/dev/null && command -v git >/dev/null || { apt-get update -qq && apt-get install -y -qq rsync git >/dev/null; }
DOMAIN="${DOMAIN:-virundhu.sathishsakthivel.tech}"
SRC=/opt/virundhu-src; APP=/opt/virundhu
if [ -d "$SRC/.git" ]; then git -C "$SRC" fetch -q --depth 1 origin main && git -C "$SRC" reset -q --hard origin/main; else
  git clone -q --depth 1 --filter=blob:none --sparse https://github.com/sathishvarun/SE-B12 "$SRC"
  git -C "$SRC" sparse-checkout set Virundhu
fi
# Release gate: deploy only code whose tests passed on GitHub ("Virundhu tests": every test, including the
# attacker's-view security tests). Waits while the run is still going. FORCE_DEPLOY=1 skips it in an emergency.
SHA=$(git -C "$SRC" rev-parse HEAD)
if [ "${FORCE_DEPLOY:-0}" != "1" ]; then
  python3 - "$SHA" <<'PY' || { echo "Not deployed. Fix the failing tests (see GitHub > Actions), or FORCE_DEPLOY=1 in an emergency."; exit 1; }
import json, sys, time, urllib.request
sha, repo = sys.argv[1], "sathishvarun/SE-B12"
api = f"https://api.github.com/repos/{repo}/actions/workflows/virundhu-ci.yml/runs"
def get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "virundhu-deploy"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)["workflow_runs"]
for _ in range(60):  # up to 15 minutes
    runs = get(f"{api}?head_sha={sha}&per_page=5") or get(f"{api}?branch=main&status=completed&per_page=1")
    if not runs:
        print("Release gate: no test run found on GitHub yet; waiting..."); time.sleep(15); continue
    run = runs[0]
    if run["status"] != "completed":
        print(f"Release gate: tests still running for {run['head_sha'][:7]}; waiting..."); time.sleep(15); continue
    print(f"Release gate: tests {run['conclusion']} for {run['head_sha'][:7]} ({run['html_url']})")
    sys.exit(0 if run["conclusion"] == "success" else 1)
print("Release gate: gave up waiting for the tests"); sys.exit(1)
PY
fi
mkdir -p "$APP"
rsync -a --delete --exclude .env --exclude deploy/vps/.env --exclude backups --exclude logs "$SRC/Virundhu/" "$APP/"
cd "$APP"
rnd() { python3 -c "import secrets;print(secrets.token_urlsafe($1))"; }
if [ ! -f .env ]; then
  PG=$(rnd 24); ADMINPW=$(rnd 15)
  cp .env.example .env
  set_kv() { if grep -q "^$1=" .env; then sed -i "s|^$1=.*|$1=$2|" .env; else echo "$1=$2" >> .env; fi; }
  set_kv APP_ENV production
  set_kv APP_URL "https://$DOMAIN"
  set_kv API_URL "https://$DOMAIN"
  set_kv DATABASE_URL "postgresql+psycopg2://virundhu:$PG@db:5432/virundhu"
  set_kv REDIS_URL "redis://redis:6379/0"
  set_kv SECRET_KEY "$(rnd 48)"
  set_kv SUPERADMIN_EMAIL "admin@$DOMAIN"
  set_kv SUPERADMIN_PASSWORD "$ADMINPW"
  set_kv DEMO_PASSWORD "$(rnd 18)"
  set_kv GOOGLE_REDIRECT_URI "https://$DOMAIN/api/v1/auth/google/callback"
  set_kv VITE_API_URL ""
  printf 'POSTGRES_PASSWORD=%s\nDOMAIN=%s\n' "$PG" "$DOMAIN" > deploy/vps/.env
  umask 077; printf 'Admin email: admin@%s\nAdmin password: %s\nChange it after the first sign-in (Admin console > Change my password).\n' "$DOMAIN" "$ADMINPW" > /root/virundhu-admin.txt
  chmod 600 .env deploy/vps/.env /root/virundhu-admin.txt
  echo "Created .env. Admin login saved in /root/virundhu-admin.txt"
fi
cd deploy/vps
docker compose up -d --build
# Daily backup at 03:00 India time (21:30 UTC), one now if none exists yet
echo "30 21 * * * root bash /opt/virundhu/deploy/vps/backup.sh >> /opt/virundhu/backups/backup.log 2>&1" > /etc/cron.d/virundhu-backup
chmod 644 /etc/cron.d/virundhu-backup
ls /opt/virundhu/backups/virundhu-*.sql.gz >/dev/null 2>&1 || bash /opt/virundhu/deploy/vps/backup.sh
docker image prune -f >/dev/null
echo "Virundhu is starting at https://$DOMAIN"
