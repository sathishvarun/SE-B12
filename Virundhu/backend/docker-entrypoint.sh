#!/bin/sh
# Apply migrations and seed once (API container only), then start the given command.
set -e
if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  echo "Applying database migrations..."
  alembic upgrade head
  python -m app.seed
fi
exec "$@"
