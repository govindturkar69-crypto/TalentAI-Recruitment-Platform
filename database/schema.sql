-- ============================================
-- AI Recruitment Platform - Database Schema
-- ============================================

CREATE DATABASE IF NOT EXISTS recruitment_db;
USE recruitment_db;

-- Users Table (Candidates + Recruiters)
CREATE TABLE IF NOT EXISTS users (
    id          INT PRIMARY KEY AUTO_INCREMENT,
    name        VARCHAR(100)  NOT NULL,
    email       VARCHAR(100)  NOT NULL UNIQUE,
    password    VARCHAR(255)  NOT NULL,
    role        ENUM('candidate','recruiter') NOT NULL DEFAULT 'candidate',
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    company_id  INT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Companies Table
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

ALTER TABLE users ADD CONSTRAINT fk_user_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE SET NULL;
CREATE INDEX idx_users_company_id ON users(company_id);

-- Audit Logs Table
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

-- Jobs Table (created by recruiters)
CREATE TABLE IF NOT EXISTS jobs (
    id               INT PRIMARY KEY AUTO_INCREMENT,
    recruiter_id     INT NOT NULL,
    job_title        VARCHAR(150) NOT NULL,
    required_skills  TEXT         NOT NULL,   -- comma-separated
    description      TEXT,
    location         VARCHAR(100),
    experience       VARCHAR(50),
    is_active        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recruiter_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Resumes Table
CREATE TABLE IF NOT EXISTS resumes (
    id           INT PRIMARY KEY AUTO_INCREMENT,
    user_id      INT          NOT NULL,
    resume_path  VARCHAR(255) NOT NULL,
    skills       TEXT,                        -- comma-separated extracted skills
    raw_text     LONGTEXT,                    -- full resume text
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Applications Table (candidate applies to job)
CREATE TABLE IF NOT EXISTS applications (
    id           INT PRIMARY KEY AUTO_INCREMENT,
    candidate_id INT   NOT NULL,
    job_id       INT   NOT NULL,
    resume_id    INT   NOT NULL,
    score        FLOAT DEFAULT 0,
    matched_skills TEXT,
    missing_skills TEXT,
    status       ENUM('applied','shortlisted','rejected','hired') DEFAULT 'applied',
    applied_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (job_id)       REFERENCES jobs(id)  ON DELETE CASCADE,
    FOREIGN KEY (resume_id)    REFERENCES resumes(id) ON DELETE CASCADE
);

-- ============================================
-- Sample Data (for testing)
-- ============================================

-- Recruiter account  (password: admin123)
INSERT INTO users (name, email, password, role) VALUES
('HR Admin', 'admin@company.com',
 'pbkdf2:sha256:600000$example$hashedpassword', 'recruiter');

-- Sample Jobs
INSERT INTO jobs (recruiter_id, job_title, required_skills, description, location, experience) VALUES
(1, 'Full Stack Developer',
 'python,flask,mysql,javascript,html,css,rest api,git',
 'We need a skilled full-stack developer to build scalable web apps.',
 'Remote', '2-4 years'),

(1, 'Data Scientist',
 'python,machine learning,pandas,sql,statistics,scikit-learn,tensorflow',
 'Analyze large datasets and build ML models for business insights.',
 'Bangalore', '3-5 years'),

(1, 'Frontend Developer',
 'javascript,react,html,css,typescript,git,rest api',
 'Create beautiful and responsive user interfaces.',
 'Mumbai', '1-3 years'),

(1, 'Backend Developer',
 'python,django,mysql,rest api,docker,aws,git',
 'Build robust backend services and APIs.',
 'Hyderabad', '2-4 years');

-- Phase 1B Schema Additions

CREATE TABLE IF NOT EXISTS candidate_profiles (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    bio TEXT,
    phone VARCHAR(20),
    location VARCHAR(100),
    experience_years VARCHAR(50),
    linkedin_url VARCHAR(255),
    github_url VARCHAR(255),
    portfolio_url VARCHAR(255),
    skills TEXT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS candidate_education (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    institution VARCHAR(255) NOT NULL,
    degree VARCHAR(255),
    field_of_study VARCHAR(255),
    start_date DATE,
    end_date DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX idx_cand_edu_userid ON candidate_education(user_id);

CREATE TABLE IF NOT EXISTS candidate_experience (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    company VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    start_date DATE,
    end_date DATE,
    is_current BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX idx_cand_exp_userid ON candidate_experience(user_id);

CREATE TABLE IF NOT EXISTS candidate_projects (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    url VARCHAR(500),
    technologies TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX idx_cand_proj_userid ON candidate_projects(user_id);

CREATE TABLE IF NOT EXISTS candidate_certifications (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    issuer VARCHAR(255),
    issue_date DATE,
    credential_url VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX idx_cand_cert_userid ON candidate_certifications(user_id);

CREATE TABLE IF NOT EXISTS candidate_achievements (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    achieved_date DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX idx_cand_ach_userid ON candidate_achievements(user_id);
