#!/usr/bin/env bash
set -Eeuo pipefail

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
BACKUP_DIR="${BACKUP_DIR:-backups/postgres}"
DB_SERVICE="${DB_SERVICE:-postgres}"
mkdir -p "$BACKUP_DIR"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
output="$BACKUP_DIR/envai_${stamp}.dump"
docker compose exec -T "$DB_SERVICE" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$output"
test -s "$output"
sha256sum "$output" > "$output.sha256"
docker compose exec -T "$DB_SERVICE" pg_restore --list < "$output" >/dev/null
echo "backup=$output checksum=$(cut -d' ' -f1 "$output.sha256")"
