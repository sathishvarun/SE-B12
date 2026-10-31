#!/usr/bin/env bash
# =============================================================================
#  Put the Help Desk on your own domain through the Traefik that already runs
#  on this VPS (Hostinger Docker / n8n style setups). Free HTTPS included.
#
#  Run INSIDE the project folder on the VPS:
#      bash deploy/connect_domain_traefik.sh helpdesk.sathishsakthivel.tech
#
#  What it does (other apps are NOT touched):
#    1. reads how your Traefik is configured (network, entrypoint, certificate resolver)
#    2. builds the Help Desk as a Docker image
#    3. runs it as container "smart-helpdesk" with Traefik labels for your domain
#       (also reachable on http://SERVER_IP:<free port, e.g. 8510>)
#    4. stops the old non-Docker service so only one copy runs
#  Safe to run again after you copy new code.
# =============================================================================
set -euo pipefail

DOMAIN="${1:-}"
[ -z "$DOMAIN" ] && { echo "Usage: bash deploy/connect_domain_traefik.sh helpdesk.yourdomain.com"; exit 1; }
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME=smart-helpdesk
cd "$APP_DIR"

step() { echo; echo "==> $*"; }
port_busy() { ss -tlnH "( sport = :$1 )" 2>/dev/null | grep -q LISTEN; }
all_labels() {   # every Traefik label on every running container (except ours)
  docker ps -q | while read -r id; do
    n="$(docker inspect -f '{{.Name}}' "$id")"
    [ "$n" = "/$NAME" ] && continue
    docker inspect -f '{{range $k,$v := .Config.Labels}}{{$k}}={{$v}}{{"\n"}}{{end}}' "$id"
  done | grep '^traefik\.' || true
}

step "1/5  Finding Traefik"
TRAEFIK="$(docker ps --format '{{.Names}} {{.Image}}' | awk 'tolower($2) ~ /traefik/ {print $1; exit}')"
[ -z "$TRAEFIK" ] && { echo "No running Traefik container found. Use deploy/setup_vps.sh instead."; exit 1; }
ARGS="$(docker inspect -f '{{join .Config.Cmd "\n"}}{{"\n"}}{{join .Args "\n"}}' "$TRAEFIK" 2>/dev/null || true)"
LABELS="$(all_labels)"

# Certificate resolver: copy what your working apps use, else read Traefik's own settings.
RESOLVER="$(printf '%s\n' "$LABELS" | sed -n 's/.*\.tls\.certresolver=//p' | head -1)"
[ -z "$RESOLVER" ] && RESOLVER="$(printf '%s\n' "$ARGS" | sed -n 's/^--certificatesresolvers\.\([^.]*\)\..*/\1/p' | head -1)"

# HTTPS entrypoint: the one listening on :443, else the one other apps use with TLS.
EP_SECURE="$(printf '%s\n' "$ARGS" | sed -n 's/^--entrypoints\.\([^.]*\)\.address=:443$/\1/p' | head -1)"
[ -z "$EP_SECURE" ] && EP_SECURE="$(printf '%s\n' "$LABELS" | sed -n 's/.*\.entrypoints=//p' | tr ',' '\n' | grep -iE 'secure|https|443' | head -1)"
[ -z "$EP_SECURE" ] && EP_SECURE=websecure
EP_WEB="$(printf '%s\n' "$ARGS" | sed -n 's/^--entrypoints\.\([^.]*\)\.address=:80$/\1/p' | head -1)"
[ -z "$EP_WEB" ] && EP_WEB=web

# Network: one Traefik is attached to (prefer a non-default one).
NETWORK="$(docker inspect -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{"\n"}}{{end}}' "$TRAEFIK" | grep -v '^$' | grep -vx 'bridge' | head -1)"
[ -z "$NETWORK" ] && NETWORK=bridge

echo "    Traefik container : $TRAEFIK"
echo "    Docker network    : $NETWORK"
echo "    HTTPS entrypoint  : $EP_SECURE   (HTTP entrypoint: $EP_WEB)"
echo "    Certificate       : ${RESOLVER:-none found - HTTPS will use the Traefik default certificate}"

step "2/5  Checking .env"
[ -f .env ] || { cp .env.example .env; echo "    Created .env - add your OPENAI_API_KEY:  nano $APP_DIR/.env   then run again."; exit 0; }
mkdir -p logs

