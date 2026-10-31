#!/usr/bin/env bash
# =============================================================================
#  SK Soft Technology Help Desk - one-time VPS setup (Ubuntu 22.04 / 24.04)
#
#  Run INSIDE the project folder on the VPS:
#      bash deploy/setup_vps.sh                 # use the VPS IP address
#      bash deploy/setup_vps.sh helpdesk.com    # or your domain name
#
#  It never touches other apps on the server:
#   - if port 80 is free     -> installs Nginx and serves the app on http://IP
#   - if port 80 is taken    -> (e.g. Traefik / Docker / Apache) skips Nginx and
#                               serves the app directly on a free port: http://IP:8510
#  Safe to run again after you copy new code - it simply updates and restarts.
# =============================================================================
set -euo pipefail

DOMAIN="${1:-_}"                                   # "_" = answer on the IP address
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_USER="$(whoami)"
SERVICE=smart-helpdesk
SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"

step() { echo; echo "==> $*"; }
port_owner() { $SUDO ss -tlnpH "( sport = :$1 )" 2>/dev/null | grep -o 'users:(("[^"]*' | head -1 | cut -d'"' -f2; }

# ---- Decide how to publish the app ------------------------------------------
OWNER80="$(port_owner 80 || true)"
if [ -z "$OWNER80" ] || [ "$OWNER80" = "nginx" ]; then
  MODE=nginx
else
  MODE=direct
fi
# Our own service may already hold a port from an earlier run: reuse it.
CURRENT_PORT="$(grep -o 'server.port=[0-9]*' /etc/systemd/system/$SERVICE.service 2>/dev/null | cut -d= -f2 || true)"
if [ -n "${PORT:-}" ]; then
  :                                               # user chose a port: PORT=8600 bash ...
elif [ -n "$CURRENT_PORT" ]; then
  PORT="$CURRENT_PORT"
else
  PORT=8510
  while [ -n "$(port_owner "$PORT" || true)" ]; do PORT=$((PORT + 1)); done
fi
echo "Port 80 is used by: ${OWNER80:-nothing}  ->  mode: $MODE, app port: $PORT"

step "1/5  Installing Python and tools"
$SUDO apt-get update -y
PKGS="python3 python3-venv python3-pip curl"
[ "$MODE" = nginx ] && PKGS="$PKGS nginx"
# shellcheck disable=SC2086
$SUDO apt-get install -y $PKGS
python3 -c 'import sys; assert sys.version_info >= (3, 10), "Python 3.10+ needed"' \
  || { echo "This VPS has Python older than 3.10. Use Ubuntu 22.04 or newer."; exit 1; }

step "2/5  Creating the virtual environment and installing packages"
cd "$APP_DIR"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q
mkdir -p logs

step "3/5  Checking the .env file"
if [ ! -f .env ]; then
  cp .env.example .env
  echo "    Created .env from .env.example."
  echo "    >>> Open it now:  nano $APP_DIR/.env   (add OPENAI_API_KEY), then run this script again."
  exit 0
fi
grep -qE '^OPENAI_API_KEY=["'\'']?sk-' .env && ! grep -q 'your-key-here' .env \
  || echo "    WARNING: OPENAI_API_KEY in .env looks empty - the app will open but cannot answer."
grep -q '^APP_PASSWORD=..*' .env \
  || echo "    Note: APP_PASSWORD is empty, so the app opens without a password."

step "4/5  Running the app as a background service (auto-restart, starts on boot)"
if [ "$MODE" = nginx ]; then ADDRESS=127.0.0.1; else ADDRESS=0.0.0.0; fi
$SUDO tee /etc/systemd/system/$SERVICE.service >/dev/null <<EOF
[Unit]
Description=SK Soft Technology Help Desk (AutoGen + Streamlit)
After=network.target

[Service]
User=$APP_USER
WorkingDirectory=$APP_DIR
Environment=TZ=Asia/Kolkata
ExecStart=$APP_DIR/.venv/bin/streamlit run app.py --server.address=$ADDRESS --server.port=$PORT --server.headless=true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
$SUDO systemctl daemon-reload
$SUDO systemctl enable $SERVICE >/dev/null
$SUDO systemctl restart $SERVICE

step "5/5  Making it reachable from the internet"
if [ "$MODE" = nginx ]; then
  $SUDO tee /etc/nginx/sites-available/helpdesk >/dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;
    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;     # Streamlit needs websockets
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 300;
    }
}
EOF
  $SUDO ln -sf /etc/nginx/sites-available/helpdesk /etc/nginx/sites-enabled/helpdesk
  $SUDO rm -f /etc/nginx/sites-enabled/default
  $SUDO nginx -t
  $SUDO systemctl reload nginx
  OPEN_RULE="Nginx Full"
else
  echo "    Port 80 belongs to '$OWNER80' - leaving it alone. The app is served directly on port $PORT."
  OPEN_RULE="$PORT/tcp"
fi
# Only add a rule if the firewall is already on - never switch it on (it could block other apps).
if command -v ufw >/dev/null && $SUDO ufw status | grep -q "Status: active"; then
  $SUDO ufw allow "$OPEN_RULE" >/dev/null && echo "    Firewall: allowed $OPEN_RULE"
fi

sleep 5
IP="$(curl -4 -s --max-time 5 https://api.ipify.org || hostname -I | awk '{print $1}')"
if [ "$MODE" = nginx ]; then URL="http://$IP"; else URL="http://$IP:$PORT"; fi
echo
if $SUDO systemctl is-active --quiet $SERVICE && curl -s --max-time 10 "http://127.0.0.1:$PORT/_stcore/health" | grep -q ok; then
  echo "============================================================"
  echo "  DONE - the Help Desk is live:   $URL"
  [ "$MODE" = nginx ] && [ "$DOMAIN" != "_" ] && echo "                                   http://$DOMAIN"
  [ "$MODE" = direct ] && echo "  (If it doesn't open, allow TCP port $PORT in your VPS provider's firewall.)"
  echo
  echo "  Useful commands:"
  echo "     systemctl status $SERVICE     # is it running?"
  echo "     journalctl -u $SERVICE -f     # live logs (Ctrl+C to exit)"
  echo "     systemctl restart $SERVICE    # restart after editing .env"
  [ "$MODE" = nginx ] && [ "$DOMAIN" != "_" ] && echo "     apt install -y certbot python3-certbot-nginx && certbot --nginx -d $DOMAIN   # free HTTPS"
  echo "============================================================"
else
  echo "The app did not start. Showing the last log lines:"
  $SUDO journalctl -u $SERVICE -n 40 --no-pager
  exit 1
fi
