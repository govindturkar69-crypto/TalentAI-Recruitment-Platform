-- database/migrations/009_add_interviews.sql

CREATE TABLE interviews (
    id INT PRIMARY KEY AUTO_INCREMENT,

    application_id INT NOT NULL,

    scheduled_at DATETIME NOT NULL,

    duration_minutes SMALLINT UNSIGNED NOT NULL DEFAULT 30,

    mode ENUM(
        'online',
        'in_person',
        'phone'
    ) NOT NULL,

    location_or_link VARCHAR(500) NULL,

    notes TEXT NULL,

    status ENUM(
        'scheduled',
        'completed',
        'cancelled'
    ) NOT NULL DEFAULT 'scheduled',

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_interviews_application
        FOREIGN KEY (application_id)
        REFERENCES applications(id)
        ON DELETE CASCADE,

    INDEX idx_interviews_application_scheduled
        (application_id, scheduled_at),

    INDEX idx_interviews_status_scheduled
        (status, scheduled_at)
);
