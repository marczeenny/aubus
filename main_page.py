# main_page.py
# Main hub page with tabs: Ride, Previous, Settings, Messages.
# The RideTab has a callback to navigate to the ProgressPage when a ride is accepted.

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTabWidget # type: ignore
from PyQt5.QtCore import QTimer # type: ignore
from logo_widget import get_logo_label, AUBUS_MAROON
from ui_styles import set_title_label
from ride_tab import RideTab
from schedule_tab import ScheduleTab
from previous_tab import PreviousTab
from settings_tab import SettingsTab
from messages_tab import MessagesTab
from progress_page import ProgressPage

class MainPage(QWidget):
    def __init__(self, parent_stack=None, app_state=None):
        super().__init__()
        self.setObjectName("MainPage")
        self.parent_stack = parent_stack
        self.app_state = app_state or {}
        self.login_page = None  # Will be set by app.py if needed
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(get_logo_label(size=64))
        title = QLabel("Main Hub")
        set_title_label(title, size=16)
        layout.addWidget(title)

        self.tabs = QTabWidget()
        # Ride tab - pass a callback to open progress page
        self.progress_page = ProgressPage(self.app_state, on_ride_end=self.hide_progress)
        self.ride_tab = RideTab(app_state=self.app_state, go_to_progress=self.show_progress)
        self.schedule_tab = ScheduleTab(self.app_state)
        self.previous_tab = PreviousTab(self.app_state)
        self.messages_tab = MessagesTab(self.app_state)
        self.settings_tab = SettingsTab(self.app_state, on_logout=self.logout)
        self.tabs.addTab(self.ride_tab, "Ride")
        self.update_schedule_tab_visibility(initial=True)
        self.tabs.addTab(self.previous_tab, "Previous")
        self.tabs.addTab(self.settings_tab, "Settings")
        self.tabs.addTab(self.messages_tab, "Messages")
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
            if event.type in {"RIDE_REQUEST", "DRIVER_RESPONSE", "RIDE_CREATED"}:
                self.ride_tab.handle_event(event)
            if event.type in {"CHAT_MESSAGE", "CONTACTS", "MESSAGES", "CONNECTION_LOST"}:
                self.messages_tab.handle_event(event)

    def update_schedule_tab_visibility(self, initial=False):
        is_driver = self.app_state.get("role") == "driver" or self.app_state.get("is_driver")
        index = self.tabs.indexOf(self.schedule_tab)
        if is_driver and index == -1:
            self.tabs.insertTab(1, self.schedule_tab)
            if not initial:
                self.schedule_tab.refresh_entries()
        elif not is_driver and index != -1:
            self.tabs.removeTab(index)
