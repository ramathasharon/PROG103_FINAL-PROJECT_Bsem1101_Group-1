-- queries/triggers_demo.sql : show the triggers refusing bad changes (used in the presentation)
\set VERBOSITY terse
\echo --- 1. A rejected permit cannot be re-opened
UPDATE permits SET status = 'Under Review' WHERE permit_id = 'PRM-004';
\echo --- 2. Submitted permits must be reviewed before approval
UPDATE permits SET status = 'Approved' WHERE permit_id = 'PRM-006';
\echo --- 3. Wrong office for the permit type
UPDATE permits SET office_name = 'Building Control Unit' WHERE permit_id = 'PRM-006';
\echo --- 4. Duplicate live application
INSERT INTO permits (permit_id, applicant_id, kind, details) VALUES ('PRM-021','APP-003','business','Bangura Pharmacy');
\echo --- 5. A legal change: approve PRM-013 (already Under Review). Dates and history are automatic
BEGIN;
UPDATE permits SET status = 'Approved' WHERE permit_id = 'PRM-013';
SELECT permit_id, status, issue_date, expiry_date FROM permits WHERE permit_id = 'PRM-013';
SELECT permit_id, old_status, new_status, note FROM permit_history WHERE permit_id = 'PRM-013' ORDER BY history_id;
ROLLBACK;
