# Revit Families Backend (FastAPI)

Backend для Revit-плагинов: загрузка семейств (`.rfa`) в S3, метаданные в Postgres, синхронизация отверстий, приём BIMdata export.

**Контракт API:** `docs/api_spec.md` (rev 4)

## Stack

- FastAPI 0.110 (Python 3.12)
- Postgres 16 (async SQLAlchemy + asyncpg)
- MinIO / AWS S3 (boto3, presigned URL)
- JWT (python-jose, HS256)
- structlog (JSON)

## Quick start (Docker Compose)

```bash
cp env.example .env
docker-compose up --build backend postgres minio minio-create-buckets
```

| Сервис | URL |
|--------|-----|
| API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| Postgres | localhost:5432 |
| MinIO | http://localhost:9000 (console :9001) |

Compose создаёт bucket `${MINIO_BUCKET_FAMILIES}`.

## Environment

См. `env.example`:

| Группа | Переменные |
|--------|------------|
| Database | `DATABASE_URL` |
| MinIO | `MINIO_ENDPOINT`, `MINIO_PUBLIC_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET_FAMILIES`, `MINIO_REGION`, `MINIO_USE_SSL` |
| JWT | `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRES_SECONDS` |
| Presigned TTL | `PRESIGNED_PUT_EXPIRES` (900), `PRESIGNED_GET_EXPIRES` (300) |
| Logging | `LOG_LEVEL` |

## Migrations

SQL в `backet/migrations/` — применяются **вручную**:

```bash
docker exec -it company_postgres psql -U families -d families -f /path/to/001_init.sql
```

| Файл | Схема |
|------|-------|
| `001_init.sql` | `ATPTLP_familymanager` — families, parameters, user_projects |
| `002_openings.sql` | `ATPTLP_openmodels` — openings, opening_history |
| `003_companies.sql` | `atptlp_info` — companies, company_users |
| `004_openings_content_hash.sql` | колонка `content_hash` |
| `011_bimdata.sql` | `stg_bim` — model_snapshots, mep_elements |
| `012_bimdata_mep_elements_snapshot_date.sql` | колонка `mep_elements.snapshot_date` (если 011 уже применена без неё) |

## Auth

### Plugin (FamilyMang, Openings, BIMdata)

```http
POST /api/v1/auth
{"companyId": "MY_COMPANY", "windowsUser": "PDE"}
→ {"accessToken": "...", "expiresIn": 28800}
```

JWT claims: `company_id`, `windows_user`.

Проверки: компания в `atptlp_info.companies` (`is_active`), whitelist в `company_users` (если не пуст).

### Families — project_id

Каталог компании: `families.project_id = companies.id` (UUID PK). Клиент Project ID **не передаёт**.

## API — Families (FamilyMang)

Префикс `/families` (без `/api/v1`). Auth: Plugin JWT.

| Method | Path | Описание |
|--------|------|----------|
| GET | `/families?limit=&offset=` | Список семейств компании |
| POST | `/families/init-upload` | Presigned PUT URL (без `project_id` в body) |
| POST | `/families/{id}/metadata` | Метаданные → status `parsed` |
| POST | `/families/{id}/complete` | S3 HEAD → status `ready` / `uploaded` |
| GET | `/families/{id}` | Карточка семейства |
| GET | `/families/{id}/download-url` | Presigned GET URL |

Legacy: `GET /projects/{project_id}/families` — только если `project_id == companies.id`.

### Upload flow

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth \
  -H "Content-Type: application/json" \
  -d '{"companyId":"MY_COMPANY","windowsUser":"PDE"}' | jq -r .accessToken)

AUTH="Authorization: Bearer $TOKEN"

curl -X POST http://localhost:8000/families/init-upload \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"original_filename":"Door.rfa","sha256":"deadbeef12345678"}'
# → presigned_put_url, family_id

# PUT .rfa на presigned_put_url (без Authorization)

curl -X POST http://localhost:8000/families/$FAMILY_ID/metadata \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"metadata":{"family_name":"Door","category":"Doors","parameters":[],"types":[],"extra":{}}}'

curl -X POST http://localhost:8000/families/$FAMILY_ID/complete \
  -H "$AUTH" -H "Content-Type: application/json" -d '{}'
```

## API — Openings (Revit plugin)

Префикс `/api/v1/openings`. Auth: Plugin JWT.

| Method | Path | Описание |
|--------|------|----------|
| POST | `/api/v1/openings/sync` | Upsert / soft-delete отверстий |
| GET | `/api/v1/openings?modelGuid=` | Список отверстий модели |

## API — BIMdata (Revit plugin)

Префикс `/api/v1/bimdata`. Auth: Plugin JWT. Контракт: `docs/api_spec.md`.

| Method | Path | Описание |
|--------|------|----------|
| POST | `/api/v1/bimdata/snapshots` | Создать export session |
| POST | `/api/v1/bimdata/snapshots/{snapshotId}/elements:batch` | Batch MEP elements |
| POST | `/api/v1/bimdata/snapshots/{snapshotId}:complete` | Завершить export |
| POST | `/api/v1/bimdata/snapshots/{snapshotId}:fail` | Пометить export failed |

Данные пишутся в Postgres schema `stg_bim`. Аналитика — в `odm` через ETL.

## API — Health

| Method | Path |
|--------|------|
| GET | `/api/v1/health`, `/health`, `/healthz` |

## Data model

### `ATPTLP_familymanager`

- `families` — status: `initiated|uploaded|parsed|ready|failed`
- `family_parameters`, `family_type_values` — нормализация metadata
- `user_projects` — legacy auth (JWT `sub`), для FamilyMang не используется

### `ATPTLP_openmodels`

- `openings`, `opening_history`

### `stg_bim`

- `model_snapshots` — export session (status: `created|completed|failed`)
- `mep_elements` — MEP elements per snapshot; каждый element содержит `snapshot_date`

### `odm`

- planned operational/analytical layer (ETL from `stg_bim`, не пишется FastAPI ingest)

### `atptlp_info`

- `companies`, `company_users`

## Dev without Docker

```bash
cd backet
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
# задать переменные из env.example
uvicorn app.main:app --reload
```

## Notes

- Object key: `projects/{project_id}/families/{family_id}/{sha256}.rfa`
- Presigned S3 — без `Authorization`
- `metadata.extra` (host/nested) сохраняется в JSONB; таблица связей и фильтры — не реализованы (см. api_spec rev 4)
