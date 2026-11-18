#!/bin/bash
# Back up the Virundhu database to the "backups" folder next to this project. Keeps the newest 30.
#   Run any time:   bash tools/backup/backup.sh
#   Restore one:    bash tools/backup/restore.sh backups/virundhu-2026-11-17-0710.sql.gz
# start.sh runs this once a day automatically. On the VPS, add it to cron (see LAUNCH_GUIDE.md).
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p backups
name="backups/virundhu-$(date +%Y-%m-%d-%H%M).sql.gz"
docker compose exec -T db pg_dump -U virundhu --no-owner virundhu | gzip > "$name.part"
mv "$name.part" "$name"
ls -1t backups/virundhu-*.sql.gz | tail -n +31 | xargs -r rm -f
echo "Backup saved: $name ($(du -h "$name" | cut -f1))"
