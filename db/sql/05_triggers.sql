-- 05_triggers.sql : rules the database enforces by itself, whichever program
-- (Python, psql, another tool) changes the data. Safe to repeat.
--
-- Firing order for BEFORE triggers on one table is alphabetical by name,
-- so the names start with a number to make the order explicit.

-- ===========================================================================
-- 1. Only allowed status changes (the workflow state machine)
-- ===========================================================================
CREATE OR REPLACE FUNCTION tf_validate_status_transition() RETURNS TRIGGER
LANGUAGE plpgsql AS $$
BEGIN
    IF NOT (
        (OLD.status = 'Submitted'    AND NEW.status IN ('Under Review','Rejected'))
     OR (OLD.status = 'Under Review' AND NEW.status IN ('Approved','Rejected'))
     OR (OLD.status = 'Approved'     AND NEW.status = 'Expired')
     OR (OLD.status = 'Expired'      AND NEW.status = 'Approved'
                                     AND NEW.expiry_date > OLD.expiry_date)  -- renewal
    ) THEN
        RAISE EXCEPTION 'A % permit cannot become % (permit %)',
                        OLD.status, NEW.status, OLD.permit_id
              USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_1_validate_transition ON permits;
CREATE TRIGGER trg_1_validate_transition
    BEFORE UPDATE OF status ON permits
    FOR EACH ROW WHEN (OLD.status IS DISTINCT FROM NEW.status)
    EXECUTE FUNCTION tf_validate_status_transition();

-- ===========================================================================
-- 2. Set issue and expiry dates automatically when a permit is approved
-- ===========================================================================
CREATE OR REPLACE FUNCTION tf_set_approval_dates() RETURNS TRIGGER
LANGUAGE plpgsql AS $$
BEGIN
    NEW.issue_date  := COALESCE(NEW.issue_date, CURRENT_DATE);
    NEW.expiry_date := COALESCE(
        NEW.expiry_date,
        NEW.issue_date + 365 * (SELECT validity_years FROM permit_types
                                 WHERE kind = NEW.kind));
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_2_set_approval_dates ON permits;
CREATE TRIGGER trg_2_set_approval_dates
    BEFORE UPDATE OF status ON permits
    FOR EACH ROW
    WHEN (OLD.status = 'Under Review' AND NEW.status = 'Approved')
    EXECUTE FUNCTION tf_set_approval_dates();

-- ===========================================================================
-- 3. An office may only be attached to permit kinds it is responsible for
-- ===========================================================================
CREATE OR REPLACE FUNCTION tf_check_office_responsibility() RETURNS TRIGGER
LANGUAGE plpgsql AS $$
BEGIN
    IF NOT fn_office_handles(NEW.office_name, NEW.kind) THEN
        RAISE EXCEPTION '% does not handle % permits', NEW.office_name, NEW.kind
              USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_3_check_office ON permits;
CREATE TRIGGER trg_3_check_office
    BEFORE INSERT OR UPDATE OF office_name ON permits
    FOR EACH ROW WHEN (NEW.office_name IS NOT NULL)
    EXECUTE FUNCTION tf_check_office_responsibility();

-- ===========================================================================
-- 4. No duplicate live applications (same applicant, same type, same details)
-- ===========================================================================
CREATE OR REPLACE FUNCTION tf_prevent_duplicate_application() RETURNS TRIGGER
LANGUAGE plpgsql AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM permits
                WHERE applicant_id = NEW.applicant_id
                  AND kind = NEW.kind
                  AND lower(details) = lower(NEW.details)
                  AND status IN ('Submitted','Under Review','Approved')) THEN
        RAISE EXCEPTION 'Applicant % already has a live % application for "%"',
                        NEW.applicant_id, NEW.kind, NEW.details
              USING ERRCODE = 'unique_violation';
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_4_prevent_duplicate ON permits;
CREATE TRIGGER trg_4_prevent_duplicate
    BEFORE INSERT ON permits
    FOR EACH ROW EXECUTE FUNCTION tf_prevent_duplicate_application();

-- ===========================================================================
-- 5. Audit trail: every creation and change is written to permit_history
-- ===========================================================================
CREATE OR REPLACE FUNCTION tf_log_permit_history() RETURNS TRIGGER
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO permit_history (permit_id, old_status, new_status, office_name, note)
        VALUES (NEW.permit_id, NULL, NEW.status, NEW.office_name,
                CASE WHEN NEW.status = 'Submitted' THEN 'Application submitted'
                     ELSE 'Record created with status ' || NEW.status END);
    ELSIF OLD.status = 'Expired' AND NEW.status = 'Approved' THEN
        INSERT INTO permit_history (permit_id, old_status, new_status, office_name, note)
        VALUES (NEW.permit_id, OLD.status, NEW.status, NEW.office_name,
                'Renewed until ' || NEW.expiry_date);
    ELSIF NEW.status IS DISTINCT FROM OLD.status THEN
        INSERT INTO permit_history (permit_id, old_status, new_status, office_name, note)
        VALUES (NEW.permit_id, OLD.status, NEW.status, NEW.office_name,
                'Status ' || OLD.status || ' -> ' || NEW.status);
    ELSIF NEW.expiry_date IS DISTINCT FROM OLD.expiry_date THEN
        INSERT INTO permit_history (permit_id, old_status, new_status, office_name, note)
        VALUES (NEW.permit_id, OLD.status, NEW.status, NEW.office_name,
                'Renewed until ' || NEW.expiry_date);
    ELSIF NEW.details IS DISTINCT FROM OLD.details THEN
        INSERT INTO permit_history (permit_id, old_status, new_status, office_name, note)
        VALUES (NEW.permit_id, OLD.status, NEW.status, NEW.office_name,
                'Details updated');
    END IF;
    RETURN NULL;                       -- AFTER trigger: return value is ignored
END $$;

DROP TRIGGER IF EXISTS trg_5_log_history ON permits;
CREATE TRIGGER trg_5_log_history
    AFTER INSERT OR UPDATE ON permits
    FOR EACH ROW EXECUTE FUNCTION tf_log_permit_history();
