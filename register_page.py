# register_page.py
# Register page for the AUBus frontend.
# Contains logo, name, email, password, password confirmation, and Register button.
# Basic client-side validation is included (matching passwords, simple email check).

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox # type: ignore
from PyQt5.QtGui import QFont # type: ignore
from logo_widget import get_logo_label, AUBUS_MAROON

class RegisterPage(QWidget):
    def __init__(self, parent_stack=None, app_state=None):
        super().__init__()
        self.setObjectName("RegisterPage")
        self.parent_stack = parent_stack
        self.app_state = app_state or {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # Logo + Title
        layout.addWidget(get_logo_label(size=80))
        title = QLabel("Create an account")
        title.setFont(QFont("Verdana", 16))
        layout.addWidget(title)

        # Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Full name")
        layout.addWidget(self.name_input)

        # Email
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email")
        layout.addWidget(self.email_input)

        # Password
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)

        # Confirm password
        self.password_confirm = QLineEdit()
        self.password_confirm.setPlaceholderText("Confirm password")
        self.password_confirm.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_confirm)

        # Register button
        register_btn = QPushButton("Register")
        register_btn.clicked.connect(self.on_register_clicked)
        layout.addWidget(register_btn)

        # Simple styling that matches maroon palette
        self.setStyleSheet(f"""
            QLabel{{ color: {AUBUS_MAROON}; }}
            QPushButton {{ background-color: white; border-radius: 6px; padding: 8px; }}
        """)

        self.setLayout(layout)

    def on_register_clicked(self):
        # Basic validation only
        name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        pw = self.password_input.text()
        pw2 = self.password_confirm.text()

        if not name or not email or not pw or not pw2:
            QMessageBox.warning(self, "Missing fields", "Please fill all fields.")
            return

        if "@" not in email or "." not in email:
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
