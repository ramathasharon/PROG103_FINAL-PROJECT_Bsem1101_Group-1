"""
models.py
---------
Domain classes for the Digital Permit & License Management System
(PROG211 Object-Oriented Programming 1 group project).

OOP concepts demonstrated here
  * Abstract base classes ...... Record (describe, to_dict) and
                                 Permit (required_documents)
  * Encapsulation .............. private attributes, @property getters and
                                 validating setters in Applicant and Permit
  * Single inheritance ......... Record -> Permit -> BusinessPermit
  * Multiple inheritance ....... Permit(Record, Auditable)
  * Hierarchical inheritance ... Permit has three children (General,
                                 Business, Building); Record has three
                                 children (Applicant, Permit, LicensingOffice)
  * Polymorphism ............... describe(), required_documents(), fee()
                                 behave differently in each permit class
  * Instance / class / static .. approve(); create(), from_row();
                                 is_valid_phone(), is_valid_name()
  * Data structures ............ dicts {id: object} in PermitRegistry,
                                 TRANSITIONS dict, tuples for constants

DPG note (privacy / data minimisation): an Applicant stores only a name,
a phone number and a district. No national ID, no home address, no photo.
"""

import re
from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta

# ---- Tuples: constants that must never change -------------------------------
STATUSES = ("Submitted", "Under Review", "Approved", "Rejected", "Expired")
DISTRICTS = (
    "Bo", "Bombali", "Bonthe", "Falaba", "Kailahun", "Kambia", "Karene",
    "Kenema", "Koinadugu", "Kono", "Moyamba", "Port Loko", "Pujehun",
    "Tonkolili", "Western Area Rural", "Western Area Urban",
)

# ---- Dictionary: which status changes are allowed (a tiny state machine) ----
TRANSITIONS = {
    "Submitted": ("Under Review", "Rejected"),
    "Under Review": ("Approved", "Rejected"),
    "Approved": ("Expired",),
    "Rejected": (),
    "Expired": (),          # an expired permit can only be renewed
}


# =============================================================================
# Abstract base class
# =============================================================================
class Record(ABC):
    """Anything stored by the system. Cannot be instantiated directly."""

    PREFIX = "REC"           # class attribute: first part of every ID
    _counters = {}           # class attribute shared by ALL records

    def __init__(self, record_id):
        self._record_id = record_id   # private: read through the property

    @property
    def record_id(self):
        """Read-only: an ID must never change after creation."""
        return self._record_id

    @abstractmethod
    def describe(self):
        """Return a one-line human-readable summary."""

    @abstractmethod
    def to_dict(self):
        """Return the record as a dictionary (used by the GUI)."""

    # ---- class methods: unique, readable IDs (APP-001, PRM-001 ...) ---------
    @classmethod
    def next_id(cls):
        n = Record._counters.get(cls.PREFIX, 0) + 1
        Record._counters[cls.PREFIX] = n
        return f"{cls.PREFIX}-{n:03d}"

    @classmethod
    def sync_counter(cls, ids):
        """Continue numbering after the highest ID already stored.

        Without this, restarting the program would reuse APP-001 and clash
        with records that are already in PostgreSQL.
        """
        highest = 0
        for rid in ids:
            match = re.fullmatch(rf"{cls.PREFIX}-(\d+)", rid)
            if match:
                highest = max(highest, int(match.group(1)))
        Record._counters[cls.PREFIX] = max(
            Record._counters.get(cls.PREFIX, 0), highest)

    @classmethod
    def release_id(cls, record_id):
        """Give back the most recent ID when saving failed, so that a refused
        record does not leave a gap in the numbering."""
        match = re.fullmatch(rf"{cls.PREFIX}-(\d+)", record_id)
        if match and Record._counters.get(cls.PREFIX) == int(match.group(1)):
            Record._counters[cls.PREFIX] -= 1

    def __str__(self):
        return self.describe()


