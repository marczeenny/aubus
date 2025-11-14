# previous_tab.py
# Contains a list of previous rides. Clicking on a ride opens a small rating UI.

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, QDialog, QHBoxLayout, QPushButton, QSpinBox # type: ignore
from PyQt5.QtGui import QFont # type: ignore
from logo_widget import AUBUS_MAROON
from ui_styles import set_title_label, style_button

class PreviousTab(QWidget):
    def __init__(self, app_state=None):
        super().__init__()
        self.app_state = app_state or {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        title = QLabel("Previous Rides")
        set_title_label(title, size=14)
        layout.addWidget(title)

        self.list_w = QListWidget()
        # demo data
        for i in range(1, 6):
            item = QListWidgetItem(f"Ride #{i} — with User{i} — {i+7}:00 — area: Ras Beirut")
            self.list_w.addItem(item)

        self.list_w.itemClicked.connect(self.on_ride_clicked)
        layout.addWidget(self.list_w)
        self.setLayout(layout)

    def on_ride_clicked(self, item: QListWidgetItem):
        # Open a simple modal to rate user(s)
        dlg = QDialog(self)
        dlg.setWindowTitle("Rate your ride companion(s)")
        v = QVBoxLayout()
        v.addWidget(QLabel(item.text()))

        # for demo, use a single spinbox 1-5
        h = QHBoxLayout()
        h.addWidget(QLabel("Rating (1-5):"))
        rating = QSpinBox()
        rating.setMinimum(1)
        rating.setMaximum(5)
        rating.setValue(5)
        from ui_styles import style_input
        style_input(rating, width=120, min_height=28)
        h.addWidget(rating)
        v.addLayout(h)

        # submit
        submit = QPushButton("Submit Rating")
        def submit_rating():
            # TODO: call backend ADD_RATING here
            # e.g., send_json(conn, {"type":"ADD_RATING", "payload": {...}})
            dlg.accept()
        submit.clicked.connect(submit_rating)
        style_button(submit, min_height=28)
        v.addWidget(submit)

        dlg.setLayout(v)
        dlg.exec_()
