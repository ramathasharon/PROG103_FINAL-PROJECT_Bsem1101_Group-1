-- 01_tables.sql : tables, keys, relationships and constraints
-- Digital Permit & License Management System (PostgreSQL 14 or newer)
-- Safe to run many times: every statement uses IF NOT EXISTS.
--
-- Normalisation (see docs/normalization.md): every table is in 3NF.
--   * no repeating groups or arrays (1NF): offices and permit types are linked
--     through the junction table office_permit_types
--   * no partial dependencies (2NF): every non-key column depends on the whole key
--   * no transitive dependencies (3NF): district -> region, permit kind -> fee
--     and validity live in their own tables
-- Privacy (DPG): NO column stores a national ID number, address or photo.

-- ---------------------------------------------------------------- districts
CREATE TABLE IF NOT EXISTS districts (
    district_name  TEXT PRIMARY KEY,
    region         TEXT NOT NULL
        CHECK (region IN ('Northern','North West','Southern','Eastern','Western Area'))
);

-- ------------------------------------------------------------- permit_types
CREATE TABLE IF NOT EXISTS permit_types (
    kind            TEXT PRIMARY KEY
        CHECK (kind ~ '^[a-z]+$'),                      -- general / business / building
    type_name       TEXT NOT NULL UNIQUE,
    details_label   TEXT NOT NULL,                      -- text shown in the GUI form
    base_fee        NUMERIC(10,2) NOT NULL CHECK (base_fee >= 0),   -- Leones (Le)
    validity_years  SMALLINT NOT NULL CHECK (validity_years BETWEEN 1 AND 10)
);

-- ------------------------------------------------------------------ offices
CREATE TABLE IF NOT EXISTS offices (
    name  TEXT PRIMARY KEY
);

-- Many-to-many: which office decides on which permit kind
CREATE TABLE IF NOT EXISTS office_permit_types (
    office_name  TEXT NOT NULL REFERENCES offices(name)
                      ON UPDATE CASCADE ON DELETE CASCADE,
    kind         TEXT NOT NULL REFERENCES permit_types(kind)
                      ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (office_name, kind)
);

-- --------------------------------------------------------------- applicants
CREATE TABLE IF NOT EXISTS applicants (
    applicant_id     TEXT PRIMARY KEY
        CHECK (applicant_id ~ '^APP-[0-9]{3,}$'),                -- APP-001
    full_name        TEXT NOT NULL
        CHECK (char_length(full_name) BETWEEN 3 AND 60),
    phone            TEXT NOT NULL
        CHECK (phone ~ '^\+?[0-9][0-9 -]{6,18}$'),
    district         TEXT NOT NULL REFERENCES districts(district_name)
                          ON UPDATE CASCADE,
    date_registered  DATE NOT NULL DEFAULT CURRENT_DATE
);

-- ------------------------------------------------------------------ permits
CREATE TABLE IF NOT EXISTS permits (
    permit_id     TEXT PRIMARY KEY
        CHECK (permit_id ~ '^PRM-[0-9]{3,}$'),                   -- PRM-001
    applicant_id  TEXT NOT NULL
        REFERENCES applicants(applicant_id) ON DELETE RESTRICT,
    kind          TEXT NOT NULL REFERENCES permit_types(kind) ON UPDATE CASCADE,
    details       TEXT NOT NULL
        CHECK (char_length(details) BETWEEN 3 AND 120),
    status        TEXT NOT NULL DEFAULT 'Submitted'
        CHECK (status IN ('Submitted','Under Review','Approved','Rejected','Expired')),
    office_name   TEXT REFERENCES offices(name) ON UPDATE CASCADE,
    date_applied  DATE NOT NULL DEFAULT CURRENT_DATE,
    issue_date    DATE,
    expiry_date   DATE,
    CHECK (expiry_date IS NULL OR issue_date IS NULL OR expiry_date >= issue_date),
    CHECK (status NOT IN ('Approved','Expired') OR expiry_date IS NOT NULL)
);

-- audit trail: one row per change, filled automatically by a trigger
CREATE TABLE IF NOT EXISTS permit_history (
    history_id   BIGSERIAL PRIMARY KEY,
    permit_id    TEXT NOT NULL REFERENCES permits(permit_id) ON DELETE CASCADE,
    old_status   TEXT,
    new_status   TEXT NOT NULL,
    office_name  TEXT,
    note         TEXT NOT NULL,
    changed_at   TIMESTAMP NOT NULL DEFAULT now()
);
