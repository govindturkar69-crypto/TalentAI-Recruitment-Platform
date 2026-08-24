-- Migration 007: Add saved_jobs table
-- Purpose: Add canonical saved_jobs table for tracking candidate saved jobs.
-- NOTE: This migration is skipped in production as production already has this table.

CREATE TABLE saved_jobs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    candidate_id INT NOT NULL,
    job_id INT NOT NULL,
    saved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    UNIQUE KEY unique_save (candidate_id, job_id)
);
