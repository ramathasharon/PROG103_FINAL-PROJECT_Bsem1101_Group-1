-- queries/09_analysis_queries.sql : the queries we show in the presentation
-- Covers joins, aggregates, GROUP BY/HAVING, subqueries, CTEs, window
-- functions, CASE, date functions, text search, views and stored functions.

\echo '--- Q1 Aggregate: permits per status (view)'
SELECT * FROM v_status_summary;

\echo '--- Q2 GROUP BY + HAVING: applicants with more than one permit'
SELECT a.full_name, COUNT(*) AS permits
  FROM applicants a JOIN permits p USING (applicant_id)
 GROUP BY a.applicant_id, a.full_name
HAVING COUNT(*) > 1
 ORDER BY permits DESC, a.full_name;

\echo '--- Q3 LEFT JOIN: districts that have no applicants yet'
SELECT d.district_name, d.region
  FROM districts d LEFT JOIN applicants a ON a.district = d.district_name
 WHERE a.applicant_id IS NULL
 ORDER BY d.region, d.district_name;

\echo '--- Q4 Subquery: permit types that cost more than the average fee'
SELECT type_name, base_fee
  FROM permit_types
 WHERE base_fee > (SELECT AVG(base_fee) FROM permit_types);

\echo '--- Q5 CTE: average days from application to issue, by type'
WITH issued AS (
    SELECT kind, issue_date - date_applied AS days_to_issue
      FROM permits WHERE issue_date IS NOT NULL)
SELECT pt.type_name, ROUND(AVG(i.days_to_issue), 1) AS avg_days, COUNT(*) AS permits
  FROM issued i JOIN permit_types pt USING (kind)
 GROUP BY pt.type_name ORDER BY avg_days;

\echo '--- Q6 Window function: latest permit of each applicant'
SELECT applicant_id, full_name, permit_id, details, date_applied
  FROM (SELECT p.applicant_id, a.full_name, p.permit_id, p.details, p.date_applied,
               ROW_NUMBER() OVER (PARTITION BY p.applicant_id
                                  ORDER BY p.date_applied DESC) AS rn
          FROM permits p JOIN applicants a USING (applicant_id)) t
 WHERE rn = 1
 ORDER BY applicant_id;

\echo '--- Q7 Window function: rank districts by number of permits'
SELECT district, permits,
       RANK() OVER (ORDER BY permits DESC) AS rank
  FROM v_district_report
 WHERE permits > 0
 ORDER BY rank, district;

\echo '--- Q8 CASE: urgency of approved permits'
SELECT permit_id, details, expiry_date, days_left,
       CASE WHEN days_left < 0   THEN 'Overdue'
            WHEN days_left <= 30 THEN 'Renew now'
            WHEN days_left <= 90 THEN 'Renew soon'
            ELSE 'OK' END AS action
  FROM v_permit_details
 WHERE status IN ('Approved','Expired')
 ORDER BY days_left;

\echo '--- Q9 View: permits expiring within 30 days'
SELECT * FROM v_expiring_soon;

\echo '--- Q10 View: workload at each licensing office'
SELECT * FROM v_office_workload;

\echo '--- Q11 View: fees collected by permit type'
SELECT * FROM v_revenue_by_type;

\echo '--- Q12 Text search: permits mentioning "pharmacy"'
SELECT permit_id, full_name, details, status
  FROM v_permit_details WHERE details ILIKE '%pharmacy%';

\echo '--- Q13 Date functions: applications per month'
SELECT to_char(date_trunc('month', date_applied), 'YYYY-MM') AS month, COUNT(*) AS applications
  FROM permits GROUP BY 1 ORDER BY 1;

\echo '--- Q14 Stored functions: fee and days left'
SELECT fn_permit_fee('building') AS building_fee,
       fn_days_to_expiry('PRM-001') AS days_left_prm001,
       fn_office_handles('Building Control Unit', 'business') AS wrong_office;

\echo '--- Q15 Audit trail written by the trigger'
SELECT permit_id, old_status, new_status, note, office_name
  FROM permit_history WHERE permit_id IN ('PRM-005') ORDER BY history_id;
