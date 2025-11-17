from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QSpinBox,
                             QPushButton, QListWidget, QListWidgetItem, QHBoxLayout, QMessageBox, QRadioButton, QComboBox)  # type: ignore
from PyQt5.QtCore import Qt  # type: ignore
from datetime import datetime
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
        self.setLayout(QVBoxLayout())

    def showEvent(self, event):
        super().showEvent(event)
        self.update_ui_for_role()

    def update_ui_for_role(self):
        # Clear existing widgets
        layout = self.layout()
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        role = self.current_role()
        if role == 'passenger':
            self.setup_passenger_ui(layout)
        else:
            self.setup_driver_ui(layout)

    def setup_passenger_ui(self, layout):
        title = QLabel("Request a Ride")
        set_title_label(title, size=14)
        layout.addWidget(title)

        self.from_uni_radio = QRadioButton("From University to My Area")
        self.from_area_radio = QRadioButton("From My Area to University")
        self.from_uni_radio.setChecked(True)
        layout.addWidget(self.from_uni_radio)
        layout.addWidget(self.from_area_radio)



        # Desired time removed — requests will use current time

        request_btn = QPushButton("Request Ride")
        request_btn.clicked.connect(self.on_request_ride_clicked)
        style_button(request_btn)
        layout.addWidget(request_btn)

        self.status_label = QLabel("Waiting for a driver to accept...")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

    def setup_driver_ui(self, layout):
        title = QLabel("Incoming Ride Requests")
        set_title_label(title, size=14)
        layout.addWidget(title)

        self.requests_list = QListWidget()
        layout.addWidget(self.requests_list)

        btn_row = QHBoxLayout()
        accept_btn = QPushButton("Accept")
        accept_btn.clicked.connect(self.on_accept_clicked)
        style_button(accept_btn, min_height=30)
        btn_row.addWidget(accept_btn)
        deny_btn = QPushButton("Deny")
        deny_btn.clicked.connect(self.on_deny_clicked)
        style_button(deny_btn, min_height=30)
        btn_row.addWidget(deny_btn)
        layout.addLayout(btn_row)

        self.refresh_driver_requests()


    def current_role(self):
        return self.app_state.get('role', 'passenger')

    def on_request_ride_clicked(self):
        direction = "To University" if self.from_area_radio.isChecked() else "From University"
        now = datetime.now()
        day = now.strftime("%A")
        time = now.strftime("%H:%M")

        api = self.app_state.get("api")
        user_id = self.app_state.get("user_id")
        area = self.app_state.get("area") # Retrieve passenger's area
        if not api or not user_id or not area: # Check if area is available
            QMessageBox.warning(self, "Not ready", "Please log in again or ensure your area is set.")
            return

        try:
            response = api.broadcast_ride_request(passenger_id=user_id, direction=direction, day=day, time=time, area=area) # Pass area to API call
        except ApiClientError as exc:
            QMessageBox.critical(self, "Request failed", str(exc))
            return
        
        if response.get("type") == "BROADCAST_OK":
            self.status_label.setText("Request sent to available drivers. Waiting for responses...")
            self.status_label.setVisible(True)
        elif response.get("type") == "NO_DRIVERS_FOUND":
            QMessageBox.information(self, "No drivers", "No available drivers found for the next 15 minutes.")


    def on_accept_clicked(self):
        item = self.requests_list.currentItem()
        if not item:
            QMessageBox.information(self, "Select one", "Please select a request to accept.")
            return
        
        ride = item.data(Qt.UserRole)
        if not ride:
            return

        api = self.app_state.get("api")
        driver_id = self.app_state.get("user_id")
        if not api or not driver_id:
            QMessageBox.warning(self, "Not ready", "Please log in again.")
            return

        try:
            response = api.respond_to_ride(ride["ride_id"], "ACCEPTED")
        except ApiClientError as exc:
            QMessageBox.critical(self, "Unable to respond", str(exc))
            return
        
        if response.get("payload", {}).get("status") == "ACCEPTED":
            QMessageBox.information(self, "Ride Accepted", "You have accepted the ride.")
        else:
            QMessageBox.information(self, "Ride Closed", "This ride is no longer available.")

        self.refresh_driver_requests()

    def on_deny_clicked(self):
        item = self.requests_list.currentItem()
        if not item:
            QMessageBox.information(self, "Select one", "Please select a request to deny.")
            return

        ride = item.data(Qt.UserRole)
        if not ride:
            return
            
        api = self.app_state.get("api")
        driver_id = self.app_state.get("user_id")
        if not api or not driver_id:
            QMessageBox.warning(self, "Not ready", "Please log in again.")
            return

        try:
            api.respond_to_ride(ride["ride_id"], "DENIED")
        except ApiClientError as exc:
            QMessageBox.critical(self, "Unable to deny", str(exc))
        
        self.refresh_driver_requests()

    def refresh_driver_requests(self):
        if self.current_role() != 'driver':
            return
        api = self.app_state.get("api")
        user_id = self.app_state.get("user_id")
        if not api or not user_id:
            return
        try:
            response = api.fetch_ride_requests(user_id)
        except ApiClientError:
            return
        
        requests = response.get("payload", {}).get("requests", [])
        self.requests_list.clear()
        for req in requests:
            item = QListWidgetItem(f"Passenger: {req['passenger_name']} - {req['direction']} at {req['time']}")
            item.setData(Qt.UserRole, req)
            self.requests_list.addItem(item)

    def handle_event(self, event):
        role = self.current_role()
        if role == "driver":
            if event.type == "RIDE_REQUEST":
                self.refresh_driver_requests()
            elif event.type == "RIDE_UNAVAILABLE":
                ride_id = event.payload.get("ride_id")
                for i in range(self.requests_list.count()):
                    item = self.requests_list.item(i)
                    ride = item.data(Qt.UserRole)
                    if ride and ride["ride_id"] == ride_id:
                        self.requests_list.takeItem(i)
                        break
        elif role == "passenger":
            if event.type == "DRIVER_RESPONSE":
                payload = event.payload
                status = payload.get("status")
                if status == "ACCEPTED":
                    QMessageBox.information(self, "Ride update", "Driver accepted the request.")
                elif status == "DENIED":
                    QMessageBox.information(self, "Ride update", "Driver denied the request.")



    def reset_form(self):
        """Clear form and matches list."""
        if hasattr(self, 'matches_list'):
            self.matches_list.clear()
        if hasattr(self, 'requests_list'):
            self.requests_list.clear()
        if hasattr(self, 'from_uni_radio'):
            self.from_uni_radio.setChecked(True)
        self.driver_results = []
