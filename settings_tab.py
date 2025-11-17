# settings_tab.py
# Settings tab: allows changing area, status (driver/passenger), logout button, and placeholders.

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox, QHBoxLayout, QSpinBox # type: ignore
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

        # Minimum-rating preference
        self.min_rating_spin = QSpinBox()
        self.min_rating_spin.setRange(0, 5)
        self.min_rating_spin.setFixedWidth(120)
        min_rating_val = int(self.app_state.get('min_rating', 0) or 0)
        self.min_rating_spin.setValue(min_rating_val)
        layout.addWidget(QLabel("Minimum partner rating (0-5):"), alignment=Qt.AlignCenter)
        layout.addWidget(self.min_rating_spin, alignment=Qt.AlignCenter)

        # Save changes (locally)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        style_button(save_btn)
        layout.addWidget(save_btn, alignment=Qt.AlignCenter)

        # (No logout button — settings tab only edits minimum-rating preference)

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
        # We only update the minimum-rating preference here. Use existing role/area from app_state.
        role = self.app_state.get('role', 'passenger')
        area = self.app_state.get('area')
        try:
            min_rating = int(self.min_rating_spin.value())
            api.set_role(user_id, role, area, min_rating=min_rating)
        except ApiClientError as exc:
            QMessageBox.critical(self, "Unable to save", str(exc))
            return
        self.app_state['min_rating'] = int(self.min_rating_spin.value())
        QMessageBox.information(self, "Saved", "Minimum rating preference updated.")

    # logout removed — this settings tab does not include logout functionality