# =============================================================================
# Mixin used for multiple inheritance
# =============================================================================
class Auditable:
    """Mixin that keeps a timestamped log of what happened to an object."""

    def _init_audit(self):
        self._history = []   # list of (timestamp, message) tuples

    def log(self, message):
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._history.append((stamp, message))

    @property
    def history(self):
        return tuple(self._history)   # tuple copy: callers cannot edit the log


# =============================================================================
# Applicant
# =============================================================================
class Applicant(Record):
    """A person or business owner who applies for permits."""

    PREFIX = "APP"

    def __init__(self, applicant_id, full_name, phone, district,
                 date_registered=None):
        super().__init__(applicant_id)
        self._full_name = None
        self._phone = None
        self._district = None
        self._date_registered = date_registered or date.today()
        # Going through the setters means validation always runs.
        self.full_name = full_name
        self.phone = phone
        self.district = district

    # ---- encapsulated attributes -------------------------------------------
    @property
    def applicant_id(self):
        return self._record_id

    @property
    def full_name(self):
        return self._full_name

    @full_name.setter
    def full_name(self, value):
        valid, message = Applicant.is_valid_name(value)
        if not valid:
            raise ValueError(message)
        self._full_name = " ".join(value.split())

    @property
    def phone(self):
        return self._phone

    @phone.setter
    def phone(self, value):
        valid, message = Applicant.is_valid_phone(value)
        if not valid:
            raise ValueError(message)
        self._phone = value.strip()

    @property
    def district(self):
        return self._district

    @district.setter
    def district(self, value):
        if value not in DISTRICTS:
            raise ValueError("Please choose a valid district.")
        self._district = value

    @property
    def date_registered(self):
        return self._date_registered

    # ---- static methods: need neither an object nor the class --------------
    @staticmethod
    def is_valid_name(text):
        """Returns a tuple (is_valid, message)."""
        text = " ".join((text or "").split())
        if not re.fullmatch(r"[A-Za-z][A-Za-z .'\-]{2,59}", text):
            return (False, "Name must be 3-60 letters (spaces, . ' - allowed).")
        return (True, "OK")

    @staticmethod
    def is_valid_phone(text):
        """Accepts 8-12 digits; spaces, + and - are allowed as separators."""
        text = (text or "").strip()
        if not re.fullmatch(r"\+?[0-9][0-9 \-]*", text):
            return (False, "Phone may contain only digits, spaces, + and -.")
        digits = re.sub(r"\D", "", text)
        if not 8 <= len(digits) <= 12:
            return (False, "Phone number must have 8 to 12 digits.")
        return (True, "OK")

    # ---- class methods ------------------------------------------------------
    @classmethod
    def create(cls, full_name, phone, district):
        """Factory: validate first, take the next ID only if validation passes."""
        obj = cls("PENDING", full_name, phone, district)
        obj._record_id = cls.next_id()
        return obj

    @classmethod
    def from_row(cls, row):
        return cls(row["applicant_id"], row["full_name"], row["phone"],
                   row["district"], row["date_registered"])

    # ---- implementations of the abstract methods ---------------------------
    def describe(self):
        return f"[{self.applicant_id}] {self.full_name} | {self.district}"

    def to_dict(self):
        return {"applicant_id": self.applicant_id, "full_name": self.full_name,
                "phone": self.phone, "district": self.district,
                "date_registered": self.date_registered.isoformat()}


