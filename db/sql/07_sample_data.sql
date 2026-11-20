-- 07_sample_data.sql : realistic but FICTIONAL sample data for testing and the demo
-- Run after scripts 01 to 06:  psql -U postgres -d permits_db -f 07_sample_data.sql
-- Dates are relative to today, so expiry examples always stay realistic.
-- (The triggers run on these inserts too: history rows are created automatically.)

INSERT INTO applicants (applicant_id, full_name, phone, district, date_registered) VALUES
 ('APP-001','Aminata Kamara',   '+232 76 123456','Western Area Urban', CURRENT_DATE - 360),
 ('APP-002','Mohamed Sesay',    '+232 77 234567','Bo',                 CURRENT_DATE - 410),
 ('APP-003','Fatmata Bangura',  '+232 78 345678','Kenema',             CURRENT_DATE - 120),
 ('APP-004','Ibrahim Conteh',   '+232 79 456789','Kono',               CURRENT_DATE - 110),
 ('APP-005','Mariama Jalloh',   '+232 76 567890','Port Loko',          CURRENT_DATE - 360),
 ('APP-006','Abdul Rahman Turay','+232 77 678901','Bombali',           CURRENT_DATE - 310),
 ('APP-007','Hawa Koroma',      '+232 78 789012','Tonkolili',          CURRENT_DATE - 30),
 ('APP-008','Sulaiman Kargbo',  '+232 79 890123','Kambia',             CURRENT_DATE - 345),
 ('APP-009','Isatu Mansaray',   '+232 76 901234','Western Area Rural', CURRENT_DATE - 70),
 ('APP-010','Alie Bundu',       '+232 77 012345','Moyamba',            CURRENT_DATE - 20),
 ('APP-011','Zainab Fofanah',   '+232 78 112233','Kailahun',           CURRENT_DATE - 15),
 ('APP-012','Joseph Lahai',     '+232 79 223344','Pujehun',            CURRENT_DATE - 130)
ON CONFLICT (applicant_id) DO NOTHING;

INSERT INTO permits (permit_id, applicant_id, kind, details, status, office_name,
                     date_applied, issue_date, expiry_date) VALUES
 ('PRM-001','APP-001','business','Kamara General Stores','Approved','Business Licensing Unit', CURRENT_DATE-350, CURRENT_DATE-345, CURRENT_DATE+20),
 ('PRM-002','APP-002','building','Plot 14, Aberdeen Ridge, Bo','Under Review','Building Control Unit', CURRENT_DATE-12, NULL, NULL),
 ('PRM-003','APP-003','general', 'Weekend market stall, Kenema','Under Review','General Permits Desk', CURRENT_DATE-6, NULL, NULL),
 ('PRM-004','APP-001','general', 'Street food stall, Lumley','Rejected','General Permits Desk', CURRENT_DATE-28, NULL, NULL),
 ('PRM-005','APP-002','business','Sesay Hardware','Approved','Business Licensing Unit', CURRENT_DATE-400, CURRENT_DATE-395, CURRENT_DATE-30),
 ('PRM-006','APP-003','business','Bangura Pharmacy','Submitted',NULL, CURRENT_DATE-2, NULL, NULL),
 ('PRM-007','APP-004','general', 'Cultural festival stage, Kono','Approved','General Permits Desk', CURRENT_DATE-100, CURRENT_DATE-95, CURRENT_DATE+270),
 ('PRM-008','APP-005','building','Guest house extension, Port Loko town','Approved','Building Control Unit', CURRENT_DATE-200, CURRENT_DATE-190, CURRENT_DATE+905),
 ('PRM-009','APP-006','business','Turay Rice Mill','Approved','Business Licensing Unit', CURRENT_DATE-300, CURRENT_DATE-290, CURRENT_DATE+75),
 ('PRM-010','APP-007','business','Koroma Tailoring Centre','Submitted',NULL, CURRENT_DATE-1, NULL, NULL),
 ('PRM-011','APP-008','general', 'Weekly market trading, Kambia','Approved','General Permits Desk', CURRENT_DATE-340, CURRENT_DATE-335, CURRENT_DATE+30),
 ('PRM-012','APP-009','building','Two-storey house, Waterloo','Rejected','Building Control Unit', CURRENT_DATE-60, NULL, NULL),
 ('PRM-013','APP-010','business','Bundu Fuel Station','Under Review','Business Licensing Unit', CURRENT_DATE-9, NULL, NULL),
 ('PRM-014','APP-011','general', 'Community football tournament','Submitted',NULL, CURRENT_DATE-4, NULL, NULL),
 ('PRM-015','APP-012','business','Lahai Fishing Supplies','Approved','Business Licensing Unit', CURRENT_DATE-120, CURRENT_DATE-110, CURRENT_DATE+255),
 ('PRM-016','APP-005','business','Jalloh Bakery','Approved','Business Licensing Unit', CURRENT_DATE-355, CURRENT_DATE-350, CURRENT_DATE+15),
 ('PRM-017','APP-001','building','Warehouse, Wellington Industrial Estate','Submitted',NULL, CURRENT_DATE-5, NULL, NULL),
 ('PRM-018','APP-004','business','Conteh Mining Supplies','Rejected','Business Licensing Unit', CURRENT_DATE-45, NULL, NULL),
 ('PRM-019','APP-006','general', 'Livestock market stall, Makeni','Approved','General Permits Desk', CURRENT_DATE-50, CURRENT_DATE-45, CURRENT_DATE+320),
 ('PRM-020','APP-009','business','Mansaray Pharmacy','Under Review','Business Licensing Unit', CURRENT_DATE-3, NULL, NULL)
ON CONFLICT (permit_id) DO NOTHING;

-- Housekeeping the application also does at start-up: expire old approved permits
SELECT fn_expire_overdue_permits() AS permits_expired;
