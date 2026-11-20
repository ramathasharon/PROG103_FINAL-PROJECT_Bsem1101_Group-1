-- queries/10_transactions_demo.sql : BEGIN / COMMIT / ROLLBACK / SAVEPOINT
-- A transaction groups statements so that they ALL happen or NONE happen
-- (like a bank transfer: money leaves one account only if it reaches the other).

\echo '=== 1. ROLLBACK: a change that is cancelled'
BEGIN;
UPDATE applicants SET phone = '+232 00 000000' WHERE applicant_id = 'APP-001';
SELECT applicant_id, phone AS phone_inside_transaction FROM applicants WHERE applicant_id = 'APP-001';
ROLLBACK;
SELECT applicant_id, phone AS phone_after_rollback FROM applicants WHERE applicant_id = 'APP-001';

\echo '=== 2. COMMIT: a change that is kept (we undo it manually afterwards)'
BEGIN;
UPDATE applicants SET phone = '+232 76 123457' WHERE applicant_id = 'APP-001';
COMMIT;
SELECT applicant_id, phone AS phone_after_commit FROM applicants WHERE applicant_id = 'APP-001';
UPDATE applicants SET phone = '+232 76 123456' WHERE applicant_id = 'APP-001';

\echo '=== 3. SAVEPOINT: undo only part of a transaction'
BEGIN;
INSERT INTO applicants (applicant_id, full_name, phone, district)
VALUES ('APP-090', 'Demo One', '+232 70 000001', 'Bo');
SAVEPOINT after_first;
INSERT INTO applicants (applicant_id, full_name, phone, district)
VALUES ('APP-091', 'Demo Two', '+232 70 000002', 'Bo');
ROLLBACK TO SAVEPOINT after_first;           -- only Demo Two is undone
SELECT applicant_id, full_name FROM applicants WHERE applicant_id IN ('APP-090','APP-091');
ROLLBACK;                                    -- now everything is undone

\echo '=== 4. All or nothing: the stored procedure fails halfway, so the applicant is not saved either'
SELECT count(*) AS applicants_before FROM applicants;
DO $$
DECLARE
    v_applicant TEXT;
    v_permit    TEXT;
BEGIN
    CALL sp_register_applicant_and_permit('Test Person', '+232 70 555555', 'Bo',
                                          'business', 'ab', v_applicant, v_permit);  -- details too short
EXCEPTION WHEN check_violation THEN
    RAISE NOTICE 'Failed as expected (error code %)', SQLSTATE;
END $$;
SELECT count(*) AS applicants_after FROM applicants;   -- unchanged

\echo '=== 5. The same procedure with valid data (rolled back after showing the result)'
BEGIN;
CALL sp_register_applicant_and_permit('Test Person', '+232 70 555555', 'Bo',
                                      'business', 'Test Trading Company', NULL, NULL);
SELECT a.applicant_id, a.full_name, p.permit_id, p.details, p.status
  FROM applicants a JOIN permits p USING (applicant_id) WHERE a.full_name = 'Test Person';
ROLLBACK;
