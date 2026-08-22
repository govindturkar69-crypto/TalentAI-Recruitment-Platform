-- database/migrations/001_foundation.sql
-- Note: This is an additive, versioned migration.
-- Requirement: Pre-migration backup must be taken prior to executing.
-- Execution: Manual. DO NOT execute automatically.

-- 1. Create Companies table
CREATE TABLE IF NOT EXISTS companies (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    website VARCHAR(255),
    logo_path VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 2. Add users.is_active and users.company_id safely
-- Assuming additive execution on a clean schema relative to this feature.
ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE users ADD COLUMN company_id INT NULL;

-- 3. Add FK and Index for users.company_id
ALTER TABLE users ADD CONSTRAINT fk_user_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE SET NULL;
CREATE INDEX idx_users_company_id ON users(company_id);

-- 4. Create Audit Logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    actor_user_id INT NULL, 
    action VARCHAR(255) NOT NULL,
    target_type VARCHAR(100) NOT NULL, 
    target_id INT,
    safe_details TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 5. Indexes for Audit Logs
CREATE INDEX idx_auditlogs_actor ON audit_logs(actor_user_id);
CREATE INDEX idx_auditlogs_created ON audit_logs(created_at);
