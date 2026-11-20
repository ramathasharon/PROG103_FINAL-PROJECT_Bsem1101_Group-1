"""
gui.py
------
PyQt6 interface for the Digital Permit & License Management System.

Only PyQt6 is used (the charts are drawn with QPainter), as the brief requires.

Layout
  MainWindow
    |-- sidebar (navigation + connection status)
    |-- header (page title)
    |-- QStackedWidget
          |-- DashboardPage : KPI cards, status donut chart, bar chart,
          |                   "needs attention" list
          |-- PermitsPage   : search + filters, table with status pills,
          |                   detail panel with the office workflow buttons
          |-- ApplicantsPage: search, table, add / edit / delete

OOP in the GUI
  * every page inherits from BasePage (which inherits from QWidget)
  * custom widgets inherit from Qt classes: Card, KpiCard, DonutChart,
    BarChart (QWidget), PillDelegate (QStyledItemDelegate),
    NewApplicationDialog, ApplicantDialog (QDialog)
  * polymorphism: each permit class supplies its own label, fee and
    document list, which the dialogs display without any if-statements
"""

from datetime import date

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QComboBox, QDialog, QFormLayout,
    QFrame, QGraphicsDropShadowEffect, QGridLayout, QHBoxLayout, QHeaderView,
    QInputDialog, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QScrollArea, QSizePolicy, QStackedWidget, QStyle, QStyledItemDelegate,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from models import DISTRICTS, PERMIT_CLASSES, STATUSES, Applicant

# =============================================================================
# Look and feel
# =============================================================================
# status -> (text colour, background colour)
STATUS_STYLE = {
    "Submitted": ("#475569", "#e2e8f0"),
    "Under Review": ("#b45309", "#fef3c7"),
    "Approved": ("#15803d", "#dcfce7"),
    "Rejected": ("#b91c1c", "#fee2e2"),
    "Expired": ("#6b7280", "#e5e7eb"),
}
TYPE_COLOURS = {"general": "#8b5cf6", "business": "#2563eb", "building": "#f59e0b"}

STYLESHEET = """
* { font-family: "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px; color: #1f2937; }
QMainWindow, QWidget#page, QDialog { background: #f4f6fa; }
QStatusBar { background: #f4f6fa; color: #6b7280; }

QFrame#sidebar { background: #0f2747; }
QLabel#brand { color: white; font-size: 19px; font-weight: 700; }
QLabel#brandSub { color: #9db4d8; font-size: 11px; }
QLabel#navCaption { color: #6f8bb8; font-size: 11px; font-weight: 600; letter-spacing: 1px; }
QPushButton#nav { background: transparent; color: #c9d6ee; text-align: left;
    padding: 13px 20px; border: none; border-left: 4px solid transparent;
    border-radius: 0; font-size: 14px; font-weight: 500; }
QPushButton#nav:hover { background: #17345f; color: white; }
QPushButton#nav:checked { background: #1d4079; color: white;
    border-left: 4px solid #60a5fa; font-weight: 700; }
QLabel#chipOnline { background: #14532d; color: #bbf7d0; border-radius: 10px;
    padding: 6px 12px; font-weight: 600; }
QLabel#chipOffline { background: #78350f; color: #fde68a; border-radius: 10px;
    padding: 6px 12px; font-weight: 600; }

QLabel#pageTitle { font-size: 26px; font-weight: 700; color: #0f172a; }
QLabel#pageSub { color: #6b7280; font-size: 13px; }
QLabel#cardTitle { font-size: 15px; font-weight: 700; color: #0f172a; }
QLabel#muted { color: #6b7280; }
QLabel#fieldName { color: #6b7280; font-size: 12px; }
QLabel#fieldValue { color: #0f172a; font-weight: 600; }
QLabel#error { color: #b91c1c; background: #fee2e2; border-radius: 8px; padding: 8px 10px; }
QLabel#info { color: #1e3a8a; background: #eff6ff; border-radius: 8px; padding: 10px 12px; }

QFrame#card { background: white; border-radius: 14px; }
QFrame#divider { background: #e5e7eb; max-height: 1px; min-height: 1px; }

QLineEdit, QComboBox { background: white; border: 1px solid #d1d9e6;
    border-radius: 9px; padding: 9px 12px; min-height: 18px; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #2563eb; }
QComboBox::drop-down { border: none; width: 26px; }
QComboBox QAbstractItemView { background: white; border: 1px solid #d1d9e6;
    selection-background-color: #dbeafe; selection-color: #0f172a; outline: 0; }

QPushButton { background: white; border: 1px solid #d1d9e6; border-radius: 9px;
    padding: 9px 16px; font-weight: 600; }
QPushButton:hover { background: #f1f5f9; }
QPushButton:disabled { color: #a3aab8; background: #f3f4f6; border: 1px solid #e5e7eb; }
QPushButton#primary { background: #2563eb; color: white; border: none; }
QPushButton#primary:hover { background: #1d4ed8; }
QPushButton#success { background: #16a34a; color: white; border: none; }
QPushButton#success:hover { background: #15803d; }
QPushButton#danger { background: #dc2626; color: white; border: none; }
QPushButton#danger:hover { background: #b91c1c; }
QPushButton#warn { background: #f59e0b; color: white; border: none; }
QPushButton#warn:hover { background: #d97706; }
QPushButton#primary:disabled, QPushButton#success:disabled,
QPushButton#danger:disabled, QPushButton#warn:disabled {
    background: #e5e7eb; color: #9ca3af; }
QPushButton#ghostDanger { background: white; color: #b91c1c; border: 1px solid #fecaca; }
QPushButton#ghostDanger:hover { background: #fef2f2; }
QPushButton#ghostDanger:disabled { color: #a3aab8; border: 1px solid #e5e7eb; background: #f3f4f6; }

QTableWidget { background: white; border: none; border-radius: 12px;
    alternate-background-color: #f8fafc; gridline-color: transparent;
    selection-background-color: #dbeafe; selection-color: #0f172a; outline: 0; }
QTableWidget::item { padding: 4px 8px; border: none; }
QHeaderView::section { background: #f1f5f9; color: #475569; border: none;
    padding: 11px 8px; font-weight: 700; font-size: 12px; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #cbd5e1; border-radius: 4px; min-height: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollArea { border: none; background: transparent; }
QToolTip { background: #0f172a; color: white; border: none; padding: 6px; }
"""