# =============================================================================
# Permit: abstract, multiple inheritance (Record + Auditable)
# =============================================================================
class Permit(Record, Auditable):
    """A permit application. Abstract: only the three subclasses are created.

    Class attributes below are overridden by each subclass (polymorphism).
    """

    PREFIX = "PRM"
    KIND = "general"
    TYPE_NAME = "General Permit"
    DETAILS_LABEL = "Purpose"
    BASE_FEE = 100            # in Leones (Le)
    VALIDITY_YEARS = 1

    def __init__(self, permit_id, applicant_id, details, status="Submitted",
                 date_applied=None, issue_date=None, expiry_date=None,
                 office="Unassigned"):
        super().__init__(permit_id)
        self._init_audit()                      # from the Auditable mixin
        self._applicant_id = applicant_id
        self._details = None
        self._status = None
        self._office = office
        self._date_applied = date_applied or date.today()
        self._issue_date = issue_date
        self._expiry_date = expiry_date
        self.details = details                  # setter validates
        self.status = status                    # setter validates

    # ---- encapsulated attributes -------------------------------------------
    @property
    def permit_id(self):
        return self._record_id

    @property
    def applicant_id(self):
        return self._applicant_id

    @property
    def kind(self):
        return self.KIND

    @property
    def type_name(self):
        return self.TYPE_NAME

    @property
    def details(self):
        return self._details

    @details.setter
    def details(self, value):
        value = " ".join((value or "").split())
        if not 3 <= len(value) <= 120:
            raise ValueError(f"{self.DETAILS_LABEL} must be 3-120 characters.")
        self._details = value

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        if value not in STATUSES:
            raise ValueError(f"Status must be one of {STATUSES}")
        self._status = value

    @property
    def office(self):
        return self._office

    @office.setter
    def office(self, value):
        self._office = value

    @property
    def date_applied(self):
        return self._date_applied

    @property
    def issue_date(self):
        return self._issue_date

    @property
    def expiry_date(self):
        return self._expiry_date

    @property
    def can_edit(self):
        """Details can only change while the application is still open."""
        return self._status in ("Submitted", "Under Review")

    # ---- abstract + overridable behaviour (polymorphism) -------------------
    @abstractmethod
    def required_documents(self):
        """Return a tuple of documents the applicant must bring."""

    def fee(self):
        return self.BASE_FEE

    def validity_days(self):
        return 365 * self.VALIDITY_YEARS

    # ---- workflow (instance methods) ----------------------------------------
    def change_status(self, new_status):
        """Move to a new status, but only along an allowed path."""
        if new_status not in TRANSITIONS.get(self._status, ()):
            raise ValueError(
                f"A {self._status} permit cannot become {new_status}.")
        old = self._status
        self.status = new_status
        self.log(f"Status {old} -> {new_status}")

    def approve(self):
        """Approve and set issue/expiry dates from today."""
        self.change_status("Approved")
        self._issue_date = date.today()
        self._expiry_date = self._issue_date + timedelta(days=self.validity_days())

    def renew(self):
        """Extend an Approved or Expired permit by one validity period."""
        if self._status not in ("Approved", "Expired"):
            raise ValueError("Only approved or expired permits can be renewed.")
        start = max(date.today(), self._expiry_date or date.today())
        self._expiry_date = start + timedelta(days=self.validity_days())
        if self._status == "Expired":
            self._status = "Approved"
        self.log(f"Renewed until {self._expiry_date.isoformat()}")

    def refresh_expiry(self, today=None):
        """Mark an approved permit as Expired when its date has passed."""
        today = today or date.today()
        if (self._status == "Approved" and self._expiry_date
                and self._expiry_date < today):
            self.change_status("Expired")
            return True
        return False

    def days_left(self, today=None):
        if self._expiry_date is None:
            return None
        return (self._expiry_date - (today or date.today())).days

    # ---- implementations of Record's abstract methods ----------------------
    def describe(self):
        return (f"[{self.permit_id}] {self.TYPE_NAME} | {self.details} | "
                f"{self.status}")

    def to_dict(self):
        def iso(d):
            return d.isoformat() if d else ""
        return {"permit_id": self.permit_id, "applicant_id": self.applicant_id,
                "kind": self.kind, "type_name": self.TYPE_NAME,
                "details": self.details, "status": self.status,
                "office": self.office, "date_applied": iso(self.date_applied),
                "issue_date": iso(self.issue_date),
                "expiry_date": iso(self.expiry_date), "fee": self.fee()}

    # ---- class methods ------------------------------------------------------
    @classmethod
    def create(cls, applicant_id, details):
        """Factory. Because it uses cls, BusinessPermit.create(...) builds a
        BusinessPermit: the factory is polymorphic too."""
        obj = cls("PENDING", applicant_id, details)
        obj._record_id = cls.next_id()
        obj.log("Application submitted")
        return obj

    @classmethod
    def from_row(cls, row):
        """Rebuild the right subclass from a database row."""
        klass = PERMIT_CLASSES[row["kind"]]
        return klass(row["permit_id"], row["applicant_id"], row["details"],
                     row["status"], row["date_applied"], row["issue_date"],
                     row["expiry_date"], row["office_name"] or "Unassigned")


