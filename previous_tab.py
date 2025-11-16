from PyQt5.QtCore import Qt # type: ignore
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QDialog,
    QHBoxLayout,
    QPushButton,
    QSpinBox,
    QMessageBox,
)  # type: ignore

from ui_styles import set_title_label, style_button, style_input
from api_client import ApiClientError


class PreviousTab(QWidget):
    def __init__(self, app_state=None):
        super().__init__()
        self.app_state = app_state or {}
        self.rides = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        title = QLabel("Previous Rides")
        set_title_label(title, size=14)
        layout.addWidget(title)

        self.status_label = QLabel("Sign in to see your ride history.")
        layout.addWidget(self.status_label)

        self.list_w = QListWidget()
        self.list_w.itemClicked.connect(self.on_ride_clicked)
        layout.addWidget(self.list_w)
        self.setLayout(layout)

    def refresh_rides(self):
        api = self.app_state.get("api")
        user_id = self.app_state.get("user_id")
        if not api or not user_id:
            self.status_label.setText("Sign in to see your ride history.")
            self.list_w.clear()
            return
        try:
            response = api.fetch_rides(user_id)
        except ApiClientError as exc:
            self.status_label.setText(f"Unable to load rides: {exc}")
            return
        rides = response.get("payload", {}).get("rides", [])
        self.rides = rides
        self.list_w.clear()
        if not rides:
            self.status_label.setText("No rides yet. Book a ride to see it here.")
            return
        self.status_label.setText(f"{len(rides)} ride(s) found.")
        for ride in rides:
            text = self._format_ride_label(ride)
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, ride)
            self.list_w.addItem(item)

    def _format_ride_label(self, ride):
        partner = ride.get("partner_name", "Unknown")
        role = ride.get("role", "passenger")
        status = ride.get("status", "PENDING")
        rating = ride.get("rating")
        rating_txt = f" | Your rating: {rating}/5" if rating else ""
        if ride.get("can_edit_rating"):
            rating_txt += " | Rating editable (36h window)"
        return f"{ride.get('day')} {ride.get('time')} - {ride.get('area')} with {partner} ({role}) [{status}]{rating_txt}"

    def on_ride_clicked(self, item: QListWidgetItem):
        ride = item.data(Qt.UserRole)
        if not ride:
            return
        self.open_rating_dialog(ride)

    def open_rating_dialog(self, ride):
        dlg = QDialog(self)
        dlg.setWindowTitle("Rate your ride companion")
        v = QVBoxLayout()
        v.addWidget(QLabel(self._format_ride_label(ride)))

        can_edit = ride.get("can_edit_rating", False)
        h = QHBoxLayout()
        h.addWidget(QLabel("Rating (1-5):"))
        rating_spin = QSpinBox()
        rating_spin.setMinimum(1)
        rating_spin.setMaximum(5)
        rating_spin.setValue(int(ride.get("rating") or 5))
        rating_spin.setEnabled(can_edit)
        style_input(rating_spin, width=120, min_height=28)
        h.addWidget(rating_spin)
        v.addLayout(h)

        submit = QPushButton("Save rating" if can_edit else "Rating locked")
        submit.setEnabled(can_edit)
        style_button(submit, min_height=28)
        v.addWidget(submit)

        def submit_rating():
            self._submit_rating(ride, rating_spin.value(), dlg)

        submit.clicked.connect(submit_rating)
        dlg.setLayout(v)
        dlg.exec_()

    def _submit_rating(self, ride, value, dialog):
        api = self.app_state.get("api")
        user_id = self.app_state.get("user_id")
        if not api or not user_id:
            QMessageBox.warning(self, "Not signed in", "Please log in again.")
            return
        try:
            response = api.update_rating(ride_id=ride["ride_id"], rater_user_id=user_id, rating=value)
        except ApiClientError as exc:
            QMessageBox.critical(self, "Unable to save rating", str(exc))
            return
        if response.get("type") == "UPDATE_RATING_OK":
            QMessageBox.information(self, "Saved", "Rating updated.")
            dialog.accept()
            self.refresh_rides()
        else:
            reason = ""
            payload = response.get("payload") or {}
            if payload.get("reason"):
                reason = f": {payload['reason']}"
            QMessageBox.warning(self, "Unable to save rating", f"Server rejected the update{reason}.")
