# main_page.py
# Main hub page with tabs: Ride, Previous, Settings, Messages.
# The RideTab has a callback to navigate to the ProgressPage when a ride is accepted.

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTabWidget # type: ignore
from PyQt5.QtGui import QFont # type: ignore
from logo_widget import get_logo_label, AUBUS_MAROON
from ride_tab import RideTab
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
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(get_logo_label(size=64))
        title = QLabel("Main Hub")
        title.setFont(QFont("Verdana", 16))
        title.setStyleSheet(f"color: {AUBUS_MAROON};")
        layout.addWidget(title)

        self.tabs = QTabWidget()
        # Ride tab — pass a callback to open progress page
        self.progress_page = ProgressPage(self.app_state)
        self.ride_tab = RideTab(app_state=self.app_state, go_to_progress=self.show_progress)
        self.tabs.addTab(self.ride_tab, "Ride")
        self.tabs.addTab(PreviousTab(self.app_state), "Previous")
        self.tabs.addTab(SettingsTab(self.app_state, on_logout=self.logout), "Settings")
        self.tabs.addTab(MessagesTab(self.app_state), "Messages")

        layout.addWidget(self.tabs)
        # Add progress page as an extra widget (switch to it when active)
        layout.addWidget(self.progress_page)
        self.progress_page.hide()  # only show when active

        self.setLayout(layout)

    def show_progress(self, ride_info):
        # Load ride info into progress page and display it
        self.progress_page.load_ride(ride_info)
        self.progress_page.show()
        # Optionally hide the tabs to focus on progress page
        self.tabs.hide()

    def logout(self):
        # For demo: return to login screen
        if self.parent_stack:
            self.app_state.clear()
            self.parent_stack.setCurrentIndex(self.parent_stack.indexOf(self.parent_stack.findChild(QWidget, "LoginPage")))
