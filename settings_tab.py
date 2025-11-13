# settings_tab.py
# Settings tab: allows changing area, status (driver/passenger), logout button, and placeholders.

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QMessageBox # type: ignore
from PyQt5.QtGui import QFont # type: ignore
from logo_widget import AUBUS_MAROON

class SettingsTab(QWidget):
    def __init__(self, app_state=None, on_logout=None):
        super().__init__()
        self.app_state = app_state or {}
        self.on_logout = on_logout
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        title = QLabel("Settings")
        title.setFont(QFont("Verdana", 14))
        title.setStyleSheet(f"color: {AUBUS_MAROON};")
        layout.addWidget(title)

        # Area change
        self.area_input = QLineEdit()
        self.area_input.setPlaceholderText("Area (e.g. Ras Beirut)")
        self.area_input.setText(self.app_state.get('area', ''))
        layout.addWidget(self.area_input)

        # Role selection
        self.role_box = QComboBox()
        self.role_box.addItems(["passenger", "driver"])
        current = self.app_state.get('role', 'passenger')
        idx = self.role_box.findText(current)
        if idx >= 0:
            self.role_box.setCurrentIndex(idx)
        layout.addWidget(self.role_box)

        # Save changes (locally)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)

        # Logout
        logout_btn = QPushButton("Logout")
        logout_btn.clicked.connect(self.logout)
        layout.addWidget(logout_btn)

        # Styling
        self.setLayout(layout)

    def save_settings(self):
        self.app_state['area'] = self.area_input.text().strip()
        self.app_state['role'] = self.role_box.currentText()
        QMessageBox.information(self, "Saved", "Settings saved locally. Integrate with backend to persist.")

    def logout(self):
        # Clear auth flag and call on_logout
        self.app_state.clear()
        if self.on_logout:
            self.on_logout()
