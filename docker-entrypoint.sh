#!/bin/sh
# Entrypoint: run DB migrations (idempotent), then execute the given command.
set -e

# Ensure the uploads directory exists inside the data volume
mkdir -p "$UPLOAD_DIR"

# Apply any pending Alembic migrations (safe to run on every start)
alembic upgrade head

# Hand off to the container command (e.g. kn0 ingest, kn0 entities, …)
exec "$@"