# =============================================================================
# Concrete permit types (hierarchical inheritance; single inheritance chain
# Record -> Permit -> BusinessPermit)
# =============================================================================
class GeneralPermit(Permit):
    """Small permits such as market trading or event permits."""
    KIND = "general"
    TYPE_NAME = "General Permit"
    DETAILS_LABEL = "Purpose"
    BASE_FEE = 100
    VALIDITY_YEARS = 1

    def required_documents(self):
        return ("Valid photo ID",)


class BusinessPermit(Permit):
    """Licence to run a shop, restaurant or other business."""
    KIND = "business"
    TYPE_NAME = "Business License"
    DETAILS_LABEL = "Business name"
    BASE_FEE = 500
    VALIDITY_YEARS = 1

    def required_documents(self):
        return ("Valid photo ID", "Business registration certificate",
                "Tax clearance certificate")

    def describe(self):                       # overrides, then extends parent
        return "BUSINESS " + super().describe()


class BuildingPermit(Permit):
    """Permission to construct or extend a building."""
    KIND = "building"
    TYPE_NAME = "Building Permit"
    DETAILS_LABEL = "Site / plot description"
    BASE_FEE = 1500
    VALIDITY_YEARS = 3

    def required_documents(self):
        return ("Valid photo ID", "Land title or lease", "Approved building plan",
                "Environmental clearance")

    def describe(self):
        return "BUILDING " + super().describe()


# Dictionary: kind stored in the database -> class to rebuild
PERMIT_CLASSES = {cls.KIND: cls for cls in
                  (GeneralPermit, BusinessPermit, BuildingPermit)}


# =============================================================================
# LicensingOffice: third child of Record
# =============================================================================
class LicensingOffice(Record):
    """A government office that decides on certain kinds of permit."""

    PREFIX = "OFF"

    def __init__(self, name, handles):
        super().__init__(name)
        self._name = name
        self._handles = tuple(handles)    # tuple: cannot be altered later

    @property
    def name(self):
        return self._name

    @property
    def handles(self):
        return self._handles

    def can_handle(self, permit):
        return permit.kind in self._handles

    def _act(self, permit, action, done_text):
        """Shared helper: check responsibility, run the action, report."""
        if not self.can_handle(permit):
            return (False, f"{self.name} does not handle {permit.type_name}s.")
        try:
            action()
        except ValueError as error:
            return (False, str(error))
        permit.office = self.name
        permit.log(f"{done_text} by {self.name}")
        return (True, f"{self.name}: {permit.permit_id} {done_text}.")

    def start_review(self, permit):
        return self._act(permit, lambda: permit.change_status("Under Review"),
                         "moved to review")

    def approve(self, permit):
        return self._act(permit, permit.approve, "approved")

    def reject(self, permit):
        return self._act(permit, lambda: permit.change_status("Rejected"),
                         "rejected")

    def renew(self, permit):
        return self._act(permit, permit.renew, "renewed")

    def describe(self):
        return f"{self.name} (handles: {', '.join(self._handles)})"

    def to_dict(self):
        return {"name": self.name, "handles": list(self._handles)}


