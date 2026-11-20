#!/usr/bin/env bash
# Switches Virundhu's payments from Dodo test mode to live mode (real money). No secrets here: paste the live API key
# and webhook key afterwards with:  KEYS="DODO_PAYMENTS_API_KEY DODO_PAYMENTS_WEBHOOK_KEY" bash set-keys.sh
# Usage: bash dodo-live.sh <live product id>      (back to test mode: bash dodo-live.sh --test <test product id>)
set -euo pipefail
ENV=/opt/virundhu/.env
set_kv() { if grep -q "^$1=" "$ENV"; then sed -i "s|^$1=.*|$1=$2|" "$ENV"; else echo "$1=$2" >> "$ENV"; fi; }
MODE=live_mode
if [ "${1:-}" = "--test" ]; then MODE=test_mode; shift; fi
PRODUCT="${1:?Give the Dodo product id, e.g. pdt_...}"
set_kv PAYMENT_PROVIDER dodo
set_kv DODO_PAYMENTS_ENVIRONMENT "$MODE"
set_kv DODO_PRODUCT_FLEX "$PRODUCT"
chmod 600 "$ENV"
cd /opt/virundhu/deploy/vps && docker compose up -d --force-recreate api worker >/dev/null 2>&1
echo "Payments now in $MODE with product $PRODUCT. Keys set: $(grep -c '^DODO_PAYMENTS_API_KEY=.\+' "$ENV") API, $(grep -c '^DODO_PAYMENTS_WEBHOOK_KEY=.\+' "$ENV") webhook."
