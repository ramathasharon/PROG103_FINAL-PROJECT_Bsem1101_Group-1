"""
tests.py
--------
Unit tests for the domain classes (no GUI, no database needed).
Run:  python -m unittest tests -v

If PostgreSQL is reachable (PG* environment variables set), the last test
class also runs the CRUD cycle against a throw-away copy of the tables.
"""

import os
import unittest
from datetime import date, timedelta

from models import (STATUSES, Applicant, BuildingPermit, BusinessPermit,
                    GeneralPermit, LicensingOffice, Permit, PermitRegistry,
                    Record)


def make_registry():
    registry = PermitRegistry()
    applicant = Applicant.create("Aminata Kamara", "+232 76 123456", "Bo")
    registry.add_applicant(applicant)
    return registry, applicant


class RecordAndApplicantTests(unittest.TestCase):
    def test_record_is_abstract(self):
        with self.assertRaises(TypeError):
            Record("x")

    def test_permit_is_abstract(self):
        with self.assertRaises(TypeError):
            Permit("P", "A", "details")

    def test_valid_applicant(self):
        a = Applicant.create("Mohamed Sesay", "076123456", "Kono")
        self.assertTrue(a.applicant_id.startswith("APP-"))
        self.assertEqual(a.describe(), f"[{a.applicant_id}] Mohamed Sesay | Kono")

    def test_invalid_applicant_values_rejected(self):
        for name, phone, district in (("A", "076123456", "Bo"),
                                      ("Mohamed 123", "076123456", "Bo"),
                                      ("Mohamed Sesay", "12345", "Bo"),
                                      ("Mohamed Sesay", "abcdefghij", "Bo"),
                                      ("Mohamed Sesay", "076123456", "Mars")):
            with self.assertRaises(ValueError):
                Applicant.create(name, phone, district)

    def test_failed_validation_does_not_burn_an_id(self):
        first = Applicant.create("Fatmata Bangura", "076123456", "Bo")
        with self.assertRaises(ValueError):
            Applicant.create("X", "076123456", "Bo")
        second = Applicant.create("Ibrahim Conteh", "076123456", "Bo")
        n1 = int(first.applicant_id.split("-")[1])
        n2 = int(second.applicant_id.split("-")[1])
        self.assertEqual(n2, n1 + 1)

    def test_sync_counter_continues_after_highest(self):
        Applicant.sync_counter(["APP-050", "APP-007"])
        self.assertEqual(Applicant.next_id(), "APP-051")

    def test_release_id_reuses_the_number_after_a_refused_save(self):
        a = Applicant.create("Fatmata Bangura", "076123456", "Bo")
        number = a.applicant_id
        Applicant.release_id(number)
        self.assertEqual(Applicant.next_id(), number)

    def test_id_is_read_only(self):
        a = Applicant.create("Mohamed Sesay", "076123456", "Kono")
        with self.assertRaises(AttributeError):
            a.record_id = "HACK"


class PermitTests(unittest.TestCase):
    def setUp(self):
        self.registry, self.applicant = make_registry()
        self.aid = self.applicant.applicant_id

    def test_polymorphism_fee_docs_and_describe(self):
        permits = [GeneralPermit.create(self.aid, "Market stall"),
                   BusinessPermit.create(self.aid, "Kamara Stores"),
                   BuildingPermit.create(self.aid, "Plot 12 Hill Station")]
        self.assertEqual([p.fee() for p in permits], [100, 500, 1500])
        self.assertEqual([len(p.required_documents()) for p in permits], [1, 3, 4])
        self.assertTrue(permits[1].describe().startswith("BUSINESS "))
        self.assertTrue(permits[2].describe().startswith("BUILDING "))
        self.assertFalse(permits[0].describe().startswith(("BUSINESS", "BUILDING")))

    def test_inheritance_chain(self):
        self.assertTrue(issubclass(BusinessPermit, Permit))
        self.assertTrue(issubclass(Permit, Record))
        self.assertTrue(hasattr(BusinessPermit, "log"))       # Auditable mixin

    def test_factory_builds_the_right_subclass(self):
        self.assertIsInstance(BuildingPermit.create(self.aid, "Plot 1 Bo"),
                              BuildingPermit)

    def test_workflow_happy_path(self):
        p = BusinessPermit.create(self.aid, "Kamara Stores")
        p.change_status("Under Review")
        p.approve()
        self.assertEqual(p.status, "Approved")
        self.assertEqual(p.issue_date, date.today())
        self.assertEqual(p.expiry_date, date.today() + timedelta(days=365))

    def test_invalid_transition_rejected(self):
        p = BusinessPermit.create(self.aid, "Kamara Stores")
        with self.assertRaises(ValueError):
            p.approve()                      # Submitted -> Approved not allowed
        p.change_status("Rejected")
        with self.assertRaises(ValueError):
            p.change_status("Under Review")  # Rejected is final

    def test_expiry_and_renewal(self):
        p = GeneralPermit.create(self.aid, "Market stall")
        p.change_status("Under Review")
        p.approve()
        p._expiry_date = date.today() - timedelta(days=1)   # simulate old permit
        self.assertTrue(p.refresh_expiry())
        self.assertEqual(p.status, "Expired")
        p.renew()
        self.assertEqual(p.status, "Approved")
        self.assertGreater(p.expiry_date, date.today())

    def test_cannot_renew_submitted_permit(self):
        p = GeneralPermit.create(self.aid, "Market stall")
        with self.assertRaises(ValueError):
            p.renew()

    def test_audit_history_is_a_tuple_copy(self):
        p = GeneralPermit.create(self.aid, "Market stall")
        p.change_status("Under Review")
        self.assertIsInstance(p.history, tuple)
        self.assertEqual(len(p.history), 2)

    def test_details_validation(self):
        with self.assertRaises(ValueError):
            GeneralPermit.create(self.aid, "ab")
        with self.assertRaises(ValueError):
            GeneralPermit.create(self.aid, "x" * 121)


class OfficeAndRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry, self.applicant = make_registry()
        self.aid = self.applicant.applicant_id
        self.business = LicensingOffice("Business Licensing Unit", ("business",))
        self.building = LicensingOffice("Building Control Unit", ("building",))

    def test_office_only_handles_its_own_permits(self):
        p = BusinessPermit.create(self.aid, "Kamara Stores")
        ok, message = self.building.start_review(p)
        self.assertFalse(ok)
        self.assertIn("does not handle", message)
        self.assertEqual(p.status, "Submitted")
        ok, _ = self.business.start_review(p)
        self.assertTrue(ok)
        self.assertEqual(p.office, "Business Licensing Unit")

    def test_office_reports_invalid_transition(self):
        p = BusinessPermit.create(self.aid, "Kamara Stores")
        ok, message = self.business.approve(p)
        self.assertFalse(ok)
        self.assertIn("cannot become", message)

    def test_registry_add_filter_count_delete(self):
        p1 = self.registry.add_permit(BusinessPermit.create(self.aid, "Shop A"))
        p2 = self.registry.add_permit(GeneralPermit.create(self.aid, "Stall B"))
        self.business.start_review(p1)
        self.assertEqual(len(self.registry), 2)
        self.assertEqual(self.registry.filter_permits(status="Under Review"), [p1])
        self.assertEqual(self.registry.filter_permits(kind="general"), [p2])
        counts = self.registry.counts_by_status()
        self.assertEqual(counts["Under Review"], 1)
        self.assertEqual(sum(counts.values()), 2)
        self.assertEqual(set(counts), set(STATUSES))
        self.registry.delete_permit(p2.permit_id)
        self.assertEqual(len(self.registry), 1)

    def test_permit_needs_a_known_applicant(self):
        with self.assertRaises(ValueError):
            self.registry.add_permit(GeneralPermit.create("APP-999", "Stall B"))

    def test_cannot_delete_applicant_with_permits(self):
        self.registry.add_permit(GeneralPermit.create(self.aid, "Stall B"))
        with self.assertRaises(ValueError):
            self.registry.delete_applicant(self.aid)

    def test_expiring_soon_and_fee_total(self):
        p = self.registry.add_permit(BusinessPermit.create(self.aid, "Shop A"))
        self.business.start_review(p)
        self.business.approve(p)
        p._expiry_date = date.today() + timedelta(days=10)
        self.assertEqual(self.registry.expiring_soon(30), [p])
        self.assertEqual(self.registry.total_fees_approved(), 500)


@unittest.skipUnless(os.environ.get("PGPASSWORD") is not None
                     or os.environ.get("PGHOST"),
                     "PostgreSQL environment variables not set")
class DatabaseTests(unittest.TestCase):
    """Full CRUD cycle against PostgreSQL (uses the configured database)."""

    def test_crud_cycle(self):
        from database import Database, DatabaseError, config_from_env
        db = Database(**config_from_env())
        db.create_tables()
        registry = PermitRegistry(db)
        registry.load()
        applicant = permit = None
        try:
            applicant = registry.add_applicant(
                Applicant.create("Test Person", "+232 76 000111", "Bo"))
            permit = registry.add_permit(
                BusinessPermit.create(applicant.applicant_id, "Test Shop"))
            office = LicensingOffice("Business Licensing Unit", ("business",))
            office.start_review(permit)
            registry.update_permit(permit)                 # the GUI saves after each step
            office.approve(permit)
            registry.update_permit(permit)

            fresh = PermitRegistry(db)
            fresh.load()                                   # reload from PostgreSQL
            saved = fresh.get_permit(permit.permit_id)
            self.assertIsInstance(saved, BusinessPermit)   # right subclass rebuilt
            self.assertEqual(saved.status, "Approved")
            self.assertEqual(saved.office, "Business Licensing Unit")
            # the database trigger wrote the audit trail
            notes = [text for _, text in fresh.history_of(permit.permit_id)]
            self.assertTrue(any("Approved" in n for n in notes))

            # the database refuses an illegal jump even if Python is bypassed
            skipped = BusinessPermit.create(applicant.applicant_id, "Another Shop")
            registry.add_permit(skipped)
            skipped._status = "Approved"
            skipped._issue_date = skipped._expiry_date = date.today()
            with self.assertRaises(DatabaseError):
                registry.update_permit(skipped)
            registry.delete_permit(skipped.permit_id)
        finally:                                           # always clean up
            if permit:
                registry.delete_permit(permit.permit_id)
            if applicant:
                registry.delete_applicant(applicant.applicant_id)
            db.close()


if __name__ == "__main__":
    unittest.main()
