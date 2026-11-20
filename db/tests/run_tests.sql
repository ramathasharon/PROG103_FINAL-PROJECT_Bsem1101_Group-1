-- tests/run_tests.sql : automated database tests
-- Run:  psql -U postgres -d permits_db -f tests/run_tests.sql
-- Needs the sample data (07_sample_data.sql). Everything happens inside one
-- transaction that is ROLLED BACK at the end, so your data is never changed.

\set QUIET on
BEGIN;

CREATE TEMP TABLE results (id SERIAL, area TEXT, test TEXT, ok BOOLEAN);

-- helper: record a pass/fail for a yes/no condition
CREATE FUNCTION pg_temp.check_that(p_area TEXT, p_test TEXT, p_ok BOOLEAN)
RETURNS VOID LANGUAGE sql AS $$
    INSERT INTO results (area, test, ok) VALUES (p_area, p_test, COALESCE(p_ok, false));
$$;

-- helper: the SQL statement MUST fail with the given SQLSTATE code.
-- If it wrongly succeeds we raise our own error (ZZ001), which also undoes the
-- statement, so one broken rule cannot disturb the tests that follow.
CREATE FUNCTION pg_temp.expect_error(p_area TEXT, p_test TEXT, p_sql TEXT, p_state TEXT)
RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
    EXECUTE p_sql;
    RAISE EXCEPTION 'statement succeeded but should have failed' USING ERRCODE = 'ZZ001';
EXCEPTION WHEN OTHERS THEN
    INSERT INTO results (area, test, ok)
    VALUES (p_area,
            CASE WHEN SQLSTATE = 'ZZ001' THEN p_test || ' (NO ERROR RAISED)' ELSE p_test END,
            SQLSTATE = p_state);
END $$;

\o /dev/null
-- ---------------------------------------------------------------- constraints
SELECT pg_temp.expect_error('Constraint','Phone with letters is rejected',
  $q$INSERT INTO applicants VALUES ('APP-100','Test Person','abc12345','Bo')$q$, '23514');
SELECT pg_temp.expect_error('Constraint','Unknown district is rejected (foreign key)',
  $q$INSERT INTO applicants VALUES ('APP-100','Test Person','+232 70 111111','Atlantis')$q$, '23503');
SELECT pg_temp.expect_error('Constraint','Name shorter than 3 characters is rejected',
  $q$INSERT INTO applicants VALUES ('APP-100','Al','+232 70 111111','Bo')$q$, '23514');
SELECT pg_temp.expect_error('Constraint','Invalid status value is rejected',
  $q$UPDATE permits SET status = 'Finished' WHERE permit_id = 'PRM-003'$q$, '23514');
SELECT pg_temp.expect_error('Constraint','Details shorter than 3 characters are rejected',
  $q$INSERT INTO permits (permit_id, applicant_id, kind, details) VALUES ('PRM-100','APP-001','general','ab')$q$, '23514');
SELECT pg_temp.expect_error('Constraint','Permit for unknown applicant is rejected',
  $q$INSERT INTO permits (permit_id, applicant_id, kind, details) VALUES ('PRM-100','APP-999','general','Market stall')$q$, '23503');
SELECT pg_temp.expect_error('Constraint','Applicant with permits cannot be deleted (RESTRICT)',
  $q$DELETE FROM applicants WHERE applicant_id = 'APP-001'$q$, '23503');
SELECT pg_temp.expect_error('Constraint','Expiry date before issue date is rejected',
  $q$INSERT INTO permits (permit_id, applicant_id, kind, details, status, issue_date, expiry_date)
     VALUES ('PRM-100','APP-001','general','Test stall','Approved', CURRENT_DATE, CURRENT_DATE - 1)$q$, '23514');
SELECT pg_temp.expect_error('Constraint','Approved permit without expiry date is rejected',
  $q$INSERT INTO permits (permit_id, applicant_id, kind, details, status)
     VALUES ('PRM-100','APP-001','general','Test stall','Approved')$q$, '23514');
SELECT pg_temp.expect_error('Constraint','Malformed permit ID is rejected',
  $q$INSERT INTO permits (permit_id, applicant_id, kind, details) VALUES ('P1','APP-001','general','Market stall')$q$, '23514');

-- ------------------------------------------------------------------- triggers
SELECT pg_temp.expect_error('Trigger','Under Review -> Submitted (going backwards) is refused',
  $q$UPDATE permits SET status = 'Submitted' WHERE permit_id = 'PRM-002'$q$, '23514');
SELECT pg_temp.expect_error('Trigger','Submitted -> Approved is refused',
  $q$UPDATE permits SET status = 'Approved' WHERE permit_id = 'PRM-006'$q$, '23514');
SELECT pg_temp.expect_error('Trigger','Rejected -> Under Review is refused',
  $q$UPDATE permits SET status = 'Under Review' WHERE permit_id = 'PRM-004'$q$, '23514');
