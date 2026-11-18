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
