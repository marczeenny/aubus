# progress_page.py
# Progress page: shows ride details and weather. Driver can start/end ride.
# Weather widget is a placeholder; a real API integration should replace 'refresh_weather' behavior.

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QMessageBox # type: ignore
from PyQt5.QtGui import QFont # type: ignore
from logo_widget import get_logo_label, AUBUS_MAROON

class ProgressPage(QWidget):
    def __init__(self, app_state=None):
        super().__init__()
        self.setObjectName("ProgressPage")
        self.app_state = app_state or {}
        self.ride_info = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(get_logo_label(size=64))

        self.info_label = QLabel("No active ride.")
        self.info_label.setFont(QFont("Verdana", 12))
        self.info_label.setStyleSheet(f"color: {AUBUS_MAROON};")
        layout.addWidget(self.info_label)

        # Buttons
        row = QHBoxLayout()
        self.start_btn = QPushButton("Start Ride")
        self.start_btn.clicked.connect(self.start_ride)
        self.end_btn = QPushButton("End Ride")
        self.end_btn.clicked.connect(self.end_ride)
        row.addWidget(self.start_btn)
        row.addWidget(self.end_btn)
        layout.addLayout(row)

        # Weather panel
        layout.addWidget(QLabel("Weather (demo):"))
        self.weather_label = QLabel("Temperature: -- °C\nWind: -- m/s\nForecast: --")
        layout.addWidget(self.weather_label)
        self.refresh_weather_btn = QPushButton("Refresh Weather (placeholder)")
        self.refresh_weather_btn.clicked.connect(self.refresh_weather)
        layout.addWidget(self.refresh_weather_btn)

        self.setLayout(layout)

    def load_ride(self, ride_info):
        """
        Called when a ride becomes active. ride_info is a dict with keys like 'place', 'time', 'accepted_by' etc.
        """
        self.ride_info = ride_info
        s = f"Ride to {ride_info.get('place')} at {ride_info.get('time')}\nPartner: {ride_info.get('accepted_by')}"
        self.info_label.setText(s)

    def start_ride(self):
        # TODO: notify backend / peers
        QMessageBox.information(self, "Ride started", "Ride marked as started (demo).")

    def end_ride(self):
        # TODO: notify backend / peers, mark ride complete
        QMessageBox.information(self, "Ride ended", "Ride marked as completed (demo).")

    def refresh_weather(self):
        # Placeholder: replace with real weather API call (OpenWeatherMap etc.)
        # Example: call your own server which calls OWM and returns JSON, then set weather_label accordingly.
        # For now show demo values:
        demo = "Temperature: 24 °C\nWind: 3.2 m/s\nForecast: Partly cloudy"
        self.weather_label.setText(demo)
