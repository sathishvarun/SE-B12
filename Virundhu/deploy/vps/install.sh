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
mkdir -p "$APP"
rsync -a --delete --exclude .env --exclude deploy/vps/.env "$SRC/Virundhu/" "$APP/"
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
docker image prune -f >/dev/null
echo "Virundhu is starting at https://$DOMAIN"
