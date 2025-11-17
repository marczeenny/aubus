# main_page.py
# Main hub page with tabs: Ride, Previous, Settings, Messages.
# The RideTab has a callback to navigate to the ProgressPage when a ride is accepted.

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTabWidget, QMessageBox # type: ignore
from PyQt5.QtCore import QTimer, Qt # type: ignore
import requests
from logo_widget import get_logo_label, AUBUS_MAROON
from ui_styles import set_title_label
from ride_tab import RideTab
from ride_tab import CurrentRidesTab
from schedule_tab import ScheduleTab
from previous_tab import PreviousTab
from messages_tab import MessagesTab
from progress_page import ProgressPage
from PyQt5.QtWidgets import QPushButton # type: ignore
from ui_styles import style_button

class MainPage(QWidget):
    def __init__(self, parent_stack=None, app_state=None):
        super().__init__()
        self.setObjectName("MainPage")
        self.parent_stack = parent_stack
        self.app_state = app_state or {}
        # expose main page to app_state so child tabs can refresh main tabs
        try:
            self.app_state["main_page"] = self
        except Exception:
            pass
        self.login_page = None  # Will be set by app.py if needed
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(get_logo_label(size=64))
        title = QLabel("Main Hub")
        set_title_label(title, size=16)
        layout.addWidget(title)

        # Simple weather display (uses Open-Meteo free API)
        self.weather_label = QLabel("Weather: unknown")
        layout.addWidget(self.weather_label)
        # start a periodic weather refresh
        try:
            self._update_weather()
        except Exception:
            pass
        self.weather_timer = QTimer(self)
        self.weather_timer.timeout.connect(self._update_weather)
        self.weather_timer.start(10 * 60 * 1000)  # every 10 minutes

        self.tabs = QTabWidget()
        # Ride tab - pass a callback to open progress page
        self.progress_page = ProgressPage(self.app_state, on_ride_end=self.hide_progress)
        self.ride_tab = RideTab(app_state=self.app_state, go_to_progress=self.show_progress)
        self.current_rides_tab = CurrentRidesTab(app_state=self.app_state, go_to_progress=self.show_progress)
        self.schedule_tab = ScheduleTab(self.app_state)
        self.previous_tab = PreviousTab(self.app_state)
        self.messages_tab = MessagesTab(self.app_state)
        # Register peer message callback if peer server is available
        peer_server = self.app_state.get('peer_server')
        if peer_server:
            try:
                peer_server.on_message = self.messages_tab.handle_peer_message
            except Exception:
                pass
        self.tabs.addTab(self.ride_tab, "Ride")
        # Current Rides tab is added dynamically for drivers by update_schedule_tab_visibility
        self.update_schedule_tab_visibility(initial=True)
        self.tabs.addTab(self.previous_tab, "Previous")
        self.tabs.addTab(self.messages_tab, "Messages")

        # Add a visible logout button instead of a Settings tab
        logout_btn = QPushButton("Logout")
        logout_btn.clicked.connect(self.logout)
        style_button(logout_btn)
        layout.addWidget(logout_btn, alignment=Qt.AlignRight)
        self.tabs.currentChanged.connect(self.on_tab_changed)

        layout.addWidget(self.tabs)
        # Add progress page as an extra widget (switch to it when active)
        layout.addWidget(self.progress_page)
        self.progress_page.hide()  # only show when active

        self.setLayout(layout)
        self.event_timer = QTimer(self)
        self.event_timer.timeout.connect(self.dispatch_events)
        self.event_timer.start(750)

    def show_progress(self, ride_info):
        # Load ride info into progress page and display it
        self.app_state["current_ride"] = ride_info
        if hasattr(self, "messages_tab"):
            self.messages_tab.set_active_ride(ride_info)
        self.progress_page.load_ride(ride_info)
        self.progress_page.show()
        # Optionally hide the tabs to focus on progress page
        self.tabs.hide()

    def hide_progress(self):
        # Hide progress page and show tabs again, returning to ride tab
        self.progress_page.hide()
        self.tabs.show()
        self.tabs.setCurrentIndex(0)  # Switch to ride tab (index 0)
        self.ride_tab.reset_form()  # Clear the form for the next ride
        self.app_state.pop("current_ride", None)
        if hasattr(self, "messages_tab"):
            self.messages_tab.clear_active_ride()
        # Update passenger request button state after a ride ends
        if hasattr(self.ride_tab, 'update_request_button_state'):
            try:
                self.ride_tab.update_request_button_state()
            except Exception:
                pass

    def reset_all_pages(self):
        """Reset all tabs and pages to their initial state."""
        self.ride_tab.reset_form()
        self.progress_page.hide()
        self.tabs.show()
        self.tabs.setCurrentIndex(0)  # Show ride tab first
        if hasattr(self, "messages_tab"):
            self.messages_tab.clear_active_ride()
        # Reset messages and previous tabs by clearing any stored data
        # (These are simple demos, but if they store local state, clear it here)

    def logout(self):
        # For demo: return to login screen
        if self.parent_stack:
            self.reset_all_pages()  # Reset all pages
            api = self.app_state.get("api")
            if api:
                api.disconnect()
            self.app_state.clear()  # Clear auth and user data
            if api:
                self.app_state["api"] = api
            # Reset form pages
            login_page = self.parent_stack.findChild(QWidget, "LoginPage")
            register_page = self.parent_stack.findChild(QWidget, "RegisterPage")
            preliminary_page = self.parent_stack.findChild(QWidget, "PreliminaryPage")
            if login_page and hasattr(login_page, 'reset_form'):
                login_page.reset_form()
            if register_page and hasattr(register_page, 'reset_form'):
                register_page.reset_form()
            if preliminary_page and hasattr(preliminary_page, 'reset_role'):
                preliminary_page.reset_role()
            self.parent_stack.setCurrentIndex(self.parent_stack.indexOf(login_page))

    def on_tab_changed(self, index):
        widget = self.tabs.widget(index)
        if widget == self.previous_tab:
            self.previous_tab.refresh_rides()
        elif widget == self.schedule_tab:
            self.schedule_tab.refresh_entries()
        elif widget == self.messages_tab:
            self.messages_tab.refresh_contacts()

    def dispatch_events(self):
        api = self.app_state.get("api")
        if not api:
            return
        self.update_schedule_tab_visibility()
        for event in api.drain_events():
            if event.type in {"RIDE_REQUEST", "DRIVER_RESPONSE", "RIDE_CREATED", "RIDE_UNAVAILABLE", "DRIVER_RESPONSE"}:
                self.ride_tab.handle_event(event)
            # Refresh current rides tab when ride state changes
            if hasattr(self, 'current_rides_tab') and event.type in {"DRIVER_RESPONSE", "RIDE_STARTED", "RIDE_COMPLETED", "RIDE_CANCELLED", "RIDE_REQUEST", "RIDE_UNAVAILABLE"}:
                try:
                    self.current_rides_tab.refresh_list()
                except Exception:
                    pass
            if event.type in {"CHAT_MESSAGE", "CONTACTS", "MESSAGES", "CONNECTION_LOST"}:
                self.messages_tab.handle_event(event)
            # Ride lifecycle notifications for progress page
            if event.type == "RIDE_STARTED":
                rid = event.payload.get("ride_id")
                cur = self.app_state.get("current_ride")
                if cur and cur.get("ride_id") == rid:
                    cur["status"] = "STARTED"
                    self.progress_page.load_ride(cur)
            if event.type == "RIDE_COMPLETED":
                rid = event.payload.get("ride_id")
                cur = self.app_state.get("current_ride")
                if cur and cur.get("ride_id") == rid:
                    QMessageBox.information(self, "Ride completed", "The ride has been completed.")
                    self.hide_progress()
            if event.type == "RIDE_CANCELLED":
                rid = event.payload.get("ride_id")
                cur = self.app_state.get("current_ride")
                if cur and cur.get("ride_id") == rid:
                    QMessageBox.information(self, "Ride cancelled", "This ride was cancelled.")
                    self.hide_progress()

    def update_schedule_tab_visibility(self, initial=False):
        is_driver = self.app_state.get("role") == "driver" or self.app_state.get("is_driver")
        index = self.tabs.indexOf(self.schedule_tab)
        if is_driver and index == -1:
            # insertTab requires a label (or icon+label). Provide a label to avoid TypeError.
            self.tabs.insertTab(1, self.schedule_tab, "Schedule")
            # also insert Current Rides tab after Ride
            try:
                self.tabs.insertTab(2, self.current_rides_tab, "Current Ride")
            except Exception:
                pass
            if not initial:
                self.schedule_tab.refresh_entries()
        elif not is_driver and index != -1:
            self.tabs.removeTab(index)
            # remove current rides tab if present
            cr_index = self.tabs.indexOf(self.current_rides_tab)
            if cr_index != -1:
                self.tabs.removeTab(cr_index)

    def _update_weather(self):
        # For demo, use Beirut coordinates; map area -> coords could be added.
        try:
            url = "https://api.open-meteo.com/v1/forecast?latitude=33.9&longitude=35.5&current_weather=true"
            r = requests.get(url, timeout=3.0)
            if r.status_code == 200:
                data = r.json()
                cw = data.get('current_weather', {})
                temp = cw.get('temperature')
                wind = cw.get('windspeed')
                if temp is not None:
                    self.weather_label.setText(f"Weather: {temp}°C, wind {wind} km/h")
                    return
        except Exception:
            pass
        self.weather_label.setText("Weather: unavailable")
