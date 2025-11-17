# settings_tab.py
# Settings tab: allows changing area, status (driver/passenger), logout button, and placeholders.

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QMessageBox, QHBoxLayout # type: ignore
from PyQt5.QtGui import QFont # type: ignore
from PyQt5.QtCore import Qt # type: ignore
from logo_widget import AUBUS_MAROON
from ui_styles import set_title_label, style_button, style_input
from api_client import ApiClientError

class SettingsTab(QWidget):
    def __init__(self, app_state=None, on_logout=None):
        super().__init__()
        self.app_state = app_state or {}
        self.on_logout = on_logout
        self.init_ui()

    def init_ui(self):
        outer = QVBoxLayout()
        outer.addStretch()

        # Center content with horizontal padding
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("Settings")
        set_title_label(title, size=14)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Area change (use dropdown)
        self.area_input = QComboBox()
        areas = ["-- Select Area --", "Beirut", "Batroun", "Tripoli", "Saida", "Baalbek", "Zahle", "Nabatieh", "Metn"]
        self.area_input.addItems(areas)
        current_area = self.app_state.get('area', "-- Select Area --")
        idx = self.area_input.findText(current_area)
        if idx >= 0:
            self.area_input.setCurrentIndex(idx)
        else:
            self.area_input.setCurrentIndex(0)
        self.area_input.setFixedWidth(320)
        layout.addWidget(self.area_input, alignment=Qt.AlignCenter)

        # Role selection
        self.role_box = QComboBox()
        self.role_box.addItems(["passenger", "driver"])
        current = self.app_state.get('role', 'passenger')
        idx = self.role_box.findText(current)
        if idx >= 0:
            self.role_box.setCurrentIndex(idx)
        self.role_box.setFixedWidth(280)
        layout.addWidget(self.role_box, alignment=Qt.AlignCenter)

        # Save changes (locally)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        style_button(save_btn)
        layout.addWidget(save_btn, alignment=Qt.AlignCenter)

        # Logout
        logout_btn = QPushButton("Logout")
        logout_btn.clicked.connect(self.logout)
        style_button(logout_btn)
        layout.addWidget(logout_btn, alignment=Qt.AlignCenter)

        # Wrap centered layout with horizontal padding
        h_layout = QHBoxLayout()
        h_layout.addStretch()
        h_layout.addLayout(layout)
        h_layout.addStretch()

        outer.addLayout(h_layout)
        outer.addStretch()

        # Styling
        self.setLayout(outer)

    def save_settings(self):
        api = self.app_state.get("api")
        user_id = self.app_state.get("user_id")
        if not api or not user_id:
            QMessageBox.warning(self, "Not authenticated", "Please log in again.")
            return
        area = self.area_input.currentText().strip()
        role = self.role_box.currentText()
        try:
            api.set_role(user_id, role, area)
        except ApiClientError as exc:
            QMessageBox.critical(self, "Unable to save", str(exc))
            return
        self.app_state['area'] = area
        self.app_state['role'] = role
        self.app_state['role_selected'] = True
        QMessageBox.information(self, "Saved", "Settings updated. Please restart (or log in again) to apply.")
        if self.on_logout:
            self.on_logout()

    def logout(self):
        # Clear auth flag while preserving API client reference
        api = self.app_state.get("api")
        self.app_state.clear()
        if api:
            self.app_state["api"] = api
        self.area_input.setCurrentIndex(0)
        self.role_box.setCurrentIndex(0)
        if self.on_logout:
            self.on_logout()
