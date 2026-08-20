#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE_DIR="${SOURCE_DIR:-uploads}"
BACKUP_DIR="${BACKUP_DIR:-backups/storage}"
mkdir -p "$BACKUP_DIR"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
output="$BACKUP_DIR/envai_storage_${stamp}.tar.gz"
tar -C "$SOURCE_DIR" -czf "$output" .
test -s "$output"
sha256sum "$output" > "$output.sha256"
echo "backup=$output checksum=$(cut -d' ' -f1 "$output.sha256")"
