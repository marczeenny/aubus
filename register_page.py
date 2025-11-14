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

        # TODO: Connect to backend to create user and check uniqueness:
        # send_json(conn, {"type":"REGISTER", "payload": {"name": name, "email": email, "password": pw, ...}})
        # For now, pretend registration is successful and redirect to preliminary page.
        self.app_state['email'] = email
        self.app_state['name'] = name
        self.app_state['authenticated'] = True

        QMessageBox.information(self, "Registered", "Registration succeeded (demo). Redirecting...")
        if self.parent_stack:
            self.parent_stack.setCurrentIndex(self.parent_stack.indexOf(self.parent_stack.findChild(QWidget, "PreliminaryPage")))

    def reset_form(self):
        """Clear all form inputs."""
        self.name_input.clear()
        self.email_input.clear()
        self.password_input.clear()
        self.password_confirm.clear()
