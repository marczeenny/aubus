# preliminary_page.py
# Page that asks user whether they are a driver or passenger.

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout # type: ignore
from PyQt5.QtGui import QFont # type: ignore
from logo_widget import get_logo_label, AUBUS_MAROON

class PreliminaryPage(QWidget):
    def __init__(self, parent_stack=None, app_state=None):
        super().__init__()
        self.setObjectName("PreliminaryPage")
        self.parent_stack = parent_stack
        self.app_state = app_state or {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)

        layout.addWidget(get_logo_label(size=80))

        label = QLabel("Are you driving or looking for a ride?")
        label.setFont(QFont("Verdana", 14))
        layout.addWidget(label)

        row = QHBoxLayout()
        passenger_btn = QPushButton("Passenger")
        passenger_btn.clicked.connect(lambda: self.choose_role("passenger"))
        row.addWidget(passenger_btn)

        driver_btn = QPushButton("Driver")
        driver_btn.clicked.connect(lambda: self.choose_role("driver"))
        row.addWidget(driver_btn)
        layout.addLayout(row)

        self.setStyleSheet(f"QLabel{{ color: {AUBUS_MAROON}; }} QPushButton{{ padding:8px; border-radius:6px; }}")
        self.setLayout(layout)

    def choose_role(self, role):
        self.app_state['role'] = role
        # navigate to main page (index depends on app stacking order)
        if self.parent_stack:
            # assume main page is present and named "MainPage"
            self.parent_stack.setCurrentIndex(self.parent_stack.indexOf(self.parent_stack.findChild(QWidget, "MainPage")))
