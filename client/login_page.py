# login_page.py
# Login page for the AUBus frontend.
# Contains logo, email textbox, password textbox (hidden), Login button,
# and a "Don't have an account? Register here:" with Register button.

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QHBoxLayout # type: ignore
from PyQt5.QtGui import QFont # type: ignore
from PyQt5.QtCore import Qt # type: ignore
from .logo_widget import get_logo_label, AUBUS_MAROON
from .ui_styles import style_button, set_title_label, style_input
from .validators import is_valid_email
from .api_client import ApiClientError

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
        outer = QVBoxLayout()
        outer.addStretch()

        # Center content with horizontal padding
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignCenter)

        # logo
        logo = get_logo_label(size=96)
        logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo)

        # title
        title = QLabel("Login")
        set_title_label(title, size=18)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # email
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email")
        style_input(self.email_input)
        layout.addWidget(self.email_input, alignment=Qt.AlignCenter)

        # password (hidden)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)  # hides typed text
        style_input(self.password_input)
        layout.addWidget(self.password_input, alignment=Qt.AlignCenter)

        # login button
        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.on_login_clicked)
        style_button(login_btn)
        layout.addWidget(login_btn, alignment=Qt.AlignCenter)

        # register redirect
        row = QHBoxLayout()
        row.setAlignment(Qt.AlignCenter)
        hint = QLabel("Don't have an account? Register here:")
        row.addWidget(hint)
        reg_btn = QPushButton("Register")
        reg_btn.clicked.connect(self.go_to_register)
        style_button(reg_btn)
        row.addWidget(reg_btn)
        layout.addLayout(row)

        # Wrap centered layout with horizontal padding
        h_layout = QHBoxLayout()
        h_layout.addStretch()
        h_layout.addLayout(layout)
        h_layout.addStretch()

        outer.addLayout(h_layout)
        outer.addStretch()

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

        self.setLayout(outer)

    def on_login_clicked(self):
        email = self.email_input.text().strip()
        password = self.password_input.text()
        if not email or not password:
            QMessageBox.warning(self, "Missing fields", "Please enter both email and password.")
            return
        # Basic email format validation (regex-based)
        if not is_valid_email(email):
            QMessageBox.warning(self, "Invalid email", "Please enter a valid email address.")
            return

        api = self.app_state.get("api")
        if not api:
            QMessageBox.critical(self, "Configuration error", "API client not initialized.")
            return

        try:
            response = api.login(username=email, password=password)
        except ApiClientError as exc:
            QMessageBox.critical(self, "Login failed", str(exc))
            return

        if response.get("type") != "LOGIN_OK" or not response.get("payload"):
            QMessageBox.warning(self, "Login failed", "Invalid username or password.")
            return

        user = response["payload"]
        self.app_state['authenticated'] = True
        self.app_state['user_id'] = user.get("user_id")
        self.app_state['name'] = user.get("name")
        self.app_state['email'] = user.get("email")
        self.app_state['is_driver'] = user.get("is_driver")
        self.app_state['area'] = user.get("area")
        self.app_state['username'] = user.get("username")
        self.app_state['role_selected'] = user.get("role_selected", False)
        self.app_state['role'] = "driver" if user.get("is_driver") else "passenger"

        # Announce our peer listening port (if peer server was started)
        api = self.app_state.get('api')
        peer_port = self.app_state.get('peer_port')
        if api and peer_port:
            try:
                resp = api.announce_peer(peer_port)
                try:
                    print(f"[LoginPage] announce_peer response: {resp}")
                except Exception:
                    pass
            except Exception:
                pass
        if self.parent_stack:
            if self.app_state['role_selected']:
                main_page = self.parent_stack.findChild(QWidget, "MainPage")
                if main_page:
                    self.parent_stack.setCurrentIndex(self.parent_stack.indexOf(main_page))
                else:
                    QMessageBox.warning(self, "Navigation error", "Main page not found.")
            else:
                preliminary = self.parent_stack.findChild(QWidget, "PreliminaryPage")
                if preliminary:
                    self.parent_stack.setCurrentIndex(self.parent_stack.indexOf(preliminary))

    def go_to_register(self):
        if self.parent_stack:
            self.parent_stack.setCurrentIndex(self.parent_stack.indexOf(self.parent_stack.findChild(QWidget, "RegisterPage")))

    def reset_form(self):
        """Clear email and password inputs."""
        self.email_input.clear()
        self.password_input.clear()
