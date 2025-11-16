# preliminary_page.py
# Page that asks user whether they are a driver or passenger.

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout # type: ignore
from PyQt5.QtGui import QFont # type: ignore
from PyQt5.QtCore import Qt # type: ignore
from logo_widget import get_logo_label, AUBUS_MAROON
from ui_styles import style_button, set_title_label
from api_client import ApiClientError
from PyQt5.QtWidgets import QMessageBox  # type: ignore

class PreliminaryPage(QWidget):
    def __init__(self, parent_stack=None, app_state=None):
        super().__init__()
        self.setObjectName("PreliminaryPage")
        self.parent_stack = parent_stack
        self.app_state = app_state or {}
        self.init_ui()

    def init_ui(self):
        outer = QVBoxLayout()
        outer.addStretch()

        # Center content with horizontal padding
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignCenter)

        logo = get_logo_label(size=80)
        logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo)

        label = QLabel("Are you driving or looking for a ride?")
        set_title_label(label, size=14)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        row = QHBoxLayout()
        row.setAlignment(Qt.AlignCenter)
        passenger_btn = QPushButton("Passenger")
        passenger_btn.clicked.connect(lambda: self.choose_role("passenger"))
        style_button(passenger_btn)
        row.addWidget(passenger_btn)

        driver_btn = QPushButton("Driver")
        driver_btn.clicked.connect(lambda: self.choose_role("driver"))
        style_button(driver_btn)
        row.addWidget(driver_btn)
        layout.addLayout(row)

        # Wrap centered layout with horizontal padding
        h_layout = QHBoxLayout()
        h_layout.addStretch()
        h_layout.addLayout(layout)
        h_layout.addStretch()

        outer.addLayout(h_layout)
        outer.addStretch()

        self.setStyleSheet(f"QLabel{{ color: {AUBUS_MAROON}; }} QPushButton{{ padding:8px; border-radius:6px; }}")
        self.setLayout(outer)

    def choose_role(self, role):
        api = self.app_state.get("api")
        user_id = self.app_state.get("user_id")
        if not api or not user_id:
            QMessageBox.warning(self, "Not ready", "Please log in again.")
            return
        try:
            api.set_role(user_id, role, self.app_state.get("area"))
        except ApiClientError as exc:
            QMessageBox.critical(self, "Unable to save", str(exc))
            return
        self.app_state['role'] = role
        self.app_state['role_selected'] = True
        if self.parent_stack:
            main_page = self.parent_stack.findChild(QWidget, "MainPage")
            if main_page:
                self.parent_stack.setCurrentIndex(self.parent_stack.indexOf(main_page))

    def reset_role(self):
        """Clear the role selection from app state."""
        if 'role' in self.app_state:
            del self.app_state['role']