def shadow(widget, blur=24, alpha=40):
    """Soft drop shadow that makes cards look lifted off the page."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, 3)
    effect.setColor(QColor(15, 39, 71, alpha))
    widget.setGraphicsEffect(effect)


def pill_style(status):
    fg, bg = STATUS_STYLE[status]
    return (f"background: {bg}; color: {fg}; border-radius: 11px; "
            f"padding: 4px 12px; font-weight: 700; font-size: 12px;")


def button(text, kind=None, handler=None):
    b = QPushButton(text)
    if kind:
        b.setObjectName(kind)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setMinimumHeight(38)
    if handler:
        b.clicked.connect(handler)
    return b


# =============================================================================
# Reusable widgets
# =============================================================================
class Card(QFrame):
    """A white rounded panel with a soft shadow."""

    def __init__(self):
        super().__init__()
        self.setObjectName("card")
        shadow(self)


class KpiCard(Card):
    """A big number with a title, used on the dashboard."""

    def __init__(self, title, colour):
        super().__init__()
        self.setStyleSheet(f"QFrame#card {{ border-left: 6px solid {colour}; }}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 16, 16)
        layout.setSpacing(2)
        self.title = QLabel(title)
        self.title.setObjectName("muted")
        self.value = QLabel("0")
        self.value.setStyleSheet(
            f"font-size: 30px; font-weight: 800; color: {colour};")
        self.note = QLabel("")
        self.note.setObjectName("muted")
        layout.addWidget(self.title)
        layout.addWidget(self.value)
        layout.addWidget(self.note)

    def set_value(self, value, note=""):
        self.value.setText(str(value))
        self.note.setText(note)


class DonutChart(QWidget):
    """Donut chart of permits per status, drawn with QPainter."""

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(210)
        self._data = {}

    def set_data(self, data):
        self._data = dict(data)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        total = sum(self._data.values())
        side = min(self.height() - 20, 190)
        ring = 26
        box = QRectF(14, (self.height() - side) / 2, side, side)
        arc = box.adjusted(ring / 2, ring / 2, -ring / 2, -ring / 2)

        p.setPen(QPen(QColor("#eef1f6"), ring))          # empty track
        p.drawEllipse(arc)
        start = 90 * 16
        if total:
            for status in STATUSES:
                count = self._data.get(status, 0)
                if not count:
                    continue
                span = -round(count / total * 360 * 16)
                p.setPen(QPen(QColor(STATUS_STYLE[status][0]), ring,
                              Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
                p.drawArc(arc, start, span)
                start += span

        p.setPen(QColor("#0f172a"))
        big = QFont(self.font()); big.setPointSize(24); big.setBold(True)
        p.setFont(big)
        p.drawText(box, Qt.AlignmentFlag.AlignCenter, str(total))
        small = QFont(self.font()); small.setPointSize(9)
        p.setFont(small)
        p.setPen(QColor("#6b7280"))
        p.drawText(box.adjusted(0, 46, 0, 0), Qt.AlignmentFlag.AlignHCenter
                   | Qt.AlignmentFlag.AlignTop, "permits")

        # legend
        x = box.right() + 34
        y = (self.height() - len(STATUSES) * 30) / 2
        for status in STATUSES:
            count = self._data.get(status, 0)
            colour = QColor(STATUS_STYLE[status][0])
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(colour)
            p.drawRoundedRect(QRectF(x, y + 6, 14, 14), 4, 4)
            p.setPen(QColor("#1f2937"))
            p.setFont(self.font())
            p.drawText(QPointF(x + 24, y + 18), status)
            p.setPen(QColor("#0f172a"))
            bold = QFont(self.font()); bold.setBold(True)
            p.setFont(bold)
            share = f"{count}  ({count / total:.0%})" if total else "0"
            p.drawText(QPointF(x + 130, y + 18), share)
            y += 30


class BarChart(QWidget):
    """Horizontal bar chart: [(label, value, colour), ...]."""

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(210)
        self._rows = []

    def set_rows(self, rows):
        self._rows = list(rows)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self._rows:
            return
        top = max(v for _, v, _ in self._rows) or 1
        row_h = min(56, (self.height() - 10) / len(self._rows))
        label_w, value_w = 120, 70
        bar_x = label_w + 10
        bar_w = max(40, self.width() - bar_x - value_w - 10)
        y = 6
        for label, value, colour in self._rows:
            p.setPen(QColor("#1f2937"))
            p.setFont(self.font())
            p.drawText(QRectF(0, y, label_w, row_h),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                       label)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#eef1f6"))
            track = QRectF(bar_x, y + row_h / 2 - 10, bar_w, 20)
            p.drawRoundedRect(track, 10, 10)
            p.setBrush(QColor(colour))
            p.drawRoundedRect(QRectF(bar_x, track.y(),
                                     max(20, bar_w * value / top), 20), 10, 10)
            bold = QFont(self.font()); bold.setBold(True)
            p.setFont(bold)
            p.setPen(QColor("#0f172a"))
            p.drawText(QRectF(bar_x + bar_w + 8, y, value_w, row_h),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                       str(value))
            y += row_h


class PillDelegate(QStyledItemDelegate):
    """Paints the status text of a table cell as a coloured pill."""

    def paint(self, painter, option, index):
        status = index.data(Qt.ItemDataRole.DisplayRole)
        if status not in STATUS_STYLE:
            return super().paint(painter, option, index)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor("#dbeafe"))
        elif index.row() % 2:
            painter.fillRect(option.rect, QColor("#f8fafc"))
        else:
            painter.fillRect(option.rect, QColor("white"))
        fg, bg = STATUS_STYLE[status]
        font = QFont(option.font); font.setBold(True); font.setPointSize(9)
        painter.setFont(font)
        width = painter.fontMetrics().horizontalAdvance(status) + 26
        rect = QRectF(option.rect.x() + 8,
                      option.rect.center().y() - 11, width, 22)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(bg))
        painter.drawRoundedRect(rect, 11, 11)
        painter.setPen(QColor(fg))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, status)
        painter.restore()

    def sizeHint(self, option, index):
        return QSize(130, 42)


def make_table(columns, stretch_column):
    table = QTableWidget(0, len(columns))
    table.setHorizontalHeaderLabels(columns)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.setWordWrap(False)
    table.setTextElideMode(Qt.TextElideMode.ElideRight)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(42)
    header = table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(stretch_column, QHeaderView.ResizeMode.Stretch)
    header.setHighlightSections(False)
    header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    header.setStretchLastSection(False)
    shadow(table, blur=20, alpha=30)
    return table


def divider():
    line = QFrame()
    line.setObjectName("divider")
    return line


# =============================================================================
# Pages
# =============================================================================
class BasePage(QWidget):
    """Behaviour shared by all pages (inheritance)."""

    data_changed = pyqtSignal()          # a page tells the window to refresh
    TITLE = ""
    SUBTITLE = ""

    def __init__(self, registry, notify):
        super().__init__()
        self.setObjectName("page")
        self.registry = registry
        self.notify = notify             # notify(text, ok=True) -> toast

    def error(self, message):
        QMessageBox.warning(self, "Cannot complete action", message)

    def refresh(self):                   # overridden by each page
        pass

    @staticmethod
    def fill_row(table, row, values):
        for col, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            table.setItem(row, col, item)


# ------------------------------------------------------------------ Dashboard
class DashboardPage(BasePage):
    TITLE = "Dashboard"
    SUBTITLE = "A live overview of applicants, permits and expiry dates"

    def __init__(self, registry, notify):
        super().__init__(registry, notify)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(18)

        kpis = QHBoxLayout()
        kpis.setSpacing(16)
        self.k_applicants = KpiCard("Registered applicants", "#2563eb")
        self.k_permits = KpiCard("Total permits", "#8b5cf6")
        self.k_pending = KpiCard("Awaiting a decision", "#f59e0b")
        self.k_expiring = KpiCard("Expiring within 30 days", "#dc2626")
        self.k_fees = KpiCard("Fees from approved permits", "#16a34a")
        for card in (self.k_applicants, self.k_permits, self.k_pending,
                     self.k_expiring, self.k_fees):
            kpis.addWidget(card)
        root.addLayout(kpis)

        charts = QHBoxLayout()
        charts.setSpacing(16)
        status_card = Card()
        sl = QVBoxLayout(status_card)
        sl.setContentsMargins(20, 16, 20, 12)
        sl.addWidget(self._title("Permits by status"))
        self.donut = DonutChart()
        sl.addWidget(self.donut)
        type_card = Card()
        tl = QVBoxLayout(type_card)
        tl.setContentsMargins(20, 16, 20, 12)
        tl.addWidget(self._title("Permits by type"))
        self.bars = BarChart()
        tl.addWidget(self.bars)
        charts.addWidget(status_card, 5)
        charts.addWidget(type_card, 4)
        root.addLayout(charts)

        attention = Card()
        al = QVBoxLayout(attention)
        al.setContentsMargins(20, 16, 20, 16)
        al.addWidget(self._title("Needs attention: expiring within 30 days or already expired"))
        self.attention_table = QTableWidget(0, 5)
        self.attention_table.setHorizontalHeaderLabels(
            ("Reference", "Applicant", "Details", "Expires", "Days left"))
        t = self.attention_table
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        t.setShowGrid(False)
        t.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        t.verticalHeader().setVisible(False)
        t.verticalHeader().setDefaultSectionSize(36)
        t.setAlternatingRowColors(True)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        t.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        al.addWidget(t)
        root.addWidget(attention, 1)

    @staticmethod
    def _title(text):
        label = QLabel(text)
        label.setObjectName("cardTitle")
        return label

    def refresh(self):
        counts = self.registry.counts_by_status()
        total = sum(counts.values())
        pending = counts["Submitted"] + counts["Under Review"]
        soon = self.registry.expiring_soon(30)
        self.k_applicants.set_value(len(self.registry.applicants()),
                                    "in the registry")
        self.k_permits.set_value(total, f"{counts['Approved']} approved")
        self.k_pending.set_value(pending,
                                 f"{counts['Submitted']} new, {counts['Under Review']} in review")
        self.k_expiring.set_value(len(soon), "renewals due soon")
        self.k_fees.set_value(f"Le {self.registry.total_fees_approved():,}",
                              "base fees")
        self.donut.set_data(counts)

        by_type = []
        for kind, klass in PERMIT_CLASSES.items():
            n = len(self.registry.filter_permits(kind=kind))
            by_type.append((klass.TYPE_NAME, n, TYPE_COLOURS[kind]))
        self.bars.set_rows(by_type)

        rows = [p for p in self.registry.permits()
                if p.days_left() is not None
                and p.status in ("Approved", "Expired") and p.days_left() <= 30]
        rows.sort(key=lambda p: p.days_left())
        rows = rows[:6]
        t = self.attention_table
        t.setRowCount(len(rows))
        for r, p in enumerate(rows):
            left = p.days_left()
            applicant = self.registry.get_applicant(p.applicant_id)
            text = f"{left} days" if left >= 0 else f"overdue by {-left} days"
            self.fill_row(t, r, (p.permit_id,
                                 applicant.full_name if applicant else p.applicant_id,
                                 f"{p.type_name}: {p.details}",
                                 p.expiry_date.isoformat(), text))
            colour = "#b91c1c" if left < 0 else "#b45309"
            t.item(r, 4).setForeground(QColor(colour))
            font = t.item(r, 4).font(); font.setBold(True)
            t.item(r, 4).setFont(font)
        t.setMaximumHeight(36 * 7 + 40)


# ------------------------------------------------------------ New permit dialog
class NewApplicationDialog(QDialog):
    """Form for a new permit application. Validation errors are shown inside
    the dialog, so the user can correct them without losing what was typed."""

    def __init__(self, registry, parent=None, applicant_id=None):
        super().__init__(parent)
        self.registry = registry
        self.created = None
        self.setWindowTitle("New permit application")
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(14)
        title = QLabel("New permit application")
        title.setObjectName("pageTitle")
        title.setStyleSheet("font-size: 21px; font-weight: 700;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.applicant_box = QComboBox()
        for a in registry.applicants():
            self.applicant_box.addItem(f"{a.applicant_id}  -  {a.full_name}",
                                       a.applicant_id)
        if applicant_id:
            self.applicant_box.setCurrentIndex(self.applicant_box.findData(applicant_id))
        self.type_box = QComboBox()
        for kind, klass in PERMIT_CLASSES.items():
            self.type_box.addItem(klass.TYPE_NAME, kind)
        self.type_box.currentIndexChanged.connect(self.update_info)
        self.details_label = QLabel()
        self.details_edit = QLineEdit()
        form.addRow("Applicant", self.applicant_box)
        form.addRow("Permit type", self.type_box)
        form.addRow(self.details_label, self.details_edit)
        layout.addLayout(form)

        self.info = QLabel()
        self.info.setObjectName("info")
        self.info.setWordWrap(True)
        self.info.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self.info)
        self.error_label = QLabel()
        self.error_label.setObjectName("error")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(button("Cancel", handler=self.reject))
        row.addWidget(button("Submit application", "primary", self.submit))
        layout.addLayout(row)
        self.update_info()

    def update_info(self):
        """Polymorphism: the chosen class supplies its own label, fee and
        documents. There is no if-statement per permit type."""
        klass = PERMIT_CLASSES[self.type_box.currentData()]
        sample = klass("SAMPLE", "-", "sample")
        self.details_label.setText(klass.DETAILS_LABEL)
        docs = "".join(f"<li>{d}</li>" for d in sample.required_documents())
        self.info.setText(
            f"<b>Fee:</b> Le {sample.fee():,} &nbsp;&nbsp; "
            f"<b>Valid for:</b> {klass.VALIDITY_YEARS} year(s)"
            f"<br><b>Documents to bring:</b><ul style='margin:4px 0 0 0'>{docs}</ul>")

    def submit(self):
        applicant_id = self.applicant_box.currentData()
        if applicant_id is None:
            self.show_error("Register an applicant first (Applicants page).")
            return
        klass = PERMIT_CLASSES[self.type_box.currentData()]
        try:
            permit = klass.create(applicant_id, self.details_edit.text())
            self.registry.add_permit(permit)
        except Exception as error:          # ValueError or database error
            self.show_error(str(error))
            return
        self.created = permit
        self.accept()

    def show_error(self, message):
        self.error_label.setText(message)
        self.error_label.show()


# ---------------------------------------------------------------- Permits page
class PermitsPage(BasePage):
    TITLE = "Permits"
    SUBTITLE = "Review, approve, reject and renew permit applications"
    COLUMNS = ("Reference", "Applicant", "Permit", "Status", "Expires")

    def __init__(self, registry, offices, notify):
        super().__init__(registry, notify)
        self.offices = {o.name: o for o in offices}
        self.current_id = None

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(18)
        left = QVBoxLayout()
        left.setSpacing(12)
        left.addLayout(self._build_toolbar())
        self.table = make_table(self.COLUMNS, 2)
        self.table.setItemDelegateForColumn(3, PillDelegate(self.table))
        self.table.itemSelectionChanged.connect(self.on_selection)
        left.addWidget(self.table, 1)
        self.summary = QLabel()
        self.summary.setObjectName("muted")
        left.addWidget(self.summary)
        root.addLayout(left, 1)
        root.addWidget(self._build_detail_panel())
        self.refresh()

    # ---- building the page ---------------------------------------------------
    def _build_toolbar(self):
        bar = QHBoxLayout()
        bar.setSpacing(10)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search permits...")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.refresh)
        self.status_filter = QComboBox()
        self.status_filter.addItems(("All statuses",) + STATUSES)
        self.status_filter.currentIndexChanged.connect(self.refresh)
        self.type_filter = QComboBox()
        self.type_filter.addItem("All types", None)
        for kind, klass in PERMIT_CLASSES.items():
            self.type_filter.addItem(klass.TYPE_NAME, kind)
        self.type_filter.currentIndexChanged.connect(self.refresh)
        bar.addWidget(self.search, 1)
        bar.addWidget(self.status_filter)
        bar.addWidget(self.type_filter)
        bar.addWidget(button("+  New application", "primary", self.new_application))
        return bar

    def _build_detail_panel(self):
        self.panel = Card()
        self.panel.setFixedWidth(310)
        outer = QVBoxLayout(self.panel)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(10)

        self.placeholder = QLabel("Select a permit in the table\nto see its details\nand take action.")
        self.placeholder.setObjectName("muted")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(self.placeholder, 1)

        self.body = QWidget()
        self.body.setObjectName("bodyHost")
        self.body.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.body.setStyleSheet("QWidget#bodyHost { background: white; }")
        body = QVBoxLayout(self.body)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(9)
        head = QHBoxLayout()
        self.d_id = QLabel()
        self.d_id.setStyleSheet("font-size: 20px; font-weight: 800; color: #0f172a;")
        self.d_pill = QLabel()
        head.addWidget(self.d_id)
        head.addStretch()
        head.addWidget(self.d_pill)
        body.addLayout(head)
        self.d_type = QLabel()
        self.d_type.setWordWrap(True)
        self.d_type.setObjectName("muted")
        body.addWidget(self.d_type)
        body.addWidget(divider())

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)
        self.d_fields = {}
        for r, name in enumerate(("Applicant", "Office", "Applied", "Issued",
                                  "Expires", "Fee")):
            label = QLabel(name); label.setObjectName("fieldName")
            value = QLabel("-"); value.setObjectName("fieldValue")
            value.setWordWrap(True)
            value.setMinimumHeight(20)
            label.setMinimumHeight(20)
            grid.addWidget(label, r, 0)
            grid.addWidget(value, r, 1)
            self.d_fields[name] = value
        grid.setColumnStretch(1, 1)
        body.addLayout(grid)
        body.addWidget(divider())

        cap = QLabel("Documents required"); cap.setObjectName("fieldName")
        body.addWidget(cap)
        self.d_docs = QLabel(); self.d_docs.setWordWrap(True)
        body.addWidget(self.d_docs)
        cap2 = QLabel("Recent history"); cap2.setObjectName("fieldName")
        body.addWidget(cap2)
        self.d_history = QLabel(); self.d_history.setWordWrap(True)
        self.d_history.setTextFormat(Qt.TextFormat.RichText)
        body.addWidget(self.d_history)
        body.addStretch(1)
        body.addWidget(divider())

        cap3 = QLabel("Acting office"); cap3.setObjectName("fieldName")
        body.addWidget(cap3)
        self.office_box = QComboBox()
        self.office_box.addItems(self.offices.keys())
        body.addWidget(self.office_box)

        actions = QGridLayout()
        actions.setSpacing(8)
        self.b_review = button("Start review", "warn", lambda: self.office_action("start_review"))
        self.b_approve = button("Approve", "success", lambda: self.office_action("approve"))
        self.b_reject = button("Reject", "danger", lambda: self.office_action("reject"))
        self.b_renew = button("Renew", "primary", lambda: self.office_action("renew"))
        self.b_edit = button("Edit details", None, self.edit_details)
        self.b_delete = button("Delete", "ghostDanger", self.delete_permit)
        actions.addWidget(self.b_review, 0, 0)
        actions.addWidget(self.b_approve, 0, 1)
        actions.addWidget(self.b_reject, 1, 0)
        actions.addWidget(self.b_renew, 1, 1)
        actions.addWidget(self.b_edit, 2, 0)
        actions.addWidget(self.b_delete, 2, 1)
        body.addLayout(actions)
        # scroll area: on small or high-DPI screens the panel scrolls
        # instead of squashing its labels and buttons
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setWidget(self.body)
        self.scroll.viewport().setAutoFillBackground(False)
        outer.addWidget(self.scroll, 100)
        self.scroll.hide()
        return self.panel

    # ---- table ----------------------------------------------------------------
    def refresh(self):
        status = self.status_filter.currentText()
        permits = self.registry.filter_permits(
            status=None if status == "All statuses" else status,
            kind=self.type_filter.currentData())
        needle = self.search.text().strip().lower()
        if needle:
            permits = [p for p in permits if needle in " ".join((
                p.permit_id, self._applicant_name(p.applicant_id), p.details,
                p.type_name, p.office)).lower()]
        permits.sort(key=lambda p: p.permit_id)
        keep = self.current_id
        self.table.blockSignals(True)
        self.table.setRowCount(len(permits))
        for row, p in enumerate(permits):
            d = p.to_dict()
            self.fill_row(self.table, row, (
                d["permit_id"], self._applicant_name(p.applicant_id),
                f"{d['type_name']}: {d['details']}", d["status"],
                d["expiry_date"] or "-"))
            self.table.item(row, 0).setFont(self._bold(self.table.item(row, 0)))
        self.table.blockSignals(False)
        self.summary.setText(f"Showing {len(permits)} of {len(self.registry)} permits")
        self._reselect(keep)

    @staticmethod
    def _bold(item):
        font = item.font(); font.setBold(True)
        return font

    def _reselect(self, permit_id):
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == permit_id:
                self.table.selectRow(row)
                self.show_detail(permit_id)
                return
        self.current_id = None
        self.show_detail(None)

    def _applicant_name(self, applicant_id):
        a = self.registry.get_applicant(applicant_id)
        return a.full_name if a else applicant_id

    def select_permit(self, permit_id):
        """Used by the New application flow (and by tests/demos)."""
        self.search.clear()
        self.status_filter.setCurrentIndex(0)
        self.type_filter.setCurrentIndex(0)
        self.current_id = permit_id
        self.refresh()

    # ---- detail panel -----------------------------------------------------------
    def on_selection(self):
        row = self.table.currentRow()
        self.current_id = self.table.item(row, 0).text() if row >= 0 else None
        self.show_detail(self.current_id)

    def show_detail(self, permit_id):
        permit = self.registry.get_permit(permit_id) if permit_id else None
        self.placeholder.setVisible(permit is None)
        self.scroll.setVisible(permit is not None)
        if permit is None:
            return
        self.d_id.setText(permit.permit_id)
        self.d_pill.setText(permit.status)
        self.d_pill.setStyleSheet(pill_style(permit.status))
        self.d_type.setText(f"{permit.type_name}: {permit.details}")
        left = permit.days_left()
        expiry = permit.expiry_date.isoformat() if permit.expiry_date else "-"
        if left is not None:
            expiry += f"  ({left} days left)" if left >= 0 else f"  (overdue {-left} d)"
        values = {"Applicant": self._applicant_name(permit.applicant_id),
                  "Office": permit.office if permit.office != "Unassigned" else "Not assigned yet",
                  "Applied": permit.date_applied.isoformat(),
                  "Issued": permit.issue_date.isoformat() if permit.issue_date else "-",
                  "Expires": expiry, "Fee": f"Le {permit.fee():,}"}
        for name, value in values.items():
            self.d_fields[name].setText(value)
        self.d_fields["Expires"].setStyleSheet(
            "font-weight: 600; color: #b91c1c;" if left is not None and left < 0
            else "font-weight: 600; color: #b45309;" if left is not None and left <= 30
            else "font-weight: 600; color: #0f172a;")
        self.d_docs.setText("\n".join("\u2022  " + d for d in permit.required_documents()))
        try:
            events = self.registry.history_of(permit.permit_id)[-4:]
        except Exception:
            events = []
        self.d_history.setText("<br>".join(
            f"<span style='color:#6b7280'>{stamp[5:16]}</span>&nbsp; {text}"
            for stamp, text in events) or "No history recorded.")

        # suggest the office that is responsible for this permit type
        for name, office in self.offices.items():
            if office.can_handle(permit):
                self.office_box.setCurrentText(name)
                break
        s = permit.status
        self.b_review.setEnabled(s == "Submitted")
        self.b_approve.setEnabled(s == "Under Review")
        self.b_reject.setEnabled(s in ("Submitted", "Under Review"))
        self.b_renew.setEnabled(s in ("Approved", "Expired"))
        self.b_edit.setEnabled(permit.can_edit)

    # ---- actions ------------------------------------------------------------------
    def new_application(self):
        if not self.registry.applicants():
            self.error("Register an applicant first (Applicants page).")
            return
        dialog = NewApplicationDialog(self.registry, self.window())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            permit = dialog.created
            self.select_permit(permit.permit_id)
            self.data_changed.emit()
            self.notify(f"Application submitted. Reference {permit.permit_id}, "
                        f"fee Le {permit.fee():,}.")

    def _save(self, permit):
        try:
            self.registry.update_permit(permit)
        except Exception as error:
            self.error(f"Database error: {error}")
            try:
                self.registry.load()         # the database refused: resync
            except Exception:
                pass
        self.refresh()
        self.data_changed.emit()

    def office_action(self, method_name):
        permit = self.registry.get_permit(self.current_id)
        if permit is None:
            return
        office = self.offices[self.office_box.currentText()]
        ok, message = getattr(office, method_name)(permit)
        if ok:
            self._save(permit)
            self.notify(message)
        else:
            self.notify(message, ok=False)
            self.error(message)

    def edit_details(self):
        permit = self.registry.get_permit(self.current_id)
        if permit is None:
            return
        text, accepted = QInputDialog.getText(
            self, "Edit details", f"{permit.DETAILS_LABEL}:", text=permit.details)
        if not accepted:
            return
        old = permit.details
        try:
            permit.details = text
            permit.log("Details updated")
            self.registry.update_permit(permit)
        except Exception as error:
            permit._details = old
            self.error(str(error))
            return
        self.refresh()
        self.data_changed.emit()
        self.notify(f"Updated details of {permit.permit_id}.")

    def delete_permit(self):
        pid = self.current_id
        if pid is None:
            return
        answer = QMessageBox.question(self, "Delete permit",
                                      f"Permanently delete {pid}?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.registry.delete_permit(pid)
        except Exception as error:
            self.error(f"Database error: {error}")
            return
        self.current_id = None
        self.refresh()
        self.data_changed.emit()
        self.notify(f"Deleted {pid}.")

    def reload_from_database(self):
        try:
            self.registry.load()
        except Exception as error:
            self.error(f"Database error: {error}")
        self.refresh()


# --------------------------------------------------------------- Applicant dialog
class ApplicantDialog(QDialog):
    """Add a new applicant, or edit an existing one."""

    def __init__(self, registry, parent=None, applicant=None):
        super().__init__(parent)
        self.registry = registry
        self.applicant = applicant
        self.saved = None
        editing = applicant is not None
        self.setWindowTitle("Edit applicant" if editing else "Register applicant")
        self.setMinimumWidth(480)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(14)
        title = QLabel("Edit applicant" if editing else "Register applicant")
        title.setStyleSheet("font-size: 21px; font-weight: 700; color: #0f172a;")
        layout.addWidget(title)
        note = QLabel("Privacy: we keep only a name, phone number and district. "
                      "Never enter ID numbers or home addresses.")
        note.setObjectName("info")
        note.setWordWrap(True)
        layout.addWidget(note)

        form = QFormLayout()
        form.setSpacing(12)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Aminata Kamara")
        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("e.g. +232 76 123456")
        self.district_box = QComboBox()
        self.district_box.addItems(DISTRICTS)
        form.addRow("Full name", self.name_edit)
        form.addRow("Phone", self.phone_edit)
        form.addRow("District", self.district_box)
        layout.addLayout(form)
        if editing:
            self.name_edit.setText(applicant.full_name)
            self.phone_edit.setText(applicant.phone)
            self.district_box.setCurrentText(applicant.district)

        self.error_label = QLabel()
        self.error_label.setObjectName("error")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(button("Cancel", handler=self.reject))
        row.addWidget(button("Save changes" if editing else "Register applicant",
                             "primary", self.save))
        layout.addLayout(row)

    def save(self):
        name = self.name_edit.text()
        phone = self.phone_edit.text()
        district = self.district_box.currentText()
        try:
            if self.applicant is None:
                applicant = Applicant.create(name, phone, district)
                self.registry.add_applicant(applicant)
            else:
                applicant = self.applicant
                backup = (applicant.full_name, applicant.phone, applicant.district)
                try:
                    applicant.full_name = name
                    applicant.phone = phone
                    applicant.district = district
                    self.registry.update_applicant(applicant)
                except Exception:
                    applicant.full_name, applicant.phone, applicant.district = backup
                    raise
        except Exception as error:
            self.error_label.setText(str(error))
            self.error_label.show()
            return
        self.saved = applicant
        self.accept()


# ------------------------------------------------------------- Applicants page
class ApplicantsPage(BasePage):
    TITLE = "Applicants"
    SUBTITLE = "People and business owners who apply for permits"
    COLUMNS = ("Reference", "Full name", "Phone", "District", "Registered", "Permits")

    def __init__(self, registry, notify):
        super().__init__(registry, notify)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        bar = QHBoxLayout()
        bar.setSpacing(10)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search applicants...")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.refresh)
        bar.addWidget(self.search, 1)
        self.b_edit = button("Edit", None, self.edit_applicant)
        self.b_delete = button("Delete", "ghostDanger", self.delete_applicant)
        bar.addWidget(self.b_edit)
        bar.addWidget(self.b_delete)
        bar.addWidget(button("+  Register applicant", "primary", self.add_applicant))
        root.addLayout(bar)
        self.table = make_table(self.COLUMNS, 1)
        self.table.itemSelectionChanged.connect(self.update_buttons)
        self.table.doubleClicked.connect(lambda _: self.edit_applicant())
        root.addWidget(self.table, 1)
        self.summary = QLabel()
        self.summary.setObjectName("muted")
        root.addWidget(self.summary)
        self.refresh()

    def selected_id(self):
        row = self.table.currentRow()
        return self.table.item(row, 0).text() if row >= 0 else None

    def update_buttons(self):
        has = self.selected_id() is not None
        self.b_edit.setEnabled(has)
        self.b_delete.setEnabled(has)

    def refresh(self):
        keep = self.selected_id()
        needle = self.search.text().strip().lower()
        people = [a for a in self.registry.applicants()
                  if not needle or needle in " ".join(
                      (a.applicant_id, a.full_name, a.phone, a.district)).lower()]
        self.table.blockSignals(True)
        self.table.setRowCount(len(people))
        for row, a in enumerate(people):
            d = a.to_dict()
            self.fill_row(self.table, row, (
                d["applicant_id"], d["full_name"], d["phone"], d["district"],
                d["date_registered"], len(self.registry.permits_of(a.applicant_id))))
            self.table.item(row, 0).setFont(PermitsPage._bold(self.table.item(row, 0)))
            self.table.item(row, 5).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.blockSignals(False)
        self.summary.setText(f"{len(people)} of {len(self.registry.applicants())} applicants")
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == keep:
                self.table.selectRow(row)
        self.update_buttons()

    def add_applicant(self):
        dialog = ApplicantDialog(self.registry, self.window())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            self.data_changed.emit()
            self.notify(f"Registered {dialog.saved.full_name} as "
                        f"{dialog.saved.applicant_id}.")

    def edit_applicant(self):
        aid = self.selected_id()
        if aid is None:
            return
        dialog = ApplicantDialog(self.registry, self.window(),
                                 self.registry.get_applicant(aid))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            self.data_changed.emit()
            self.notify(f"Updated {aid}.")

    def delete_applicant(self):
        aid = self.selected_id()
        if aid is None:
            return
        answer = QMessageBox.question(self, "Delete applicant",
                                      f"Permanently delete {aid}?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.registry.delete_applicant(aid)
        except Exception as error:
            self.error(str(error))
            return
        self.refresh()
        self.data_changed.emit()
        self.notify(f"Deleted {aid}.")


# =============================================================================
# Main window
# =============================================================================
class MainWindow(QMainWindow):
    def __init__(self, registry, offices, mode_text):
        super().__init__()
        self.setWindowTitle("Digital Permit & License Management System")
        self.resize(1400, 820)
        self.setMinimumSize(1200, 700)
        self.setStyleSheet(STYLESHEET)
        online = "PostgreSQL" in mode_text and "OFFLINE" not in mode_text

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar(mode_text, online))

        content = QWidget()
        content.setObjectName("page")
        col = QVBoxLayout(content)
        col.setContentsMargins(30, 24, 30, 18)
        col.setSpacing(14)
        self.title = QLabel()
        self.title.setObjectName("pageTitle")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("pageSub")
        col.addWidget(self.title)
        col.addWidget(self.subtitle)
        self.stack = QStackedWidget()
        col.addWidget(self.stack, 1)
        root.addWidget(content, 1)
        self.setCentralWidget(central)

        self.dashboard = DashboardPage(registry, self.show_message)
        self.permits_page = PermitsPage(registry, offices, self.show_message)
        self.applicants_page = ApplicantsPage(registry, self.show_message)
        self.pages = [self.dashboard, self.permits_page, self.applicants_page]
        for page in self.pages:
            self.stack.addWidget(page)
            page.data_changed.connect(self.refresh_all)
        self.nav_group.idClicked.connect(self.go_to)
        self.go_to(0)
        self.dashboard.refresh()

        self.toast = QLabel(self)
        self.toast.hide()
        self._toast_timer = QTimer(self)
        self._toast_timer.setSingleShot(True)
        self._toast_timer.timeout.connect(self.toast.hide)
        self.statusBar().showMessage(mode_text)

    # ---- sidebar -----------------------------------------------------------------
    def _build_sidebar(self, mode_text, online):
        bar = QFrame()
        bar.setObjectName("sidebar")
        bar.setFixedWidth(210)
        layout = QVBoxLayout(bar)
        layout.setContentsMargins(0, 26, 0, 22)
        layout.setSpacing(0)
        brand = QLabel("  Permit Hub")
        brand.setObjectName("brand")
        sub = QLabel("   Digital Permit & License\n   Management System")
        sub.setObjectName("brandSub")
        layout.addWidget(brand)
        layout.addWidget(sub)
        layout.addSpacing(28)
        caption = QLabel("   MENU")
        caption.setObjectName("navCaption")
        layout.addWidget(caption)
        layout.addSpacing(8)
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        for i, text in enumerate(("Dashboard", "Permits", "Applicants")):
            b = QPushButton(text)
            b.setObjectName("nav")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            self.nav_group.addButton(b, i)
            layout.addWidget(b)
        layout.addStretch(1)
        chip = QLabel(("  Connected to PostgreSQL" if online
                       else "  Offline: data is not saved"))
        chip.setObjectName("chipOnline" if online else "chipOffline")
        chip.setWordWrap(True)
        wrap = QHBoxLayout()
        wrap.setContentsMargins(16, 0, 16, 0)
        wrap.addWidget(chip)
        layout.addLayout(wrap)
        foot = QLabel("   PROG211 OOP 1 Group Project")
        foot.setObjectName("brandSub")
        layout.addSpacing(10)
        layout.addWidget(foot)
        return bar

    # ---- navigation and refresh --------------------------------------------------
    def go_to(self, index):
        self.nav_group.button(index).setChecked(True)
        page = self.pages[index]
        self.title.setText(page.TITLE)
        self.subtitle.setText(page.SUBTITLE)
        self.stack.setCurrentIndex(index)
        page.refresh()

    def refresh_all(self):
        self.dashboard.refresh()
        self.permits_page.refresh()
        self.applicants_page.refresh()

    # ---- toast messages ------------------------------------------------------------
    def show_message(self, text, ok=True):
        colour, bg = ("#14532d", "#dcfce7") if ok else ("#7f1d1d", "#fee2e2")
        self.toast.setStyleSheet(
            f"background: {bg}; color: {colour}; border-radius: 10px; "
            f"padding: 12px 18px; font-weight: 600; font-size: 13px;")
        self.toast.setText(text)
        self.toast.adjustSize()
        self.toast.move(self.width() - self.toast.width() - 30, 26)   # top right
        self.toast.raise_()
        self.toast.show()
        self._toast_timer.start(5000)
        self.statusBar().showMessage(text, 8000)
