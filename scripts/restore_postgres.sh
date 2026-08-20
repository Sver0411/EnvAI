#!/usr/bin/env bash
set -Eeuo pipefail

: "${BACKUP_FILE:?BACKUP_FILE is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
if [[ "${CONFIRM_RESTORE:-}" != "YES" ]]; then
  echo "Refusing restore. Set CONFIRM_RESTORE=YES and use an isolated target database." >&2
  exit 2
fi
test -s "$BACKUP_FILE"
if [[ -f "$BACKUP_FILE.sha256" ]]; then sha256sum -c "$BACKUP_FILE.sha256"; fi
DB_SERVICE="${DB_SERVICE:-postgres}"
docker compose exec -T "$DB_SERVICE" pg_restore --clean --if-exists --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$BACKUP_FILE"
echo "restore completed"
