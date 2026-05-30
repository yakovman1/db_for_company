CREATE TABLE IF NOT EXISTS "ATPTLP_familymanager".user_favorites (
    company_id   TEXT        NOT NULL,
    windows_user TEXT        NOT NULL,
    family_id    UUID        NOT NULL REFERENCES "ATPTLP_familymanager".families(id) ON DELETE CASCADE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (company_id, windows_user, family_id)
);

CREATE INDEX IF NOT EXISTS idx_user_favorites_lookup
    ON "ATPTLP_familymanager".user_favorites (company_id, windows_user);

ALTER TABLE "ATPTLP_familymanager".families
    ADD COLUMN IF NOT EXISTS has_thumbnail BOOLEAN NOT NULL DEFAULT false;
