#!/bin/bash
# Put a backup back into the database. This REPLACES everything currently in it.
#   bash tools/backup/restore.sh backups/virundhu-2026-11-17-0710.sql.gz
set -euo pipefail
cd "$(dirname "$0")/../.."
file="${1:?Give the backup file, for example backups/virundhu-2026-11-17-0710.sql.gz}"
[ -f "$file" ] || { echo "No such file: $file"; exit 1; }
read -r -p "This replaces ALL current data with $file. Type RESTORE to continue: " ok
[ "$ok" = "RESTORE" ] || { echo "Cancelled."; exit 1; }
bash tools/backup/backup.sh  # safety copy of what's there now
docker compose exec -T db psql -U virundhu -d postgres -c "DROP DATABASE IF EXISTS virundhu WITH (FORCE);" -c "CREATE DATABASE virundhu OWNER virundhu;"
gunzip -c "$file" | docker compose exec -T db psql -q -U virundhu -d virundhu
echo "Restored from $file. Restart the app:  ./start.sh"
