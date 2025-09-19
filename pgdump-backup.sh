#!/usr/bin/env bash
set -euo pipefail

# Cron: 0 0 * * 1,3,5 user /opt/pg/backup-handler/pgdump-backup.sh
# config.ini:
#[backup]
#source_dir = /opt/pg/backup-handler/sql_files
#backup_dir = /opt/pg/backup-handler/files
#backup_name = pg
#
#[pgdump]
#container = pg-db
#user = postgres
#backup_password = VerySecurePassword
#post_cmd=/opt/pg/backup-handler/.venv/bin/python /opt/pg/backup-handler/backup.py




SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/config.ini"

parse_ini() {
    local section=$1 key=$2 file=$3
    awk -F '=' -v section="$section" -v key="$key" '
    $0 ~ "\\["section"\\]" { in_section=1; next }
    /^\[.*\]/ { in_section=0 }
    in_section && $1 ~ key { gsub(/^[ \t]+|[ \t]+$/,"",$2); print $2 }
    ' "$file"
}

SOURCE_DIR=$(parse_ini backup source_dir "$CONFIG_FILE")
BACKUP_DIR=$(parse_ini backup backup_dir "$CONFIG_FILE")
BACKUP_NAME=$(parse_ini backup backup_name "$CONFIG_FILE")
CONTAINER=$(parse_ini pgdump container "$CONFIG_FILE")
DB_USER=$(parse_ini pgdump user "$CONFIG_FILE")
BACKUP_PASS=$(parse_ini pgdump backup_password "$CONFIG_FILE")
POST_CMD=$(parse_ini pgdump post_cmd "$CONFIG_FILE")

TIMESTAMP="$(date +%Y%m%d_%H%M)"
SQL_FILE="${SOURCE_DIR}/${BACKUP_NAME}_${TIMESTAMP}.sql"
OUTFILE="${SOURCE_DIR}/${BACKUP_NAME}_${TIMESTAMP}.7z"

for cmd in docker 7z; do
  command -v $cmd >/dev/null 2>&1 || { echo "$cmd not found"; exit 1; }
done

mkdir -p "$SOURCE_DIR" || err "Error mkdir $SOURCE_DIR"
rm -rf ${SOURCE_DIR}/*
docker exec -i "$CONTAINER" pg_dumpall -U "$DB_USER" > "$SQL_FILE"
7z a -p"$BACKUP_PASS" -mhe=on "$OUTFILE" "$SQL_FILE" >/dev/null
chmod 600 "$OUTFILE"
rm -f "$SQL_FILE"
echo "$OUTFILE"

eval "$POST_CMD"
rm -rf $OUTFILE
