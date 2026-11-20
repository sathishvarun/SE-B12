#!/usr/bin/env bash
# Asks for each secret key (typing is hidden), saves it in /opt/virundhu/.env and restarts Virundhu.
# Press Enter without pasting to keep the current value. Only some keys: KEYS="DODO_PAYMENTS_API_KEY DODO_PAYMENTS_WEBHOOK_KEY" bash set-keys.sh
set -euo pipefail
ENV=/opt/virundhu/.env
set_kv() { if grep -q "^$1=" "$ENV"; then sed -i "s|^$1=.*|$1=$2|" "$ENV"; else echo "$1=$2" >> "$ENV"; fi; }
for k in ${KEYS:-OPENAI_API_KEY GOOGLE_CLIENT_SECRET DODO_PAYMENTS_API_KEY DODO_PAYMENTS_WEBHOOK_KEY}; do
  read -rsp "Paste $k (hidden) and press Enter: " v; echo
  if [ -n "$v" ]; then set_kv "$k" "$v"; echo "  saved"; else echo "  kept as it was"; fi
done
chmod 600 "$ENV"
cd /opt/virundhu/deploy/vps && docker compose up -d --force-recreate api worker >/dev/null 2>&1
echo "Done. Virundhu restarted with your keys."
