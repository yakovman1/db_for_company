CREATE SCHEMA IF NOT EXISTS stg_bim;

CREATE TABLE IF NOT EXISTS stg_bim.model_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id TEXT NOT NULL,
    created_by_windows_user TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    snapshot_date TIMESTAMPTZ NOT NULL,
    model_name TEXT NOT NULL,
    revit_version INTEGER NOT NULL,
    pbp_x DOUBLE PRECISION,
    pbp_y DOUBLE PRECISION,
    pbp_z DOUBLE PRECISION,
    pbp_angle DOUBLE PRECISION,
    sp_x DOUBLE PRECISION,
    sp_y DOUBLE PRECISION,
    sp_z DOUBLE PRECISION,
    fop_name TEXT,
    fop_path TEXT,
    project_number TEXT,
    project_name TEXT,
    project_stage TEXT,
    worksets_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    linked_files_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'created',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    CONSTRAINT ck_model_snapshots_status CHECK (status IN ('created', 'completed', 'failed'))
);

CREATE TABLE IF NOT EXISTS stg_bim.mep_elements (
    snapshot_id UUID NOT NULL REFERENCES stg_bim.model_snapshots(id) ON DELETE CASCADE,
    element_guid TEXT NOT NULL,
    revit_id INTEGER,
    category_name TEXT,
    family_name TEXT,
    type_name TEXT,
    workset_name TEXT,
    level_guid TEXT,
    level_name TEXT,
    space_guid TEXT,
    system_classification TEXT,
    system_name TEXT,
    is_linear BOOLEAN NOT NULL DEFAULT false,
    length DOUBLE PRECISION,
    dimension_1 DOUBLE PRECISION,
    dimension_2 DOUBLE PRECISION,
    location_point JSONB,
    bounding_box_volume DOUBLE PRECISION,
    bep_parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    connectors_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    PRIMARY KEY (snapshot_id, element_guid)
);

-- Staging: minimal indexes for ingest and ETL pickup only.
-- Analytical indexes (category, system, GIN on JSONB) belong in odm after ETL.
CREATE INDEX IF NOT EXISTS ix_model_snapshots_company_date
    ON stg_bim.model_snapshots (company_id, snapshot_date);
