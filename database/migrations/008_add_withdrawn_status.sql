-- Migration 008: Add 'withdrawn' status to applications table

ALTER TABLE applications
MODIFY COLUMN status
ENUM(
    'applied',
    'shortlisted',
    'rejected',
    'hired',
    'withdrawn'
)
NOT NULL
DEFAULT 'applied';