SELECT pg_temp.expect_error('Trigger','Expired -> Approved without a new expiry date is refused',
  $q$UPDATE permits SET status = 'Approved' WHERE permit_id = 'PRM-005'$q$, '23514');
SELECT pg_temp.expect_error('Trigger','Wrong office on insert is refused',
  $q$INSERT INTO permits (permit_id, applicant_id, kind, details, office_name)
     VALUES ('PRM-100','APP-001','business','Test Shop','Building Control Unit')$q$, '23514');
SELECT pg_temp.expect_error('Trigger','Wrong office on update is refused',
  $q$UPDATE permits SET office_name = 'Building Control Unit' WHERE permit_id = 'PRM-006'$q$, '23514');
SELECT pg_temp.expect_error('Trigger','Duplicate live application is refused',
  $q$INSERT INTO permits (permit_id, applicant_id, kind, details)
     VALUES ('PRM-100','APP-003','business','BANGURA PHARMACY')$q$, '23505');

INSERT INTO permits (permit_id, applicant_id, kind, details)
VALUES ('PRM-101','APP-001','general','Street food stall, Lumley');   -- earlier one was rejected
SELECT pg_temp.check_that('Trigger','Re-applying after a rejection is allowed',
  EXISTS (SELECT 1 FROM permits WHERE permit_id = 'PRM-101'));

UPDATE permits SET status = 'Under Review' WHERE permit_id = 'PRM-017';        -- Submitted -> Under Review
UPDATE permits SET status = 'Approved'     WHERE permit_id = 'PRM-017';        -- building permit, 3 years
SELECT pg_temp.check_that('Trigger','Approval sets issue date to today',
  (SELECT issue_date = CURRENT_DATE FROM permits WHERE permit_id = 'PRM-017'));
SELECT pg_temp.check_that('Trigger','Building permit expiry is 3 x 365 days after issue',
  (SELECT expiry_date = issue_date + 1095 FROM permits WHERE permit_id = 'PRM-017'));
SELECT pg_temp.check_that('Trigger','History has 3 rows for PRM-017 (created, review, approved)',
  (SELECT count(*) = 3 FROM permit_history WHERE permit_id = 'PRM-017'));
SELECT pg_temp.check_that('Trigger','History records the status change text',
  (SELECT bool_or(note = 'Status Under Review -> Approved') FROM permit_history WHERE permit_id = 'PRM-017'));

UPDATE permits SET expiry_date = CURRENT_DATE + 365, status = 'Approved' WHERE permit_id = 'PRM-005';  -- renewal
SELECT pg_temp.check_that('Trigger','Renewal of an expired permit is allowed and logged',
  (SELECT bool_or(note LIKE 'Renewed until %') FROM permit_history WHERE permit_id = 'PRM-005'));

-- ------------------------------------------------------------------ functions
SELECT pg_temp.check_that('Function','fn_next_id gives APP-013', fn_next_id('APP') = 'APP-013');
SELECT pg_temp.check_that('Function','fn_next_id gives PRM-102 after PRM-101', fn_next_id('PRM') = 'PRM-102');
SELECT pg_temp.expect_error('Function','fn_next_id rejects an unknown prefix',
  $q$SELECT fn_next_id('XYZ')$q$, 'P0001');
SELECT pg_temp.check_that('Function','fn_permit_fee returns 100, 500 and 1500',
  (fn_permit_fee('general'), fn_permit_fee('business'), fn_permit_fee('building')) = (100.00, 500.00, 1500.00));
SELECT pg_temp.expect_error('Function','fn_permit_fee rejects an unknown kind',
  $q$SELECT fn_permit_fee('driving')$q$, 'P0001');
SELECT pg_temp.check_that('Function','fn_office_handles is true for the right office',
  fn_office_handles('Building Control Unit','building'));
SELECT pg_temp.check_that('Function','fn_office_handles is false for the wrong office',
  NOT fn_office_handles('Building Control Unit','business'));
SELECT pg_temp.check_that('Function','fn_days_to_expiry matches the dates',
  fn_days_to_expiry('PRM-001') = (SELECT expiry_date - CURRENT_DATE FROM permits WHERE permit_id = 'PRM-001'));
SELECT pg_temp.check_that('Function','fn_days_to_expiry is NULL when there is no expiry date',
  fn_days_to_expiry('PRM-006') IS NULL);

INSERT INTO permits (permit_id, applicant_id, kind, details, status, issue_date, expiry_date)
VALUES ('PRM-103','APP-012','general','Old stall','Approved', CURRENT_DATE-400, CURRENT_DATE-35);
SELECT pg_temp.check_that('Function','fn_expire_overdue_permits expires exactly one permit',
  fn_expire_overdue_permits() = 1);
