# login_page.py
# Login page for the AUBus frontend.
# Contains logo, email textbox, password textbox (hidden), Login button,
# and a "Don't have an account? Register here:" with Register button.

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QHBoxLayout # type: ignore
from PyQt5.QtGui import QFont # type: ignore
from logo_widget import get_logo_label, AUBUS_MAROON

class LoginPage(QWidget):
    def __init__(self, parent_stack=None, app_state=None):
        """
        parent_stack: a QStackedWidget that this page can use to change pages
        app_state: dictionary for shared state across pages (e.g., user info)
        """
        super().__init__()
        self.parent_stack = parent_stack
        self.app_state = app_state or {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)

        # logo
        layout.addWidget(get_logo_label(size=96))

        # title
        title = QLabel("Login")
        title.setFont(QFont("Verdana", 18))
        layout.addWidget(title)

        # email
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email")
        layout.addWidget(self.email_input)

        # password (hidden)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)  # hides typed text
        layout.addWidget(self.password_input)

        # login button
        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.on_login_clicked)
        layout.addWidget(login_btn)

        # register redirect
        row = QHBoxLayout()
        hint = QLabel("Don't have an account? Register here:")
        row.addWidget(hint)
        reg_btn = QPushButton("Register")
        reg_btn.clicked.connect(self.go_to_register)
        row.addWidget(reg_btn)
        layout.addLayout(row)

        # minor styling
        self.setStyleSheet(f"""
            QWidget {{
                font-family: Verdana;
            }}
            QPushButton {{
                background-color: white;
                border-radius: 6px;
                padding: 8px;
            }}
            QLabel{{ color: {AUBUS_MAROON}; }}
        """)

        self.setLayout(layout)

    def on_login_clicked(self):
        # NOTE: currently not connected to backend.
        email = self.email_input.text().strip()
        password = self.password_input.text()
        if not email or not password:
            QMessageBox.warning(self, "Missing fields", "Please enter both email and password.")
            return

        # TODO: replace with backend authentication call (send_json / socket).
        # For now, store email in app_state and go to preliminary page.
        self.app_state['email'] = email
        # mark user temporarily as authenticated
        self.app_state['authenticated'] = True
        # go to preliminary page (index must match app setup)
        if self.parent_stack:
            # index 2 is typically PreliminaryPage in app.py - ensure consistency
            self.parent_stack.setCurrentIndex(self.parent_stack.indexOf(self.parent_stack.findChild(QWidget, "PreliminaryPage")))

    def go_to_register(self):
        if self.parent_stack:
            self.parent_stack.setCurrentIndex(self.parent_stack.indexOf(self.parent_stack.findChild(QWidget, "RegisterPage")))
