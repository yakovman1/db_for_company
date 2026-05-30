ALTER TABLE "ATPTLP_familymanager".families
    ADD COLUMN IF NOT EXISTS version        INTEGER     NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS family_name    TEXT,
    ADD COLUMN IF NOT EXISTS category       TEXT,
    ADD COLUMN IF NOT EXISTS is_primary     BOOLEAN,
    ADD COLUMN IF NOT EXISTS parent_family_id UUID;

CREATE INDEX IF NOT EXISTS ix_families_identity
    ON "ATPTLP_familymanager".families (project_id, family_name, category, is_primary)
    WHERE family_name IS NOT NULL;
