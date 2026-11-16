-- Database initialization script for Campus Office Hours Booking API
-- Table: office_hour_bookings

CREATE TABLE IF NOT EXISTS office_hour_bookings (
    id SERIAL PRIMARY KEY,
    professor_id VARCHAR(255) NOT NULL,
    student_id VARCHAR(255) NOT NULL,
    starts_at_utc TIMESTAMPTZ NOT NULL,
    duration_minutes INTEGER NOT NULL,
    original_timezone VARCHAR(100) NOT NULL,
    CONSTRAINT chk_positive_duration CHECK (duration_minutes > 0)
);

-- Indices for rapid lookup and overlap queries
CREATE INDEX IF NOT EXISTS idx_office_hour_bookings_professor_id ON office_hour_bookings(professor_id);
CREATE INDEX IF NOT EXISTS idx_office_hour_bookings_starts_at_utc ON office_hour_bookings(starts_at_utc);
