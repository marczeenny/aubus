"""Driver schedule UI.

Allows drivers to add weekly availability entries used by ride matching.
"""

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QHBoxLayout,
    QComboBox,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
)  # type: ignore
from PyQt5.QtCore import Qt  # type: ignore

from ui_styles import set_title_label, style_button, style_input
from api_client import ApiClientError

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DIRECTIONS = ["To University", "From University"]


class ScheduleTab(QWidget):
    def __init__(self, app_state=None):
        super().__init__()
        self.app_state = app_state or {}
        self.entries = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        title = QLabel("Driver Schedule")
        set_title_label(title, size=14)
        layout.addWidget(title)

        self.info_label = QLabel("Add your availability for rides to help passengers find you.")
        layout.addWidget(self.info_label)

        form = QHBoxLayout()

        self.day_box = QComboBox()
        self.day_box.addItems(DAYS)
        form.addWidget(self.day_box)

        self.time_input = QLineEdit()
        self.time_input.setPlaceholderText("Time (e.g. 08:30)")
        style_input(self.time_input, width=120)
        form.addWidget(self.time_input)

        self.direction_box = QComboBox()
        self.direction_box.addItems(DIRECTIONS)
        form.addWidget(self.direction_box)

        self.area_input = QComboBox()
        areas = ["-- Select Area --", "Beirut", "Batroun", "Tripoli", "Saida", "Baalbek", "Zahle", "Nabatieh", "Metn"]
        self.area_input.addItems(areas)
        # preselect app_state area if available
        current_area = self.app_state.get('area', "-- Select Area --")
        idx = self.area_input.findText(current_area)
        if idx >= 0:
            self.area_input.setCurrentIndex(idx)
        style_input(self.area_input, width=160)
        form.addWidget(self.area_input)

        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self.add_entry)
        style_button(add_btn, min_height=28)
        form.addWidget(add_btn)

        layout.addLayout(form)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Day", "Time", "Direction", "Area"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table)

        actions = QHBoxLayout()
        delete_btn = QPushButton("Delete Selected")
        delete_btn.clicked.connect(self.delete_selected)
        style_button(delete_btn, min_height=28)
        actions.addWidget(delete_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_entries)
        style_button(refresh_btn, min_height=28)
        actions.addWidget(refresh_btn)

        layout.addLayout(actions)
        self.setLayout(layout)

    def current_user(self):
        return self.app_state.get("user_id")

    def api(self):
        return self.app_state.get("api")

    def add_entry(self):
        user_id = self.current_user()
        api = self.api()
        if not api or not user_id:
            QMessageBox.warning(self, "Not signed in", "Please log in as a driver to add a schedule.")
            return
        day = self.day_box.currentText()
        time_value = self.time_input.text().strip()
        direction = self.direction_box.currentText()
        area = self.area_input.currentText().strip()
        if not time_value or not area or area == "-- Select Area --":
            QMessageBox.warning(self, "Missing fields", "Please provide time and area.")
            return
        try:
            api.add_schedule(user_id, day, time_value, direction, area)
        except ApiClientError as exc:
            QMessageBox.critical(self, "Unable to add", str(exc))
            return
        self.time_input.clear()
        try:
            self.area_input.setCurrentIndex(0)
        except Exception:
            pass
        self.refresh_entries()

    def refresh_entries(self):
        api = self.api()
        user_id = self.current_user()
        if not api or not user_id:
            self.entries = []
            self.table.setRowCount(0)
            return
        if self.app_state.get("role") != "driver":
            self.info_label.setText("Only drivers can manage a schedule. Switch to driver role to add entries.")
            self.entries = []
            self.table.setRowCount(0)
            return
        try:
            response = api.list_schedule(user_id)
        except ApiClientError as exc:
            self.info_label.setText(f"Unable to load schedule: {exc}")
            return
        self.entries = response.get("payload", {}).get("entries", [])
        self.table.setRowCount(len(self.entries))
        for row, entry in enumerate(self.entries):
            self.table.setItem(row, 0, QTableWidgetItem(entry.get("day", "")))
            self.table.setItem(row, 1, QTableWidgetItem(entry.get("time", "")))
            self.table.setItem(row, 2, QTableWidgetItem(entry.get("direction", "")))
            self.table.setItem(row, 3, QTableWidgetItem(entry.get("area", "")))
            # store schedule id in first column
            self.table.item(row, 0).setData(Qt.UserRole, entry.get("id"))

    def delete_selected(self):
        selected = self.table.currentRow()
        if selected < 0 or selected >= len(self.entries):
            QMessageBox.information(self, "Select entry", "Choose a schedule row to delete.")
            return
        entry = self.entries[selected]
        schedule_id = entry.get("id")
        api = self.api()
        user_id = self.current_user()
        if not api or not user_id or not schedule_id:
            return
        try:
            api.delete_schedule_entry(user_id, schedule_id)
        except ApiClientError as exc:
            QMessageBox.critical(self, "Unable to delete", str(exc))
            return
        self.refresh_entries()
