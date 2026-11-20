-- 06_views.sql : saved queries the application and staff can use like tables
-- Safe to repeat (CREATE OR REPLACE).

-- Everything about a permit in one row (joins 4 tables)
CREATE OR REPLACE VIEW v_permit_details AS
SELECT p.permit_id,
       p.applicant_id,
       a.full_name,
       a.district,
       d.region,
       pt.type_name,
       p.kind,
       p.details,
       p.status,
       p.office_name,
       p.date_applied,
       p.issue_date,
       p.expiry_date,
       pt.base_fee                      AS fee,
       p.expiry_date - CURRENT_DATE     AS days_left
  FROM permits p
  JOIN applicants   a  ON a.applicant_id  = p.applicant_id
  JOIN districts    d  ON d.district_name = a.district
  JOIN permit_types pt ON pt.kind         = p.kind;

-- Number of permits in each status (including statuses with zero permits)
CREATE OR REPLACE VIEW v_status_summary AS
SELECT s.status, COUNT(p.permit_id) AS permits
  FROM (VALUES (1,'Submitted'), (2,'Under Review'), (3,'Approved'),
               (4,'Rejected'),  (5,'Expired')) AS s(ord, status)
  LEFT JOIN permits p ON p.status = s.status
 GROUP BY s.ord, s.status
 ORDER BY s.ord;

-- Approved permits that expire within 30 days
CREATE OR REPLACE VIEW v_expiring_soon AS
SELECT permit_id, full_name, type_name, details, expiry_date, days_left
  FROM v_permit_details
 WHERE status = 'Approved' AND days_left BETWEEN 0 AND 30
 ORDER BY expiry_date;

-- Work waiting at each office
CREATE OR REPLACE VIEW v_office_workload AS
SELECT o.name AS office,
       COUNT(p.permit_id) FILTER (WHERE p.status IN ('Submitted','Under Review')) AS open_permits,
       COUNT(p.permit_id) FILTER (WHERE p.status = 'Approved')                    AS approved,
       COUNT(p.permit_id) FILTER (WHERE p.status = 'Rejected')                    AS rejected
  FROM offices o
  JOIN office_permit_types opt ON opt.office_name = o.name
  LEFT JOIN permits p          ON p.kind = opt.kind
 GROUP BY o.name
 ORDER BY o.name;

-- Fees from approved permits, by permit type
CREATE OR REPLACE VIEW v_revenue_by_type AS
SELECT pt.type_name,
       COUNT(p.permit_id)              AS approved_permits,
       COALESCE(SUM(pt.base_fee), 0)   AS total_fees_le
  FROM permit_types pt
  LEFT JOIN permits p ON p.kind = pt.kind AND p.status = 'Approved'
 GROUP BY pt.type_name, pt.kind
 ORDER BY pt.kind;

-- Activity by district (for planning)
CREATE OR REPLACE VIEW v_district_report AS
SELECT d.region,
       d.district_name AS district,
       COUNT(DISTINCT a.applicant_id) AS applicants,
       COUNT(p.permit_id)             AS permits,
       COUNT(p.permit_id) FILTER (WHERE p.status = 'Approved') AS approved
  FROM districts d
  LEFT JOIN applicants a ON a.district = d.district_name
  LEFT JOIN permits p    ON p.applicant_id = a.applicant_id
 GROUP BY d.region, d.district_name
 ORDER BY d.region, d.district_name;
