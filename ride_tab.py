from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QSpinBox,
                             QPushButton, QListWidget, QListWidgetItem, QHBoxLayout, QMessageBox)  # type: ignore
from PyQt5.QtCore import Qt  # type: ignore
from ui_styles import style_button, set_title_label, style_input
from api_client import ApiClientError


class RideTab(QWidget):
    def __init__(self, app_state=None, go_to_progress=None):
        """
        app_state: shared state dict
        go_to_progress: callable (ride_info) -> shows progress page
        """
        super().__init__()
        self.app_state = app_state or {}
        self.go_to_progress = go_to_progress
        self.driver_results = []
        self.pending_passenger_requests = {}
        self.pending_driver_requests = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        title = QLabel("Request / Offer a Ride")
        set_title_label(title, size=14)
        layout.addWidget(title)

        self.place_input = QLineEdit()
        self.place_input.setPlaceholderText("Departure place / area")
        style_input(self.place_input, width=300)
        layout.addWidget(self.place_input)

        self.day_input = QLineEdit()
        self.day_input.setPlaceholderText("Day (e.g. Monday)")
        style_input(self.day_input, width=300)
        layout.addWidget(self.day_input)

        self.time_input = QLineEdit()
        self.time_input.setPlaceholderText("Departure time (e.g. 08:30)")
        style_input(self.time_input, width=300)
        layout.addWidget(self.time_input)

        self.seats_input = QSpinBox()
        self.seats_input.setMinimum(1)
        self.seats_input.setMaximum(10)
        self.seats_input.setValue(1)
        self.seats_input.setPrefix("Seats: ")
        style_input(self.seats_input, width=140)
        layout.addWidget(self.seats_input)

        ride_btn = QPushButton("Ride")
        ride_btn.clicked.connect(self.on_ride_clicked)
        style_button(ride_btn)
        layout.addWidget(ride_btn)

        self.matches_list = QListWidget()
        layout.addWidget(self.matches_list)

        btn_row = QHBoxLayout()
        accept_btn = QPushButton("Accept Selected")
        accept_btn.clicked.connect(self.on_accept_selected)
        style_button(accept_btn, min_height=30)
        btn_row.addWidget(accept_btn)
        deny_btn = QPushButton("Deny Selected")
        deny_btn.clicked.connect(self.on_deny_selected)
        style_button(deny_btn, min_height=30)
        btn_row.addWidget(deny_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def current_role(self):
        return self.app_state.get('role', 'passenger')

    def on_ride_clicked(self):
        place = self.place_input.text().strip()
        day = self.day_input.text().strip()
        time = self.time_input.text().strip()
        if not place or not day or not time:
            QMessageBox.warning(self, "Missing info", "Please enter place, day, and time.")
            return

        api = self.app_state.get("api")
        user_id = self.app_state.get("user_id")
        if not api or not user_id:
            QMessageBox.warning(self, "Not ready", "Please log in again.")
            return

        role = self.current_role()
        if role == 'passenger':
            try:
                response = api.request_drivers(area=place, day=day, time=time)
            except ApiClientError as exc:
                QMessageBox.critical(self, "Request failed", str(exc))
                return
            drivers = response.get("payload", {}).get("drivers", [])
            self.driver_results = drivers
            self.matches_list.clear()
            for driver in drivers:
                item = QListWidgetItem(f"{driver['name']} - {driver['username']} - rating: {driver['rating']:.2f} - leaves at {driver['time']}")
                item.setData(Qt.UserRole, driver)
                self.matches_list.addItem(item)
            if not drivers:
                QMessageBox.information(self, "No drivers", "No available drivers matched your search.")
        else:
            try:
                api.add_schedule(user_id, day=day, time=time, direction="to_AUB", area=place)
            except ApiClientError as exc:
                QMessageBox.critical(self, "Schedule error", str(exc))
                return
            QMessageBox.information(self, "Schedule saved", "Availability saved. Incoming requests will appear below.")
            self.refresh_driver_requests()

    def on_accept_selected(self):
        item = self.matches_list.currentItem()
        if not item:
            QMessageBox.information(self, "Select one", "Please select a list item first.")
            return
        api = self.app_state.get("api")
        user_id = self.app_state.get("user_id")
        if not api or not user_id:
            QMessageBox.warning(self, "Not ready", "Please log in again.")
            return
        role = self.current_role()
        if role == 'passenger':
            driver = item.data(Qt.UserRole)
            if not driver:
                return
            day = self.day_input.text().strip()
            time = self.time_input.text().strip()
            area = self.place_input.text().strip()
            try:
                response = api.create_ride(passenger_id=user_id, driver_id=driver["id"], day=day, time=time, area=area)
            except ApiClientError as exc:
                QMessageBox.critical(self, "Unable to request ride", str(exc))
                return
            ride_id = response.get("payload", {}).get("ride_id")
            if ride_id:
                self.pending_passenger_requests[ride_id] = {
                    "ride_id": ride_id,
                    "place": area,
                    "time": time,
                    "day": day,
                    "partner_name": driver["name"],
                    "partner_username": driver.get("username"),
                    "partner_id": driver.get("id"),
                    "role": "passenger"
                }
                QMessageBox.information(self, "Request sent", f"Request sent to {driver['name']}. Waiting for response.")
        else:
            ride = item.data(Qt.UserRole)
            if not ride:
                return
            try:
                resp = api.respond_to_ride(ride["ride_id"], "ACCEPTED")
            except ApiClientError as exc:
                QMessageBox.critical(self, "Unable to respond", str(exc))
                return
            saved = self.pending_driver_requests.pop(ride["ride_id"], None)
            if saved and self.go_to_progress:
                self.app_state["current_ride"] = {
                    "ride_id": ride["ride_id"],
                    "place": saved["area"],
                    "time": saved["time"],
                    "partner_name": saved["passenger_name"],
                    "partner_username": saved.get("passenger_username"),
                    "partner_id": saved.get("passenger_id"),
                    "role": "driver"
                }
                self.go_to_progress(self.app_state["current_ride"])
            self.refresh_driver_requests()

    def on_deny_selected(self):
        item = self.matches_list.currentItem()
        if not item:
            QMessageBox.information(self, "Select one", "Please select a match to deny.")
            return
        role = self.current_role()
        api = self.app_state.get("api")
        if role == 'driver':
            ride = item.data(Qt.UserRole)
            if ride and api:
                try:
                    api.respond_to_ride(ride["ride_id"], "DENIED")
                except ApiClientError as exc:
                    QMessageBox.critical(self, "Unable to deny", str(exc))
            self.refresh_driver_requests()
        item.setText(item.text() + " - DENIED")

    def refresh_driver_requests(self):
        if self.current_role() != 'driver':
            return
        api = self.app_state.get("api")
        user_id = self.app_state.get("user_id")
        if not api or not user_id:
            return
        try:
            response = api.fetch_pending_rides(user_id)
        except ApiClientError:
            return
        rides = response.get("payload", {}).get("rides", [])
        self.matches_list.clear()
        self.pending_driver_requests = {ride["ride_id"]: ride for ride in rides}
        for ride in rides:
            item = QListWidgetItem(f"Passenger {ride['passenger_name']} - {ride['area']} at {ride['time']} ({ride['day']})")
            item.setData(Qt.UserRole, ride)
            self.matches_list.addItem(item)

    def handle_event(self, event):
        role = self.current_role()
        if event.type == "RIDE_REQUEST" and role == "driver":
            payload = event.payload
            ride_id = payload.get("ride_id")
            if not ride_id:
                return
            ride = {
                "ride_id": ride_id,
                "passenger_id": payload.get("passenger_id"),
                "passenger_username": payload.get("passenger_username"),
                "passenger_name": payload.get("passenger_name") or f"Passenger {payload.get('passenger_id')}",
                "area": payload.get("area"),
                "day": payload.get("day"),
                "time": payload.get("time"),
                "status": "REQUESTED"
            }
            self.pending_driver_requests[ride_id] = ride
            item = QListWidgetItem(f"{ride['passenger_name']} - {ride['area']} at {ride['time']} ({ride['day']})")
            item.setData(Qt.UserRole, ride)
            self.matches_list.addItem(item)
        elif event.type == "DRIVER_RESPONSE" and role == "passenger":
            payload = event.payload
            ride_id = payload.get("ride_id")
            status = payload.get("status")
            info = self.pending_passenger_requests.pop(ride_id, None)
            if status == "ACCEPTED" and info and self.go_to_progress:
                self.app_state["current_ride"] = info
                self.go_to_progress(info)
            elif status == "DENIED":
                QMessageBox.information(self, "Ride update", "Driver denied the request.")

    def reset_form(self):
        """Clear form and matches list to allow requesting/offering another ride."""
        self.place_input.clear()
        self.day_input.clear()
        self.time_input.clear()
        self.seats_input.setValue(1)
        self.matches_list.clear()
        self.driver_results = []

    def showEvent(self, event):
        super().showEvent(event)
        if self.current_role() == 'driver':
            self.refresh_driver_requests()
