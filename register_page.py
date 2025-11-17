# register_page.py
# Register page for the AUBus frontend.
# Contains logo, name, email, password, password confirmation, and Register button.
# Basic client-side validation is included (matching passwords, simple email check).

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QHBoxLayout, QRadioButton, QGridLayout, QComboBox # type: ignore
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

        # Area input (for drivers) - use controlled dropdown to avoid typos
        self.area_input = QComboBox()
        areas = ["-- Select Area --", "Beirut", "Batroun", "Tripoli", "Saida", "Baalbek", "Zahle", "Nabatieh", "Metn"]
        self.area_input.addItems(areas)
        # If app_state already has an area, pre-select it
        current_area = self.app_state.get('area') or "-- Select Area --"
        idx = self.area_input.findText(current_area)
        if idx >= 0:
            self.area_input.setCurrentIndex(idx)
        self.area_input.setVisible(True)
        self.area_input.setFixedWidth(300)
        layout.addWidget(self.area_input, alignment=Qt.AlignCenter)

        # Role selection
        role_layout = QHBoxLayout()
        self.passenger_radio = QRadioButton("Passenger")
        self.driver_radio = QRadioButton("Driver")
        self.passenger_radio.setChecked(True)  # Default to passenger
        role_layout.addWidget(self.passenger_radio)
        role_layout.addWidget(self.driver_radio)
        layout.addLayout(role_layout)


        # Schedule widget (hidden by default)
        self.schedule_widget = self._create_schedule_grid()
        self.schedule_widget.setVisible(False)
        layout.addWidget(self.schedule_widget)

        self.driver_radio.toggled.connect(self.schedule_widget.setVisible)

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

    def _generate_time_slots(self):
        slots = []
        for hour in range(24):
            for minute in range(0, 60, 15):
                slots.append(f"{hour:02d}:{minute:02d}")
        return slots

    def _create_schedule_grid(self):
        schedule_widget = QWidget()
        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)

        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        self.routes = {"To University": "area_to_uni", "From University": "uni_to_area"}
        route_labels = list(self.routes.keys())

        # Header
        grid_layout.addWidget(QLabel("Day"), 0, 0)
        grid_layout.addWidget(QLabel(route_labels[0]), 0, 1)
        grid_layout.addWidget(QLabel(route_labels[1]), 0, 2)

        time_slots = self._generate_time_slots()
        self.schedule_inputs = {}

        for i, day in enumerate(days):
            grid_layout.addWidget(QLabel(day), i + 1, 0)
            for j, route in enumerate(route_labels):
                combo = QComboBox()
                combo.addItems(["-"] + time_slots)
                grid_layout.addWidget(combo, i + 1, j + 1)
                self.schedule_inputs[(day, route)] = combo

        schedule_widget.setLayout(grid_layout)
        return schedule_widget

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

        role = "driver" if self.driver_radio.isChecked() else "passenger"
        area = self.area_input.currentText().strip()
        schedule = None

        if not area or area == "-- Select Area --":
            QMessageBox.warning(self, "Area required", "Please select your area from the list.")
            return

        if role == "driver":
            schedule = {}
            for (day, route), combo in self.schedule_inputs.items():
                time = combo.currentText()
                if time != "-":
                    if day not in schedule:
                        schedule[day] = {}
                    schedule[day][route] = time

        api = self.app_state.get("api")
        if not api:
            QMessageBox.critical(self, "Configuration error", "API client not initialized.")
            return

        try:
            response = api.register(name=name, email=email, username=email, password=pw, role=role, area=area, schedule=schedule)
        except ApiClientError as exc:
            QMessageBox.critical(self, "Registration failed", str(exc))
            return

        if response.get("type") != "REGISTER_OK":
            reason = ""
            payload = response.get("payload") or {}
            if payload.get("reason"):
                reason = f": {payload['reason']}"
            QMessageBox.warning(self, "Registration failed", f"Could not register{reason}.")
            return

        # Automatically log the user in after registration so we have the user profile.
        try:
            login_resp = api.login(username=email, password=pw)
        except ApiClientError as exc:
            QMessageBox.warning(self, "Registered", f"Account created, but automatic login failed: {exc}. Please log in manually.")
            return

        if login_resp.get("type") != "LOGIN_OK" or not login_resp.get("payload"):
            QMessageBox.warning(self, "Registered", "Account created, but login failed. Please try signing in manually.")
            return

        user = login_resp["payload"]
        self.app_state['authenticated'] = True
        self.app_state['user_id'] = user.get("user_id")
        self.app_state['name'] = user.get("name")
        self.app_state['email'] = user.get("email")
        self.app_state['is_driver'] = user.get("is_driver")
        self.app_state['area'] = user.get("area")
        self.app_state['username'] = user.get("username")
        self.app_state['role_selected'] = user.get("role_selected", False)
        self.app_state['role'] = "driver" if user.get("is_driver") else "passenger"

        QMessageBox.information(self, "Registered", "Registration succeeded. Redirecting...")
        if self.parent_stack:
            if self.app_state['role_selected']:
                main_page = self.parent_stack.findChild(QWidget, "MainPage")
                if main_page:
                    self.parent_stack.setCurrentIndex(self.parent_stack.indexOf(main_page))
            else:
                preliminary = self.parent_stack.findChild(QWidget, "PreliminaryPage")
                if preliminary:
                    self.parent_stack.setCurrentIndex(self.parent_stack.indexOf(preliminary))

    def reset_form(self):
        """Clear all form inputs."""
        self.name_input.clear()
        self.email_input.clear()
        self.password_input.clear()
        self.password_confirm.clear()
        # reset area combo
        try:
            self.area_input.setCurrentIndex(0)
        except Exception:
            pass