SELECT pg_temp.check_that('Function','The overdue permit is now Expired',
  (SELECT status = 'Expired' FROM permits WHERE permit_id = 'PRM-103'));

-- ----------------------------------------------------------------- procedures
CALL sp_decide_permit('PRM-006','Business Licensing Unit','review');
CALL sp_decide_permit('PRM-006','Business Licensing Unit','approve');
SELECT pg_temp.check_that('Procedure','sp_decide_permit review then approve works',
  (SELECT status = 'Approved' AND expiry_date = CURRENT_DATE + 365
     AND office_name = 'Business Licensing Unit' FROM permits WHERE permit_id = 'PRM-006'));
CALL sp_decide_permit('PRM-006','Business Licensing Unit','renew');
SELECT pg_temp.check_that('Procedure','sp_decide_permit renew adds one more year',
  (SELECT expiry_date = CURRENT_DATE + 730 FROM permits WHERE permit_id = 'PRM-006'));
SELECT pg_temp.expect_error('Procedure','sp_decide_permit refuses the wrong office',
  $q$CALL sp_decide_permit('PRM-010','Building Control Unit','review')$q$, 'P0001');
SELECT pg_temp.expect_error('Procedure','sp_decide_permit refuses an unknown decision',
  $q$CALL sp_decide_permit('PRM-010','Business Licensing Unit','delete')$q$, 'P0001');
SELECT pg_temp.expect_error('Procedure','sp_decide_permit refuses an unknown permit',
  $q$CALL sp_decide_permit('PRM-999','Business Licensing Unit','review')$q$, 'P0001');
SELECT pg_temp.expect_error('Procedure','sp_decide_permit refuses to renew a submitted permit',
  $q$CALL sp_decide_permit('PRM-010','Business Licensing Unit','renew')$q$, 'P0001');

DO $$
DECLARE v_a TEXT; v_p TEXT; v_before INT; v_after INT;
BEGIN
    SELECT count(*) INTO v_before FROM applicants;
    BEGIN
        CALL sp_register_applicant_and_permit('Test Person','+232 70 555555','Bo','business','ab',v_a,v_p);
    EXCEPTION WHEN check_violation THEN NULL;
    END;
    SELECT count(*) INTO v_after FROM applicants;
    PERFORM pg_temp.check_that('Procedure','sp_register_applicant_and_permit is all-or-nothing', v_before = v_after);
END $$;

DO $$
DECLARE v_a TEXT; v_p TEXT;
BEGIN
    CALL sp_register_applicant_and_permit('Kadiatu Sankoh','+232 76 998877','Falaba','general','Craft market stall',v_a,v_p);
    PERFORM pg_temp.check_that('Procedure','sp_register_applicant_and_permit creates both rows',
        EXISTS (SELECT 1 FROM permits WHERE permit_id = v_p AND applicant_id = v_a));
END $$;

-- ---------------------------------------------------------------------- views
SELECT pg_temp.check_that('View','v_status_summary has 5 rows', (SELECT count(*) = 5 FROM v_status_summary));
SELECT pg_temp.check_that('View','v_status_summary adds up to the number of permits',
  (SELECT sum(permits) FROM v_status_summary) = (SELECT count(*) FROM permits));
SELECT pg_temp.check_that('View','v_permit_details has one row per permit',
  (SELECT count(*) FROM v_permit_details) = (SELECT count(*) FROM permits));
SELECT pg_temp.check_that('View','v_expiring_soon contains only approved permits due within 30 days',
  (SELECT count(*) > 0 AND bool_and(days_left BETWEEN 0 AND 30) FROM v_expiring_soon));
SELECT pg_temp.check_that('View','v_revenue_by_type totals at least Le 3,800 for approved permits',
  (SELECT sum(total_fees_le) FROM v_revenue_by_type) >= 3800);

-- -------------------------------------------------------------------- indexes
SELECT pg_temp.check_that('Index','All 7 custom indexes exist',
  (SELECT count(*) = 7 FROM pg_indexes WHERE schemaname = 'public'
      AND indexname IN ('idx_permits_status','idx_permits_applicant','idx_permits_kind',
                        'idx_permits_approved_expiry','idx_applicants_district',
                        'idx_permits_dup_check','idx_history_permit')));
SELECT pg_temp.check_that('Index','The partial index only covers approved permits',
  (SELECT indexdef LIKE '%WHERE (status = ''Approved''%' FROM pg_indexes WHERE indexname = 'idx_permits_approved_expiry'));

-- -------------------------------------------------------------------- results
\o
\set QUIET off
\pset format aligned
SELECT id, area, test, CASE WHEN ok THEN 'PASS' ELSE 'FAIL' END AS result FROM results ORDER BY id;
SELECT count(*) FILTER (WHERE ok) AS passed, count(*) FILTER (WHERE NOT ok) AS failed, count(*) AS total FROM results;

ROLLBACK;   -- undo everything the tests did
