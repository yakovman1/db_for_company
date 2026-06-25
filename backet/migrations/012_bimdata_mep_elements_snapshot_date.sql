-- Apply only if 011_bimdata.sql was already run without snapshot_date on mep_elements.
ALTER TABLE stg_bim.mep_elements
    ADD COLUMN IF NOT EXISTS snapshot_date TIMESTAMPTZ;

UPDATE stg_bim.mep_elements AS e
SET snapshot_date = s.snapshot_date
FROM stg_bim.model_snapshots AS s
WHERE e.snapshot_id = s.id
  AND e.snapshot_date IS NULL;

ALTER TABLE stg_bim.mep_elements
    ALTER COLUMN snapshot_date SET NOT NULL;
