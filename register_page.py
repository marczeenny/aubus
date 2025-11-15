# register_page.py
# Register page for the AUBus frontend.
# Contains logo, name, email, password, password confirmation, and Register button.
# Basic client-side validation is included (matching passwords, simple email check).

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QHBoxLayout # type: ignore
from PyQt5.QtGui import QFont # type: ignore
from PyQt5.QtCore import Qt # type: ignore
from logo_widget import get_logo_label, AUBUS_MAROON
from validators import is_valid_email
from ui_styles import style_button, set_title_label, style_input
from api_client import ApiClientError

class RegisterPage(QWidget):
    def __init__(self, parent_stack=None, app_state=None):
        super().__init__()
        self.setObjectName("RegisterPage")
        self.parent_stack = parent_stack
        self.app_state = app_state or {}
        self.init_ui()

    def init_ui(self):
        outer = QVBoxLayout()
        outer.addStretch()

        # Center content with horizontal padding
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignCenter)

        # Logo + Title
        logo = get_logo_label(size=80)
        logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo)
        title = QLabel("Create an account")
        set_title_label(title, size=16)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Full name")
        style_input(self.name_input)
        layout.addWidget(self.name_input, alignment=Qt.AlignCenter)

        # Email
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email")
        style_input(self.email_input)
        layout.addWidget(self.email_input, alignment=Qt.AlignCenter)

        # Password
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        style_input(self.password_input)
        layout.addWidget(self.password_input, alignment=Qt.AlignCenter)

        # Confirm password
        self.password_confirm = QLineEdit()
        self.password_confirm.setPlaceholderText("Confirm password")
        self.password_confirm.setEchoMode(QLineEdit.Password)
        style_input(self.password_confirm)
        layout.addWidget(self.password_confirm, alignment=Qt.AlignCenter)

        # Register button
        register_btn = QPushButton("Register")
        register_btn.clicked.connect(self.on_register_clicked)
        style_button(register_btn)
        layout.addWidget(register_btn, alignment=Qt.AlignCenter)

        # Wrap centered layout with horizontal padding
        h_layout = QHBoxLayout()
        h_layout.addStretch()
        h_layout.addLayout(layout)
        h_layout.addStretch()

        outer.addLayout(h_layout)
        outer.addStretch()

        # Simple styling that matches maroon palette
        self.setStyleSheet(f"""
            QLabel{{ color: {AUBUS_MAROON}; }}
            QPushButton {{ background-color: white; border-radius: 6px; padding: 8px; }}
        """)

        self.setLayout(outer)

    def on_register_clicked(self):
        # Basic validation only
        name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        pw = self.password_input.text()
        pw2 = self.password_confirm.text()

        if not name or not email or not pw or not pw2:
            QMessageBox.warning(self, "Missing fields", "Please fill all fields.")
            return

        if not is_valid_email(email):
            QMessageBox.warning(self, "Invalid email", "Please enter a valid email address.")
            return

        if pw != pw2:
            QMessageBox.warning(self, "Password mismatch", "Passwords do not match.")
            return

        api = self.app_state.get("api")
        if not api:
            QMessageBox.critical(self, "Configuration error", "API client not initialized.")
            return

        try:
            response = api.register(name=name, email=email, username=email, password=pw)
        except ApiClientError as exc:
            QMessageBox.critical(self, "Registration failed", str(exc))
            return

        if response.type != "REGISTER_OK":
            reason = ""
            if response.payload and response.payload.get("reason"):
                reason = f": {response.payload['reason']}"
            QMessageBox.warning(self, "Registration failed", f"Could not register{reason}.")
            return

        # Automatically log the user in after registration so we have the user profile.
        try:
            login_resp = api.login(username=email, password=pw)
        except ApiClientError as exc:
            QMessageBox.warning(self, "Registered", f"Account created, but automatic login failed: {exc}. Please log in manually.")
            return

        if login_resp.type != "LOGIN_OK" or not login_resp.payload:
            QMessageBox.warning(self, "Registered", "Account created, but login failed. Please try signing in manually.")
            return

        user = login_resp.payload
        self.app_state['authenticated'] = True
        self.app_state['user_id'] = user.get("user_id")
        self.app_state['name'] = user.get("name")
        self.app_state['email'] = user.get("email")
        self.app_state['is_driver'] = user.get("is_driver")
        self.app_state['area'] = user.get("area")
        self.app_state['username'] = user.get("username")

        QMessageBox.information(self, "Registered", "Registration succeeded. Redirecting...")
        if self.parent_stack:
            preliminary = self.parent_stack.findChild(QWidget, "PreliminaryPage")
            if preliminary:
                self.parent_stack.setCurrentIndex(self.parent_stack.indexOf(preliminary))

    def reset_form(self):
        """Clear all form inputs."""
        self.name_input.clear()
        self.email_input.clear()
        self.password_input.clear()
        self.password_confirm.clear()
