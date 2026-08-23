-- Migration 006: Reconcile Job Lifecycle
-- Production jobs.is_active exists but is nullable. 
-- We must safely backfill NULL values to TRUE (1) and make the column NOT NULL.

UPDATE jobs 
SET is_active = 1 
WHERE is_active IS NULL;

ALTER TABLE jobs
MODIFY COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1;
