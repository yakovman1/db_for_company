ALTER TABLE "ATPTLP_openmodels".openings
    ADD COLUMN IF NOT EXISTS content_hash TEXT;
