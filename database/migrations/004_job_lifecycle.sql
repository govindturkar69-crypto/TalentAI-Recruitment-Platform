-- database/migrations/004_job_lifecycle.sql
-- Purpose: Add canonical job lifecycle column to jobs table.

-- PRE-CHECK: SHOW COLUMNS FROM jobs LIKE 'is_active'; (Expected: Empty)
ALTER TABLE jobs ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;
