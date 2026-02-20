#!/bin/bash
set -euo pipefail

# --- настройки БД ---
DB_NAME="ATPTLP_1"
DB_USER="admin"

# --- пути ---
BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="${BASE_DIR}/backups"

DATE="$(date +'%Y-%m-%d_%H-%M')"
FILENAME="backup_${DATE}.sql"
TMP_FILE="${BACKUP_DIR}/${FILENAME}.tmp"

echo "[*] Create backup: ${FILENAME}"

mkdir -p "${BACKUP_DIR}"

docker exec company_postgres pg_dump \
  -U "${DB_USER}" \
  -d "${DB_NAME}" \
  -F p \
  > "${TMP_FILE}"

mv "${TMP_FILE}" "${BACKUP_DIR}/${FILENAME}"

echo "[+] Backup saved to ${BACKUP_DIR}/${FILENAME}"
