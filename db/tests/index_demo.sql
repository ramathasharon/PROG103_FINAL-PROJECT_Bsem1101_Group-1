-- tests/index_demo.sql : do the indexes really help?
-- Adds 40,000 temporary permits, compares query plans WITH and WITHOUT an index,
-- then ROLLS BACK so your real data is untouched.
-- (SET session_replication_role = replica switches triggers off for the bulk load;
--  it needs a superuser such as postgres.)

BEGIN;
SET LOCAL session_replication_role = replica;

INSERT INTO permits (permit_id, applicant_id, kind, details, status, office_name,
                     date_applied, issue_date, expiry_date)
SELECT 'PRM-' || (1000 + g),
       'APP-' || lpad((1 + g % 12)::text, 3, '0'),
       'general',
       'Load test permit ' || g,
       CASE WHEN g % 10 < 8 THEN 'Rejected' ELSE 'Approved' END,   -- 80% rejected, 20% approved
       NULL,
       CURRENT_DATE - 400,
       CASE WHEN g % 10 >= 8 THEN CURRENT_DATE - 300 END,
       CASE WHEN g % 10 >= 8 THEN CURRENT_DATE + (g % 700) END
  FROM generate_series(1, 40000) g;
ANALYZE permits;

\echo '=== Query: approved permits expiring in the next 30 days'
\echo '--- WITH the partial index idx_permits_approved_expiry'
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY ON)
SELECT permit_id, expiry_date FROM permits
 WHERE status = 'Approved' AND expiry_date BETWEEN CURRENT_DATE AND CURRENT_DATE + 30;

DROP INDEX idx_permits_approved_expiry;
DROP INDEX idx_permits_status;
\echo '--- WITHOUT the indexes (the database must read every row)'
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY ON)
SELECT permit_id, expiry_date FROM permits
 WHERE status = 'Approved' AND expiry_date BETWEEN CURRENT_DATE AND CURRENT_DATE + 30;

ROLLBACK;   -- indexes come back and the 40,000 rows disappear
