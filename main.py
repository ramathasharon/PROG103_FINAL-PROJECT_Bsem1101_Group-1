"""
main.py
-------
Entry point:  python main.py

Connects to PostgreSQL. If the database is not reachable, the user may
continue in OFFLINE mode (records live in memory only) so the program can
still be demonstrated.
"""

import sys

from PyQt6.QtWidgets import QApplication, QMessageBox

from database import Database, config_from_env
from gui import MainWindow
from models import LicensingOffice, PermitRegistry

OFFLINE_OFFICES = (
    LicensingOffice("Business Licensing Unit", ("business",)),
    LicensingOffice("Building Control Unit", ("building",)),
    LicensingOffice("General Permits Desk", ("general",)),
)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")   # same look on every operating system
    try:
        db = Database(**config_from_env())
        db.create_tables()
        registry = PermitRegistry(db)
        registry.load()
        offices = db.fetch_offices()
        mode = "Connected to PostgreSQL"
    except Exception as error:
        answer = QMessageBox.question(
            None, "Database unavailable",
            f"Could not connect to PostgreSQL:\n{error}\n\n"
            "Continue in offline mode? (nothing will be saved)")
        if answer != QMessageBox.StandardButton.Yes:
            return 1
        registry = PermitRegistry()
        offices = OFFLINE_OFFICES
        mode = "OFFLINE mode - data is not saved"

    window = MainWindow(registry, offices, mode)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
