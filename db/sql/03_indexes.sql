-- 03_indexes.sql : indexes chosen for the queries the application really runs
-- (PRIMARY KEY and UNIQUE constraints already create their own indexes.)

-- Filter by status (the status drop-down on the Permits tab)
CREATE INDEX IF NOT EXISTS idx_permits_status      ON permits (status);

-- "All permits of one applicant" (permit count on the Applicants tab, FK look-ups)
CREATE INDEX IF NOT EXISTS idx_permits_applicant   ON permits (applicant_id);

-- Filter by permit type
CREATE INDEX IF NOT EXISTS idx_permits_kind        ON permits (kind);

-- Partial index: only approved permits are ever checked for expiry, so the
-- index stays small and the "expiring soon" query is fast.
CREATE INDEX IF NOT EXISTS idx_permits_approved_expiry
    ON permits (expiry_date) WHERE status = 'Approved';

-- Reports by district
CREATE INDEX IF NOT EXISTS idx_applicants_district ON applicants (district);

-- Duplicate-application check made by a trigger (applicant + kind, case-insensitive details)
CREATE INDEX IF NOT EXISTS idx_permits_dup_check
    ON permits (applicant_id, kind, lower(details));

-- Show the history of one permit
CREATE INDEX IF NOT EXISTS idx_history_permit      ON permit_history (permit_id, changed_at);
