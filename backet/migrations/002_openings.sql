CREATE SCHEMA IF NOT EXISTS "ATPTLP_openmodels";

-- Openings registry (OPN_Database)
CREATE TABLE IF NOT EXISTS "ATPTLP_openmodels".openings (
    id BIGSERIAL PRIMARY KEY,
    model_guid UUID NOT NULL,
    element_unique_id TEXT NOT NULL,
    element_id BIGINT,
    family_name TEXT,
    type_name TEXT,
    category_name TEXT,
    level_name TEXT,
    location_x DOUBLE PRECISION,
    location_y DOUBLE PRECISION,
    location_z DOUBLE PRECISION,
    width DOUBLE PRECISION,
    height DOUBLE PRECISION,
    depth DOUBLE PRECISION,
    diameter DOUBLE PRECISION,
    extra_fields JSONB,
    content_hash TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    schedule_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (model_guid, element_unique_id)
);

CREATE INDEX IF NOT EXISTS ix_openings_model_guid ON "ATPTLP_openmodels".openings (model_guid);

CREATE TABLE IF NOT EXISTS "ATPTLP_openmodels".opening_history (
    id BIGSERIAL PRIMARY KEY,
    opening_id BIGINT NOT NULL REFERENCES "ATPTLP_openmodels".openings(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by TEXT
);

CREATE INDEX IF NOT EXISTS ix_opening_history_opening_id ON "ATPTLP_openmodels".opening_history (opening_id);
