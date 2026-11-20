-- 04_functions_procedures.sql : reusable business logic stored in the database
-- Needs PostgreSQL 14+ (procedures with OUT parameters). Safe to repeat.

-- ---------------------------------------------------------------------------
-- fn_next_id: next readable ID for a table, e.g. APP-004 or PRM-007
-- An advisory lock stops two sessions from receiving the same number.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_next_id(p_prefix TEXT) RETURNS TEXT
LANGUAGE plpgsql AS $$
DECLARE
    v_max INTEGER;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtext('next_id_' || p_prefix));
    IF p_prefix = 'APP' THEN
        SELECT COALESCE(MAX(substring(applicant_id FROM 5)::INTEGER), 0)
          INTO v_max FROM applicants;
    ELSIF p_prefix = 'PRM' THEN
        SELECT COALESCE(MAX(substring(permit_id FROM 5)::INTEGER), 0)
          INTO v_max FROM permits;
    ELSE
        RAISE EXCEPTION 'Unknown ID prefix: %', p_prefix;
    END IF;
    RETURN p_prefix || '-' || lpad((v_max + 1)::TEXT, 3, '0');
END $$;

-- ---------------------------------------------------------------------------
-- fn_permit_fee: fee for a permit kind
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_permit_fee(p_kind TEXT) RETURNS NUMERIC
LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_fee NUMERIC;
BEGIN
    SELECT base_fee INTO v_fee FROM permit_types WHERE kind = p_kind;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Unknown permit kind: %', p_kind;
    END IF;
    RETURN v_fee;
END $$;

-- ---------------------------------------------------------------------------
-- fn_office_handles: is this office responsible for this permit kind?
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_office_handles(p_office TEXT, p_kind TEXT)
RETURNS BOOLEAN LANGUAGE sql STABLE AS $$
    SELECT EXISTS (SELECT 1 FROM office_permit_types
                    WHERE office_name = p_office AND kind = p_kind);
$$;

-- ---------------------------------------------------------------------------
-- fn_days_to_expiry: days left on a permit (negative = already past), NULL if
-- the permit has no expiry date yet
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_days_to_expiry(p_permit_id TEXT) RETURNS INTEGER
LANGUAGE sql STABLE AS $$
    SELECT expiry_date - CURRENT_DATE FROM permits WHERE permit_id = p_permit_id;
$$;

-- ---------------------------------------------------------------------------
-- fn_expire_overdue_permits: mark approved permits whose date has passed as
-- Expired and return how many were changed. The application calls this at
-- start-up and on Refresh.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_expire_overdue_permits() RETURNS INTEGER
LANGUAGE plpgsql AS $$
DECLARE
    v_count INTEGER;
BEGIN
    WITH changed AS (
        UPDATE permits SET status = 'Expired'
         WHERE status = 'Approved' AND expiry_date < CURRENT_DATE
        RETURNING 1)
    SELECT count(*) INTO v_count FROM changed;
    RETURN v_count;
END $$;

-- ---------------------------------------------------------------------------
-- sp_register_applicant_and_permit: register a new applicant AND file their
-- first permit in ONE transaction. If the permit is refused (for example a
-- bad details text) the applicant is not saved either: all or nothing.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE sp_register_applicant_and_permit(
    IN  p_name      TEXT,
    IN  p_phone     TEXT,
    IN  p_district  TEXT,
    IN  p_kind      TEXT,
    IN  p_details   TEXT,
    OUT o_applicant_id TEXT,
    OUT o_permit_id    TEXT)
LANGUAGE plpgsql AS $$
BEGIN
    o_applicant_id := fn_next_id('APP');
    INSERT INTO applicants (applicant_id, full_name, phone, district)
    VALUES (o_applicant_id, p_name, p_phone, p_district);

    o_permit_id := fn_next_id('PRM');
    INSERT INTO permits (permit_id, applicant_id, kind, details)
    VALUES (o_permit_id, o_applicant_id, p_kind, p_details);
END $$;

-- ---------------------------------------------------------------------------
-- sp_decide_permit: an office reviews, approves, rejects or renews a permit.
-- Decisions: 'review' | 'approve' | 'reject' | 'renew'
-- The triggers (05_triggers.sql) enforce the status rules and write history.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE sp_decide_permit(
    IN p_permit_id TEXT,
    IN p_office    TEXT,
    IN p_decision  TEXT)
LANGUAGE plpgsql AS $$
DECLARE
    v_permit permits%ROWTYPE;
    v_days   INTEGER;
BEGIN
    SELECT * INTO v_permit FROM permits WHERE permit_id = p_permit_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Permit % does not exist', p_permit_id;
    END IF;
    IF NOT fn_office_handles(p_office, v_permit.kind) THEN
        RAISE EXCEPTION '% does not handle % permits', p_office, v_permit.kind;
    END IF;

    CASE lower(p_decision)
        WHEN 'review' THEN
            UPDATE permits SET status = 'Under Review', office_name = p_office
             WHERE permit_id = p_permit_id;
        WHEN 'approve' THEN
            UPDATE permits SET status = 'Approved', office_name = p_office
             WHERE permit_id = p_permit_id;       -- dates set by trigger
        WHEN 'reject' THEN
            UPDATE permits SET status = 'Rejected', office_name = p_office
             WHERE permit_id = p_permit_id;
        WHEN 'renew' THEN
            IF v_permit.status NOT IN ('Approved','Expired') THEN
                RAISE EXCEPTION 'Only approved or expired permits can be renewed';
            END IF;
            SELECT validity_years * 365 INTO v_days
              FROM permit_types WHERE kind = v_permit.kind;
            UPDATE permits
               SET expiry_date = GREATEST(CURRENT_DATE, expiry_date) + v_days,
                   status = 'Approved', office_name = p_office
             WHERE permit_id = p_permit_id;
        ELSE
            RAISE EXCEPTION 'Unknown decision "%". Use review, approve, reject or renew',
                            p_decision;
    END CASE;
END $$;