# =============================================================================
# PermitRegistry: the in-memory dictionaries + add/update/delete/display
# =============================================================================
class PermitRegistry:
    """Keeps two dictionaries in step with the database:
         {applicant_id: Applicant}   and   {permit_id: Permit}

    `repository` is a Database object (database.py). It is optional, so the
    class also works with memory only (unit tests and offline mode).
    """

    def __init__(self, repository=None):
        self._applicants = {}
        self._permits = {}
        self._repo = repository

    # ---- loading ------------------------------------------------------------
    def load(self):
        """Fill the dictionaries from the database and fix the ID counters."""
        if self._repo is None:
            return
        self._repo.expire_overdue()   # stored function: old approved permits expire
        self._applicants = {a.applicant_id: a
                            for a in self._repo.fetch_applicants()}
        self._permits = {p.permit_id: p for p in self._repo.fetch_permits()}
        Applicant.sync_counter(self._applicants.keys())
        Permit.sync_counter(self._permits.keys())

    # ---- applicants (CRUD) ----------------------------------------------------
    def add_applicant(self, applicant):
        if self._repo is not None:
            try:
                self._repo.insert_applicant(applicant)
            except Exception:
                Applicant.release_id(applicant.applicant_id)
                raise
        self._applicants[applicant.applicant_id] = applicant
        return applicant

    def update_applicant(self, applicant):
        if applicant.applicant_id not in self._applicants:
            raise KeyError(applicant.applicant_id)
        if self._repo is not None:
            self._repo.update_applicant(applicant)

    def delete_applicant(self, applicant_id):
        if applicant_id not in self._applicants:
            raise KeyError(applicant_id)
        if self.permits_of(applicant_id):
            raise ValueError("This applicant still has permits. "
                             "Delete those permits first.")
        if self._repo is not None:
            self._repo.delete_applicant(applicant_id)
        del self._applicants[applicant_id]

    def get_applicant(self, applicant_id):
        return self._applicants.get(applicant_id)

    def applicants(self):
        return list(self._applicants.values())

    # ---- permits (CRUD) -------------------------------------------------------
    def add_permit(self, permit):
        if permit.applicant_id not in self._applicants:
            Permit.release_id(permit.permit_id)
            raise ValueError("Unknown applicant. Register the applicant first.")
        if self._repo is not None:
            try:
                self._repo.insert_permit(permit)
            except Exception:
                Permit.release_id(permit.permit_id)
                raise
        self._permits[permit.permit_id] = permit
        return permit

    def update_permit(self, permit):
        if permit.permit_id not in self._permits:
            raise KeyError(permit.permit_id)
        if self._repo is not None:
            self._repo.update_permit(permit)

    def delete_permit(self, permit_id):
        if permit_id not in self._permits:
            raise KeyError(permit_id)
        if self._repo is not None:
            self._repo.delete_permit(permit_id)
        del self._permits[permit_id]

    def get_permit(self, permit_id):
        return self._permits.get(permit_id)

    def history_of(self, permit_id):
        """List of (time, text). From the database audit trail when connected,
        otherwise from the in-memory log of the object."""
        if self._repo is not None:
            return self._repo.fetch_history(permit_id)
        return list(self._permits[permit_id].history)

    def permits(self):
        return list(self._permits.values())

    # ---- queries --------------------------------------------------------------
    def permits_of(self, applicant_id):
        return [p for p in self._permits.values()
                if p.applicant_id == applicant_id]

    def filter_permits(self, status=None, kind=None):
        return [p for p in self._permits.values()
                if (status in (None, "All") or p.status == status)
                and (kind in (None, "All") or p.kind == kind)]

    def counts_by_status(self):
        counts = {s: 0 for s in STATUSES}
        for permit in self._permits.values():
            counts[permit.status] += 1
        return counts

    def expiring_soon(self, days=30):
        """Approved permits that expire within `days` days."""
        return [p for p in self._permits.values()
                if p.status == "Approved" and p.days_left() is not None
                and 0 <= p.days_left() <= days]

    def total_fees_approved(self):
        return sum(p.fee() for p in self._permits.values()
                   if p.status == "Approved")

    def display_all(self):
        """Polymorphism: each object prints itself through its own describe()."""
        if not self._permits:
            print("No permits recorded.")
        for permit in self._permits.values():
            print(permit.describe())

    def __len__(self):
        return len(self._permits)
