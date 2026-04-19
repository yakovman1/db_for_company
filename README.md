# Revit Families Backend (FastAPI)

Backend for ingesting Revit families (`.rfa`) to S3-compatible storage and persisting metadata in Postgres. Generates presigned URLs for upload/download and enforces per-project access with JWT.

## Stack
- FastAPI (Python 3.12)
- Postgres (async SQLAlchemy)
- MinIO / AWS S3 via boto3
- JWT auth stub (HS256)
- Structured logging (structlog)

## Quick start (Docker Compose)
```bash
cp env.example .env
docker-compose up --build
```
Services:
- API: http://localhost:8000
- Postgres: localhost:5432 (db/user/pass from `.env`)
- MinIO: http://localhost:9000 (console http://localhost:9001)

Compose auto-creates the bucket `${MINIO_BUCKET_FAMILIES}`.

## Environment
Key vars (see `env.example`):
- Database: `DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/families`
- MinIO only:
  - `MINIO_ENDPOINT` (compose: `http://minio:9000`, host: `http://localhost:9000`)
  - Credentials: `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, bucket `MINIO_BUCKET_FAMILIES`
  - Region/SSL: `MINIO_REGION` (default `us-east-1`), `MINIO_USE_SSL`
- Security: `JWT_SECRET`, `JWT_ALGORITHM`
- Presigned TTLs: `PRESIGNED_PUT_EXPIRES`, `PRESIGNED_GET_EXPIRES`
- Logging: `LOG_LEVEL`

## Migrations
- SQL in `migrations/001_init.sql` (manual apply example):
  ```bash
  psql "$DATABASE_URL" -f migrations/001_init.sql
  ```

## Auth model (stub)
- Expect `Authorization: Bearer <jwt>`.
- JWT claims: `sub` (UUID user id). Signature verified with `JWT_SECRET`.
- Project access is checked against `user_projects` table.

Generate a test token:
```bash
python - <<'PY'
import uuid, jwt, datetime
payload = {"sub": str(uuid.uuid4()), "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)}
print(jwt.encode(payload, "dev-secret-change", algorithm="HS256"))
PY
```

Seed a project/user link (psql inside container):
```bash
docker exec -it backend_family-postgres-1 psql -U families -d families \
  -c "insert into user_projects(user_id, project_id) values ('<USER_UUID>', '<PROJECT_UUID>') on conflict do nothing;"
```

## API (required endpoints)
- `POST /families/init-upload` → presigned PUT URL + `family_id`
- `POST /families/{family_id}/metadata` → save metadata, status→`parsed`
- `POST /families/{family_id}/complete` → mark uploaded/ready (optionally HEAD object)
- `GET /families/{family_id}` → family card + raw metadata
- `GET /families/{family_id}/download-url` → presigned GET URL
- `GET /projects/{project_id}/families` → list with pagination

### Sample flow (curl)
```bash
AUTH="Authorization: Bearer $TOKEN"

PROJECT_ID="<project-uuid>"
FILENAME="Door.rfa"

# 1) Init upload
curl -X POST http://localhost:8000/families/init-upload \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"project_id\":\"$PROJECT_ID\",\"original_filename\":\"$FILENAME\",\"sha256\":\"deadbeef\"}"

# Use presigned_put_url to upload directly to S3 (example with curl):
# curl -X PUT -T Door.rfa "https://..." -H "Content-Type: application/octet-stream"

# 2) Push metadata
curl -X POST http://localhost:8000/families/$FAMILY_ID/metadata \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d @metadata.json

# 3) Complete
curl -X POST http://localhost:8000/families/$FAMILY_ID/complete \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d "{}"

# 4) Download URL
curl -X GET http://localhost:8000/families/$FAMILY_ID/download-url -H "$AUTH"
```

`metadata.json` example:
```json
{
  "metadata": {
    "family_name": "Door Single",
    "category": "Doors",
    "parameters": [
      {"name": "Width", "is_instance": false, "storage_type": "double", "spec": "mm"},
      {"name": "Height", "is_instance": false, "storage_type": "double", "spec": "mm"}
    ],
    "types": [
      {"type_name": "900x2100", "values": {"Width": "900", "Height": "2100"}}
    ]
  }
}
```

## Data model (Postgres)
- `families`: UUID `id`, `project_id`, `status` (`initiated|uploaded|parsed|ready|failed`), `bucket`, `object_key`, `original_filename`, `sha256`, `size_bytes`, `metadata_json`, `etag`, timestamps.
- `family_parameters`: flattened parameter catalog for filtering.
- `family_type_values`: per-type parameter values (text).
- `user_projects`: mapping user → project for authorization.

## Dev without Docker
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export $(grep -v '^#' env.example | xargs)  # or create .env
uvicorn app.main:app --reload
```

## Notes
- Object key format: `projects/{project_id}/families/{family_id}/{sha256|sanitized_filename}.rfa`
- Presigned URLs are the only way to reach S3 objects; `bucket/object_key` are returned only after access checks.
- Metadata upserts overwrite previous values (idempotent).
- Minimal HEAD verification in `/families/{id}/complete` (best effort).

