#!/usr/bin/env bash
# Switches on email (password reset, welcome, alerts) using a Gmail App password. Typing the password is hidden.
set -euo pipefail
ENV=/opt/virundhu/.env
set_kv() { if grep -q "^$1=" "$ENV"; then sed -i "s|^$1=.*|$1=$2|" "$ENV"; else echo "$1=$2" >> "$ENV"; fi; }
read -rp "Gmail address that sends Virundhu emails: " mail
read -rsp "Paste the 16-letter Gmail App password (hidden) and press Enter: " pw; echo
pw="${pw// /}"
[ -n "$mail" ] && [ ${#pw} -ge 16 ] || { echo "Gmail address or App password missing. Nothing changed."; exit 1; }
set_kv SMTP_HOST smtp.gmail.com
set_kv SMTP_PORT 587
set_kv SMTP_USER "$mail"
set_kv SMTP_PASSWORD "$pw"
set_kv EMAIL_FROM "\"Virundhu <$mail>\""
set_kv CONTACT_EMAIL "$mail"
chmod 600 "$ENV"
cd /opt/virundhu/deploy/vps && docker compose up -d --force-recreate api worker >/dev/null 2>&1
sleep 8
docker exec virundhu-api-1 python -c "
from app.services.emailer import send_email
ok = send_email(['$mail'], 'Virundhu email is working', 'Hi,\n\nThis test email shows Virundhu can send password-reset links, welcome emails and alerts.\n')
print('Test email sent to $mail' if ok else 'Sending failed: check the App password and try again.')"
