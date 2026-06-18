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

-- Sample jobs
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
