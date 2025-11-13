# ride_tab.py
# Ride tab: enter departure time/place, number of seats if driver, and press "Ride"
# Shows a "match list" with accept/deny (simulated). This tab is intended to be integrated
# later with the server (use send_json / recv_json).

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QSpinBox, # type: ignore
                             QPushButton, QListWidget, QListWidgetItem, QHBoxLayout, QMessageBox)
from PyQt5.QtGui import QFont # type: ignore
from logo_widget import AUBUS_MAROON

class RideTab(QWidget):
    def __init__(self, app_state=None, go_to_progress=None):
        """
        app_state: shared state dict
        go_to_progress: callable (ride_info) -> shows progress page
        """
        super().__init__()
        self.app_state = app_state or {}
        self.go_to_progress = go_to_progress
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        title = QLabel("Request / Offer a Ride")
        title.setFont(QFont("Verdana", 14))
        title.setStyleSheet(f"color: {AUBUS_MAROON};")
        layout.addWidget(title)

        self.place_input = QLineEdit()
        self.place_input.setPlaceholderText("Departure place / area")
        layout.addWidget(self.place_input)

        self.time_input = QLineEdit()
        self.time_input.setPlaceholderText("Departure time (e.g. 08:30)")
        layout.addWidget(self.time_input)

        self.seats_input = QSpinBox()
        self.seats_input.setMinimum(1)
        self.seats_input.setMaximum(10)
        self.seats_input.setValue(1)
        self.seats_input.setPrefix("Seats: ")
        layout.addWidget(self.seats_input)

        ride_btn = QPushButton("Ride")
        ride_btn.clicked.connect(self.on_ride_clicked)
        layout.addWidget(ride_btn)

        # matches list (drivers for passenger / passengers for driver)
        self.matches_list = QListWidget()
        layout.addWidget(self.matches_list)

        # Accept / Deny buttons (simulate driver's controls)
        btn_row = QHBoxLayout()
        accept_btn = QPushButton("Accept Selected")
        accept_btn.clicked.connect(self.on_accept_selected)
        btn_row.addWidget(accept_btn)
        deny_btn = QPushButton("Deny Selected")
        deny_btn.clicked.connect(self.on_deny_selected)
        btn_row.addWidget(deny_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def on_ride_clicked(self):
        place = self.place_input.text().strip()
        time = self.time_input.text().strip()
        seats = self.seats_input.value()

        if not place or not time:
            QMessageBox.warning(self, "Missing info", "Please enter place and time.")
            return

        role = self.app_state.get('role', 'passenger')
        # TODO: Send REQUEST_RIDE or ADD_SCHEDULE to backend here with send_json()

        # For demo, generate dummy matches
        self.matches_list.clear()
        if role == 'passenger':
            # show drivers
            for i in range(1, 5):
                item = QListWidgetItem(f"Driver {i} — area: {place} — leaves at {time} — rating: {3+i%3}")
                self.matches_list.addItem(item)
        else:
            # show passenger requests
            for i in range(1, 4):
                item = QListWidgetItem(f"Passenger {i} — wants {seats} seats — {place} at {time}")
                self.matches_list.addItem(item)

    def on_accept_selected(self):
        # For simulation: mark selected item accepted and if both sides accepted, go to progress
        item = self.matches_list.currentItem()
        if not item:
            QMessageBox.information(self, "Select one", "Please select a match to accept.")
            return
        item.setText(item.text() + " — ACCEPTED")
        # In real app, notify backend. For demo, proceed to progress page when accepted
        if self.go_to_progress:
            ride_info = {
                "place": self.place_input.text(),
                "time": self.time_input.text(),
                "accepted_by": item.text()
            }
            self.go_to_progress(ride_info)

    def on_deny_selected(self):
        item = self.matches_list.currentItem()
        if not item:
            QMessageBox.information(self, "Select one", "Please select a match to deny.")
            return
        item.setText(item.text() + " — DENIED")
        # In real app, notify backend
