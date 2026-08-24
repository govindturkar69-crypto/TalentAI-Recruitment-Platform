-- ============================================
-- Pre-003/004 Schema Fixture
-- Represents production DB schema BEFORE migrations 003 and 004
-- ============================================

-- Users Table (Candidates + Recruiters)
CREATE TABLE IF NOT EXISTS users (
    id          INT PRIMARY KEY AUTO_INCREMENT,
    name        VARCHAR(100)  NOT NULL,
    email       VARCHAR(100)  NOT NULL UNIQUE,
    password    VARCHAR(255)  NOT NULL,
    role        ENUM('candidate','recruiter') NOT NULL DEFAULT 'candidate',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Jobs Table (created by recruiters)
CREATE TABLE IF NOT EXISTS jobs (
    id               INT PRIMARY KEY AUTO_INCREMENT,
    recruiter_id     INT NOT NULL,
    job_title        VARCHAR(150) NOT NULL,
    required_skills  TEXT         NOT NULL,   -- comma-separated
    description      TEXT,
    location         VARCHAR(100),
    experience       VARCHAR(50),
    is_active        TINYINT(1) DEFAULT 1,
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
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Simulating the table that already exists in production
CREATE TABLE saved_jobs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    candidate_id INT NOT NULL,
    job_id INT NOT NULL,
    saved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    UNIQUE KEY unique_save (candidate_id, job_id)
);
