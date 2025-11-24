# progress_page.py
# Progress page: shows ride details and weather. Driver can start/end ride.
# Weather widget is a placeholder; a real API integration should replace 'refresh_weather' behavior.

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QMessageBox # type: ignore
from logo_widget import get_logo_label
from ui_styles import set_title_label, style_button
from api_client import ApiClientError

class ProgressPage(QWidget):
    def __init__(self, app_state=None, on_ride_end=None):
        super().__init__()
        self.setObjectName("ProgressPage")
        self.app_state = app_state or {}
        self.ride_info = {}
        self.on_ride_end = on_ride_end
        self.ride_started = False  # Track if ride has been started
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(get_logo_label(size=64))

        self.info_label = QLabel("No active ride.")
        set_title_label(self.info_label, size=12)
        layout.addWidget(self.info_label)

        # Buttons
        row = QHBoxLayout()
        self.start_btn = QPushButton("Start Ride")
        self.start_btn.clicked.connect(self.start_ride)
        style_button(self.start_btn, min_height=32)
        self.end_btn = QPushButton("End Ride")
        self.end_btn.clicked.connect(self.end_ride)
        self.end_btn.setEnabled(False)  # Disabled until ride is started
        style_button(self.end_btn, min_height=32)
        # Leave button for passengers to leave before ride starts
        self.leave_btn = QPushButton("Leave Ride")
        self.leave_btn.clicked.connect(self.leave_ride)
        self.leave_btn.setVisible(False)
        style_button(self.leave_btn, min_height=32)
        row.addWidget(self.start_btn)
        row.addWidget(self.end_btn)
        row.addWidget(self.leave_btn)
        layout.addLayout(row)

        # (Weather removed from this page — kept in Main page only)

        self.setLayout(layout)

    def load_ride(self, ride_info):
        """
        Called when a ride becomes active. ride_info is a dict with keys like 'place', 'time', 'partner_name', etc.
        """
        self.ride_info = ride_info
        self.ride_started = False  # Reset ride started flag
        role = ride_info.get("role", "passenger")
        self.start_btn.setVisible(role == "driver")
        self.start_btn.setEnabled(role == "driver")
        # End button is enabled when the ride is started
        started = (ride_info.get("status") == "STARTED")
        self.end_btn.setEnabled(started)
        # Show leave option for passenger when ride not started
        if role == "passenger":
            self.leave_btn.setVisible(ride_info.get("status") != "STARTED")
            self.leave_btn.setEnabled(ride_info.get("status") != "STARTED")
        else:
            self.leave_btn.setVisible(False)
        # Determine partner display. For passengers show their driver; for drivers show
        # a summary of current passengers (avoid showing a single "first" passenger).
        partner = None
        if role == 'driver':
            # Try to fetch all accepted/started rides for this driver and list passenger names
            api = self.app_state.get('api')
            user_id = self.app_state.get('user_id')
            passengers = []
            if api and user_id:
                try:
                    resp = api.fetch_rides(user_id)
                    rides = resp.get('payload', {}).get('rides', [])
                    # collect partner names for rides where this user is driver and status is ACCEPTED or STARTED
                    for r in rides:
                        if r.get('role') == 'driver' and r.get('status') in ("ACCEPTED", "STARTED"):
                            name = r.get('partner_name') or r.get('passenger_name') or r.get('partner_username')
                            if name:
                                passengers.append(name)
                except Exception:
                    passengers = []
            if passengers:
                if len(passengers) == 1:
                    partner = passengers[0]
                else:
                    partner = f"Passengers ({len(passengers)}): {', '.join(passengers)}"
            else:
                # Fallback to ride_info fields if fetch failed or no passengers found
                partner = ride_info.get('partner_name') or ride_info.get('accepted_by') or 'Passengers'
        else:
            # passenger view — show the driver name if available
            partner = ride_info.get('partner_name') or ride_info.get('accepted_by') or ride_info.get('partner_username') or 'Driver'

        # Determine a sensible destination string. Prefer explicit 'place', then 'area',
        # then try to infer from 'direction' (e.g. contains 'University'), otherwise default.
        place = ride_info.get('place')
        if not place:
            place = ride_info.get('area')
        if not place:
            direction = (ride_info.get('direction') or "").lower()
            if 'university' in direction or 'to university' in direction:
                place = 'to university'
            elif 'from university' in direction:
                place = 'from university'
            else:
                # Fallback: prefer driver's area from app_state when available
                place = ride_info.get('area') or self.app_state.get('area') or 'to university'

        s = f"Ride to {place} at {ride_info.get('time')}\nPartner: {partner}\nRole: {role}"
        self.info_label.setText(s)

    def start_ride(self):
        if self.ride_info.get("role") != "driver":
            return
        api = self.app_state.get("api")
        ride_id = self.ride_info.get("ride_id")
        if not api or not ride_id:
            QMessageBox.warning(self, "No ride", "Cannot start ride without an active ride.")
            return
        try:
            api.start_ride(ride_id)
        except ApiClientError as exc:
            QMessageBox.critical(self, "Unable to start", str(exc))
            return
        QMessageBox.information(self, "Ride started", "Ride marked as started.")
        self.ride_started = True
        # Disable start button so it cannot be clicked again
        self.start_btn.setEnabled(False)
        self.start_btn.setText("Started")
        self.end_btn.setEnabled(True)  # Enable end button once ride is started

    def end_ride(self):
        api = self.app_state.get("api")
        ride_id = self.ride_info.get("ride_id")
        if not api or not ride_id:
            QMessageBox.warning(self, "No ride", "Cannot end ride without an active ride.")
            return
        try:
            api.complete_ride(ride_id)
        except ApiClientError as exc:
            QMessageBox.critical(self, "Unable to end ride", str(exc))
            return
        QMessageBox.information(self, "Ride ended", "Ride marked as completed.")
        # Reset buttons for next time
        self.end_btn.setEnabled(False)
        self.start_btn.setEnabled(True)
        self.start_btn.setText("Start Ride")
        self.ride_started = False
        if self.on_ride_end:
            self.on_ride_end()

    def leave_ride(self):
        """Called by passenger to leave/cancel before ride start."""
        api = self.app_state.get("api")
        ride_id = self.ride_info.get("ride_id")
        if not api or not ride_id:
            QMessageBox.warning(self, "No ride", "Cannot leave ride without an active ride.")
            return
        try:
            resp = api.cancel_ride(ride_id)
        except ApiClientError as exc:
            QMessageBox.critical(self, "Unable to leave", str(exc))
            return
        if resp.get("type") == "CANCEL_RIDE_OK":
            QMessageBox.information(self, "Left ride", "You left the ride.")
            # Reset UI
            self.leave_btn.setVisible(False)
            self.leave_btn.setEnabled(False)
            if self.on_ride_end:
                self.on_ride_end()
        else:
            QMessageBox.warning(self, "Unable to leave", resp.get("payload", {}).get("reason", "Unknown reason"))

    def refresh_weather(self):
        # Placeholder: replace with real weather API call (OpenWeatherMap etc.)
        # Example: call your own server which calls OWM and returns JSON, then set weather_label accordingly.
        # For now show demo values:
        demo = "Temperature: 24 deg C\nWind: 3.2 m/s\nForecast: Partly cloudy"
        self.weather_label.setText(demo)
