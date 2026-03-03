# db_for_company

Корневой README для быстрого входа в проект.

## Что внутри

- `backet/` - FastAPI backend для загрузки и каталога Revit family (`.rfa`)
- `revit-plugin/` - Revit-плагин (MVP) для интеграции с backend
- `docker-compose.yml` - локальная инфраструктура (Postgres + MinIO + backend)

## Быстрый старт

1. Подготовить окружение:
   - скопировать `backet/env.example` в `.env` в корне проекта и заполнить значения
2. Поднять сервисы:
   - `docker compose up -d --build`
3. Проверить API:
   - `http://localhost:8000/healthz`

## Основная документация

- Backend: `backet/README.md`
- Revit plugin: `revit-plugin/README.md`

## Важно

- В репозиторий не коммитить `.env` (секреты и локальные настройки).
- Для presigned URL используется разделение endpoint:
  - внутренний: `MINIO_ENDPOINT` (backend -> minio внутри docker-сети)
  - публичный: `MINIO_PUBLIC_ENDPOINT` (клиент -> minio с хоста)
