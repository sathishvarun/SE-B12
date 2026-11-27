#!/usr/bin/env bash
# Daily database backup on the VPS (cron runs it at 03:00 India time). Compressed; keeps the newest 30 days.
set -euo pipefail
dir=/opt/virundhu/backups; mkdir -p "$dir"; chmod 700 "$dir"
name="$dir/virundhu-$(date +%Y-%m-%d-%H%M).sql.gz"
docker exec virundhu-db-1 pg_dump -U virundhu --no-owner virundhu | gzip -9 > "$name.part"
mv "$name.part" "$name"; chmod 600 "$name"
# Only the app (to show backups in the admin console) and root can read them
uid=$(docker exec virundhu-api-1 id -u 2>/dev/null || echo 1000); chown -R "$uid" "$dir"
find "$dir" -name 'virundhu-*.sql.gz' -mtime +30 -delete
echo "$(date '+%F %T') backup saved: $name ($(du -h "$name" | cut -f1))"
# Off the server, so a lost VPS doesn't take the backups with it:
# 1) encrypted copy emailed to the admin (needs BACKUP_PASSPHRASE in /opt/virundhu/.env)
docker exec virundhu-api-1 python -m app.tools.offsite_backup send 2>&1 | tail -1 || echo "off-server email copy failed"
# 2) optional: any cloud folder through rclone (Google Drive, S3, ...): BACKUP_RCLONE_REMOTE=gdrive:virundhu-backups
remote=$(grep -s '^BACKUP_RCLONE_REMOTE=' /opt/virundhu/deploy/vps/.env | cut -d= -f2- || true)
if [ -n "${remote:-}" ] && command -v rclone >/dev/null; then
  rclone copy "$name" "$remote" && echo "copied to $remote" || echo "rclone copy failed"
fi
