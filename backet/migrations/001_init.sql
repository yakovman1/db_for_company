-- Families
CREATE TABLE IF NOT EXISTS families (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL,
    bucket VARCHAR(255) NOT NULL,
    object_key VARCHAR(1024) NOT NULL,
    sha256 VARCHAR(128),
    size_bytes INTEGER,
    original_filename VARCHAR(255) NOT NULL,
    etag VARCHAR(128),
    status TEXT NOT NULL,
    metadata_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_families_project_id ON families (project_id);
CREATE INDEX IF NOT EXISTS ix_families_sha256 ON families (sha256);

-- User projects (composite PK)
CREATE TABLE IF NOT EXISTS user_projects (
    user_id UUID NOT NULL,
    project_id UUID NOT NULL,
    PRIMARY KEY (user_id, project_id)
);
CREATE INDEX IF NOT EXISTS ix_user_projects_user_id ON user_projects (user_id);
CREATE INDEX IF NOT EXISTS ix_user_projects_project_id ON user_projects (project_id);

-- Family parameters
CREATE TABLE IF NOT EXISTS family_parameters (
    id UUID PRIMARY KEY,
    family_id UUID NOT NULL REFERENCES families(id) ON DELETE CASCADE,
    param_name VARCHAR(255) NOT NULL,
    is_instance BOOLEAN DEFAULT FALSE,
    is_shared BOOLEAN DEFAULT FALSE,
    shared_guid VARCHAR(64),
    storage_type VARCHAR(64),
    spec TEXT,
    UNIQUE (family_id, param_name)
);
CREATE INDEX IF NOT EXISTS ix_family_parameters_family_id ON family_parameters (family_id);

-- Family type values
CREATE TABLE IF NOT EXISTS family_type_values (
    id UUID PRIMARY KEY,
    family_id UUID NOT NULL REFERENCES families(id) ON DELETE CASCADE,
    type_name VARCHAR(255) NOT NULL,
    param_name VARCHAR(255) NOT NULL,
    value_text TEXT,
    UNIQUE (family_id, type_name, param_name)
);
CREATE INDEX IF NOT EXISTS ix_family_type_values_family_id ON family_type_values (family_id);



