#!/bin/sh
# Apply pending DB migrations, then exec the main process.
# Set RUN_MIGRATIONS=0 to skip (e.g. for one-off CLI tasks in the same image).
set -eu

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    echo "[entrypoint] Running 'alembic upgrade head'…"
    alembic upgrade head
fi

if [ -n "${SEED_ADMIN_ON_START:-}" ] && [ "$SEED_ADMIN_ON_START" = "1" ]; then
    echo "[entrypoint] Running 'flask seed-admin'…"
    flask seed-admin || true
fi

exec "$@"
