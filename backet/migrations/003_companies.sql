CREATE SCHEMA IF NOT EXISTS atptlp_info;

CREATE TABLE IF NOT EXISTS atptlp_info.companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id TEXT UNIQUE NOT NULL,
    name TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS atptlp_info.company_users (
    company_id TEXT NOT NULL REFERENCES atptlp_info.companies(company_id) ON DELETE CASCADE,
    windows_user TEXT NOT NULL,
    PRIMARY KEY (company_id, windows_user)
);
