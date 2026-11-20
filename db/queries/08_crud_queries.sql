-- queries/08_crud_queries.sql : basic CRUD statements (Create, Read, Update, Delete)
-- Every change is inside BEGIN ... ROLLBACK so the demo data stays untouched.
-- Replace ROLLBACK with COMMIT if you want to keep a change.

\echo '--- READ 1: all applicants in the Southern region (JOIN + WHERE + ORDER BY)'
SELECT a.applicant_id, a.full_name, a.district, d.region
  FROM applicants a JOIN districts d ON d.district_name = a.district
 WHERE d.region = 'Southern'
 ORDER BY a.full_name;

\echo '--- READ 2: permits waiting for a decision, oldest first'
SELECT permit_id, full_name, type_name, status, date_applied
  FROM v_permit_details
 WHERE status IN ('Submitted','Under Review')
 ORDER BY date_applied;

BEGIN;
\echo '--- CREATE: register an applicant, then file a permit'
INSERT INTO applicants (applicant_id, full_name, phone, district)
VALUES ('APP-013', 'Kadiatu Sankoh', '+232 76 998877', 'Falaba');
INSERT INTO permits (permit_id, applicant_id, kind, details)
VALUES ('PRM-021', 'APP-013', 'general', 'Craft market stall, Kabala');
SELECT permit_id, status, date_applied FROM permits WHERE permit_id = 'PRM-021';

\echo '--- UPDATE: change the phone number and permit details'
UPDATE applicants SET phone = '+232 76 998800' WHERE applicant_id = 'APP-013';
UPDATE permits SET details = 'Craft and souvenir stall, Kabala' WHERE permit_id = 'PRM-021';
SELECT a.full_name, a.phone, p.details
  FROM applicants a JOIN permits p USING (applicant_id) WHERE a.applicant_id = 'APP-013';

\echo '--- DELETE: remove the permit first, then the applicant (RESTRICT rule)'
DELETE FROM permits WHERE permit_id = 'PRM-021';
DELETE FROM applicants WHERE applicant_id = 'APP-013';
SELECT count(*) AS applicants_left FROM applicants;
ROLLBACK;
