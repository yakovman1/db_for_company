-- Revision 8: журнал операций familylogs
-- Источник DDL: docs/familylogs_spec.md §4

CREATE TABLE IF NOT EXISTS "ATPTLP_familymanager".familylogs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),

    -- Кто
    company_id          TEXT NOT NULL,
    windows_user        TEXT NOT NULL,

    -- Что
    action              TEXT NOT NULL,
    outcome             TEXT NOT NULL DEFAULT 'success',
    source              TEXT NOT NULL DEFAULT 'server',  -- 'server' | 'client'

    -- Семейство (nullable для auth / catalog_error без family)
    family_id           UUID NULL
        REFERENCES "ATPTLP_familymanager".families(id) ON DELETE SET NULL,
    family_name         TEXT NULL,
    original_filename   TEXT NULL,
    category            TEXT NULL,
    family_version      INTEGER NULL,
    is_primary          BOOLEAN NULL,
    parent_family_id    UUID NULL,

    -- Каталог backend (носитель CATALOG)
    catalog_project_id  UUID NULL,

    -- Revit-проект / документ
    revit_project_name  TEXT NULL,
    revit_project_path  TEXT NULL,
    revit_document_kind TEXT NULL,  -- 'project' | 'family_editor' | NULL

    -- Ошибка
    error_message       TEXT NULL,
    http_status         INTEGER NULL,

    -- Доп. контекст (sha256, nested_count, etag, plugin_version, …)
    details             JSONB NOT NULL DEFAULT '{}'::jsonb,

    CONSTRAINT familylogs_outcome_check
        CHECK (outcome IN ('success', 'error', 'skipped', 'partial')),
    CONSTRAINT familylogs_source_check
        CHECK (source IN ('server', 'client')),
    CONSTRAINT familylogs_document_kind_check
        CHECK (revit_document_kind IS NULL OR revit_document_kind IN ('project', 'family_editor'))
);

CREATE INDEX IF NOT EXISTS ix_familylogs_created_at
    ON "ATPTLP_familymanager".familylogs (created_at DESC);

CREATE INDEX IF NOT EXISTS ix_familylogs_company_user
    ON "ATPTLP_familymanager".familylogs (company_id, windows_user, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_familylogs_family_id
    ON "ATPTLP_familymanager".familylogs (family_id, created_at DESC)
    WHERE family_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_familylogs_action
    ON "ATPTLP_familymanager".familylogs (action, created_at DESC);
