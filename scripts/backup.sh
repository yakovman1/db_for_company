#!/bin/bash

DATE=$(date +"%Y-%m-%d_%H-%M")
BACKUP_DIR="./backups"
FILENAME="backup_${DATE}.sql"

echo "[*] Create backup: $FILENAME"

docker exec company_postgres pd_dump \
  -U $POSTGRES_USER \
  -d $POSTGRES_DB \
  -F p \
  > "${BACKUP_DIR}/${FILENAME}"

echo "[+] Ready: "${BACKUP_DIR}/${FILENAME}"