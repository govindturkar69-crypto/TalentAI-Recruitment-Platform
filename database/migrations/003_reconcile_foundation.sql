-- database/migrations/003_reconcile_foundation.sql
-- Purpose: Safely deploy missing Phase 1A foundation objects against production.

-- PRE-CHECK: SHOW TABLES LIKE 'companies'; (Expected: Empty)
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

-- PRE-CHECK: SHOW COLUMNS FROM users LIKE 'is_active'; (Expected: Empty)
ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;

-- PRE-CHECK: SHOW COLUMNS FROM users LIKE 'company_id'; (Expected: Empty)
ALTER TABLE users ADD COLUMN company_id INT NULL;

-- PRE-CHECK: SELECT * FROM information_schema.KEY_COLUMN_USAGE WHERE TABLE_NAME = 'users' AND CONSTRAINT_NAME = 'fk_user_company'; (Expected: Empty)
ALTER TABLE users ADD CONSTRAINT fk_user_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE SET NULL;
CREATE INDEX idx_users_company_id ON users(company_id);

-- PRE-CHECK: SHOW TABLES LIKE 'audit_logs'; (Expected: Empty)
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

CREATE INDEX idx_auditlogs_actor ON audit_logs(actor_user_id);
CREATE INDEX idx_auditlogs_created ON audit_logs(created_at);
