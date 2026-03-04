-- Run this on your LIVE database (MySQL/MariaDB).
-- Replace 'school_event' with your actual database name if different.

USE school_event;

-- 1) Allow CONFIRMED status (run if you get "Data truncated" on admin Confirm)
ALTER TABLE event_registrations MODIFY status VARCHAR(20) DEFAULT 'REGISTERED';

-- 2) Add photo column to students (for profile photo in Create Profile)
ALTER TABLE students ADD COLUMN photo VARCHAR(255) NULL AFTER blood_group;

-- 3) Add photo column to event_registrations (optional; app works without it)
ALTER TABLE event_registrations ADD COLUMN photo VARCHAR(255) NULL AFTER txn_no;

-- 4) Which bKash number they sent payment to: 'faisal' or 'guddu'
ALTER TABLE event_registrations ADD COLUMN bkash_to VARCHAR(20) NULL AFTER txn_no;
