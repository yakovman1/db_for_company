ALTER TABLE "ATPTLP_familymanager".families
    ADD COLUMN IF NOT EXISTS uploaded_at TIMESTAMPTZ;
