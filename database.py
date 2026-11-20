"""
database.py
-----------
PostgreSQL layer (psycopg2). Only this file talks to the database, so the
rest of the program never contains SQL.

Connection settings come from environment variables so that no password is
ever written in the source code or pushed to GitHub:

    PGHOST (default localhost)   PGPORT (default 5432)
    PGDATABASE (default permits_db)
    PGUSER (default postgres)    PGPASSWORD (no default)
"""

import functools
import os
from pathlib import Path

import psycopg2
import psycopg2.extras

from models import Applicant, LicensingOffice, Permit

# Scripts run at start-up, in this order (all safe to repeat). They live in
# db/sql/ together with the sample data; queries and tests are in db/queries, db/tests.
SQL_FOLDER = Path(__file__).with_name("db") / "sql"
SETUP_SCRIPTS = ("01_tables.sql", "02_reference_data.sql", "03_indexes.sql",
                 "04_functions_procedures.sql", "05_triggers.sql", "06_views.sql")


class DatabaseError(Exception):
    """A clean, readable database problem (no long PostgreSQL context lines)."""


def translate_errors(method):
    """Decorator: turn psycopg2 errors into DatabaseError with a short message.

    The database triggers raise messages such as "A Rejected permit cannot
    become Under Review"; this shows exactly that text in the GUI.
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except psycopg2.Error as error:
            message = (error.diag.message_primary if error.diag else None) or str(error)
            raise DatabaseError(message) from error
    return wrapper


def config_from_env():
    return {
        "host": os.environ.get("PGHOST", "localhost"),
        "port": os.environ.get("PGPORT", "5432"),
        "dbname": os.environ.get("PGDATABASE", "permits_db"),
        "user": os.environ.get("PGUSER", "postgres"),
        "password": os.environ.get("PGPASSWORD", ""),
    }


class Database:
    """Thin wrapper: one connection, one method per database operation.

    Every method uses `with self._conn`, which commits on success and rolls
    back automatically if anything fails (a transaction).
    """

    def __init__(self, **config):
        self._config = config or config_from_env()
        self._conn = psycopg2.connect(connect_timeout=5, **self._config)

    # ---- setup --------------------------------------------------------------
    @translate_errors
    def create_tables(self):
        """Run the setup scripts in db/ (safe to repeat)."""
        with self._conn, self._conn.cursor() as cur:
            for name in SETUP_SCRIPTS:
                cur.execute((SQL_FOLDER / name).read_text(encoding="utf-8"))

    # ---- Applicants: Create / Read / Update / Delete ------------------------
    @translate_errors
    def insert_applicant(self, a):
        sql = """INSERT INTO applicants
                 (applicant_id, full_name, phone, district, date_registered)
                 VALUES (%s,%s,%s,%s,%s)"""
        with self._conn, self._conn.cursor() as cur:
            cur.execute(sql, (a.applicant_id, a.full_name, a.phone,
                              a.district, a.date_registered))

    @translate_errors
    def fetch_applicants(self):
        with self._conn, self._conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM applicants ORDER BY applicant_id")
            return [Applicant.from_row(row) for row in cur.fetchall()]

    @translate_errors
    def update_applicant(self, a):
        sql = """UPDATE applicants SET full_name=%s, phone=%s, district=%s
                 WHERE applicant_id=%s"""
        with self._conn, self._conn.cursor() as cur:
            cur.execute(sql, (a.full_name, a.phone, a.district, a.applicant_id))

    @translate_errors
    def delete_applicant(self, applicant_id):
        with self._conn, self._conn.cursor() as cur:
            cur.execute("DELETE FROM applicants WHERE applicant_id=%s",
                        (applicant_id,))

    # ---- Permits: Create / Read / Update / Delete ---------------------------
    @translate_errors
    def insert_permit(self, p):
        sql = """INSERT INTO permits
                 (permit_id, applicant_id, kind, details, status, office_name,
                  date_applied, issue_date, expiry_date)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
        with self._conn, self._conn.cursor() as cur:
            cur.execute(sql, (p.permit_id, p.applicant_id, p.kind, p.details,
                              p.status, self._office_or_none(p),
                              p.date_applied, p.issue_date, p.expiry_date))

    @translate_errors
    def fetch_permits(self):
        with self._conn, self._conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM permits ORDER BY permit_id")
            return [Permit.from_row(row) for row in cur.fetchall()]

    @translate_errors
    def update_permit(self, p):
        sql = """UPDATE permits
                 SET details=%s, status=%s, office_name=%s,
                     issue_date=%s, expiry_date=%s
                 WHERE permit_id=%s"""
        with self._conn, self._conn.cursor() as cur:
            cur.execute(sql, (p.details, p.status, self._office_or_none(p),
                              p.issue_date, p.expiry_date, p.permit_id))

    @translate_errors
    def delete_permit(self, permit_id):
        with self._conn, self._conn.cursor() as cur:
            cur.execute("DELETE FROM permits WHERE permit_id=%s", (permit_id,))

    # ---- Offices (read only) -------------------------------------------------
    @translate_errors
    def fetch_offices(self):
        """Offices and the permit kinds they handle (many-to-many junction table)."""
        sql = """SELECT o.name, array_agg(opt.kind ORDER BY opt.kind)
                   FROM offices o
                   JOIN office_permit_types opt ON opt.office_name = o.name
                  GROUP BY o.name ORDER BY o.name"""
        with self._conn, self._conn.cursor() as cur:
            cur.execute(sql)
            return [LicensingOffice(name, handles)
                    for name, handles in cur.fetchall()]

    # ---- Stored function and audit trail -------------------------------------
    @translate_errors
    def expire_overdue(self):
        """Call fn_expire_overdue_permits(): returns how many permits expired."""
        with self._conn, self._conn.cursor() as cur:
            cur.execute("SELECT fn_expire_overdue_permits()")
            return cur.fetchone()[0]

    @translate_errors
    def fetch_history(self, permit_id):
        """Audit trail written by the database trigger: [(time, text), ...]."""
        sql = """SELECT to_char(changed_at, 'YYYY-MM-DD HH24:MI:SS'), note, office_name
                   FROM permit_history WHERE permit_id = %s
                  ORDER BY history_id"""
        with self._conn, self._conn.cursor() as cur:
            cur.execute(sql, (permit_id,))
            return [(stamp, note + (f" ({office})" if office else ""))
                    for stamp, note, office in cur.fetchall()]

    # ---- helpers --------------------------------------------------------------
    @staticmethod
    def _office_or_none(p):
        return None if p.office == "Unassigned" else p.office

    def close(self):
        self._conn.close()