step "3/5  Building the Help Desk image (first time takes 2-4 minutes)"
docker build -q -t $NAME:latest . >/dev/null
echo "    Image built."

step "4/5  Starting the container with Traefik labels for $DOMAIN"
# Stop the older non-Docker version (systemd) if it exists, so only one copy runs.
if systemctl list-unit-files 2>/dev/null | grep -q "^$NAME.service"; then
  systemctl disable --now $NAME >/dev/null 2>&1 || true
  echo "    Stopped the old non-Docker service."
fi
# Re-use the port from an earlier run, otherwise pick the first free port from 8510 up
# (8501/8502 etc. are often used by other Streamlit apps on the same server).
OLD_PORT="$(docker port $NAME 8501/tcp 2>/dev/null | head -1 | sed 's/.*://' || true)"
docker rm -f $NAME >/dev/null 2>&1 || true
if [ -n "${HOST_PORT:-}" ]; then :
elif [ -n "$OLD_PORT" ] && ! port_busy "$OLD_PORT"; then HOST_PORT="$OLD_PORT"
else HOST_PORT=8510; while port_busy "$HOST_PORT"; do HOST_PORT=$((HOST_PORT + 1)); done
fi
echo "    Direct port for this app: $HOST_PORT"

TLS_LABELS=(--label "traefik.http.routers.$NAME.tls=true")
[ -n "$RESOLVER" ] && TLS_LABELS+=(--label "traefik.http.routers.$NAME.tls.certresolver=$RESOLVER")

docker run -d --name $NAME --restart unless-stopped \
  --network "$NETWORK" \
  -p "$HOST_PORT:8501" \
  -e TZ=Asia/Kolkata \
  -v "$APP_DIR/.env:/app/.env:ro" \
  -v "$APP_DIR/logs:/app/logs" \
  -v "$APP_DIR/knowledge_base:/app/knowledge_base:ro" \
  --label "traefik.enable=true" \
  --label "traefik.docker.network=$NETWORK" \
  --label "traefik.http.services.$NAME.loadbalancer.server.port=8501" \
  --label "traefik.http.routers.$NAME.rule=Host(\`$DOMAIN\`)" \
  --label "traefik.http.routers.$NAME.entrypoints=$EP_SECURE" \
  "${TLS_LABELS[@]}" \
  --label "traefik.http.routers.$NAME-http.rule=Host(\`$DOMAIN\`)" \
  --label "traefik.http.routers.$NAME-http.entrypoints=$EP_WEB" \
  --label "traefik.http.routers.$NAME-http.middlewares=$NAME-https" \
  --label "traefik.http.middlewares.$NAME-https.redirectscheme.scheme=https" \
  $NAME:latest >/dev/null
echo "    Container started."

step "5/5  Checking it works"
ok=""
for _ in $(seq 1 30); do
  sleep 2
  if curl -s --max-time 3 "http://127.0.0.1:$HOST_PORT/_stcore/health" | grep -q ok; then ok=1; break; fi
done
if [ -z "$ok" ]; then
  echo "The app did not start. Last log lines:"; docker logs --tail 40 $NAME; exit 1
fi
CODE="000"
for _ in $(seq 1 20); do   # Traefik may need a few seconds to get the certificate
  CODE="$(curl -sk -o /dev/null -w '%{http_code}' --max-time 5 --resolve "$DOMAIN:443:127.0.0.1" "https://$DOMAIN/_stcore/health" || true)"
  [ "$CODE" = "200" ] && break
  sleep 3
done
IP="$(curl -4 -s --max-time 5 https://api.ipify.org || hostname -I | awk '{print $1}')"
echo
echo "============================================================"
if [ "$CODE" = "200" ]; then
  echo "  DONE - the Help Desk is live:   https://$DOMAIN"
else
  echo "  The app is running, but Traefik did not answer for $DOMAIN yet (HTTP $CODE)."
  echo "  Wait 1-2 minutes (certificate + DNS) and open https://$DOMAIN"
  echo "  If it still shows another site:  docker logs --tail 50 $TRAEFIK"
fi
echo "  Also available at:               http://$IP:$HOST_PORT"
echo
echo "  Useful commands:"
echo "     docker logs -f $NAME          # live logs (Ctrl+C to exit)"
echo "     docker restart $NAME          # restart after editing .env"
echo "     bash deploy/connect_domain_traefik.sh $DOMAIN   # after copying new code"
echo "============================================================"
