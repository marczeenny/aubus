"""Ride tab and driver/passenger UI.

Contains ride search, driver results, and passenger/driver actions used by
the main hub. Handles creating ride requests and accepting offers.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QSpinBox,
                             QPushButton, QListWidget, QListWidgetItem, QHBoxLayout, QMessageBox, QRadioButton, QComboBox, QDialog, QListView)  # type: ignore
from PyQt5.QtCore import Qt  # type: ignore
from datetime import datetime
from .ui_styles import style_button, set_title_label, style_input
from .api_client import ApiClientError


class RideTab(QWidget):
    def __init__(self, app_state=None, go_to_progress=None):
        """
        app_state: shared state dict
        go_to_progress: callable (ride_info) -> shows progress page
        """
        super().__init__()
        self.app_state = app_state or {}
        self.go_to_progress = go_to_progress
        self.driver_results = []
        self.pending_passenger_requests = {}
        self.pending_driver_requests = {}
        self.init_ui()

    def init_ui(self):
        self.setLayout(QVBoxLayout())

    def showEvent(self, event):
        super().showEvent(event)
        self.update_ui_for_role()

    def update_ui_for_role(self):
        # Clear existing widgets
        layout = self.layout()
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        role = self.current_role()
        if role == 'passenger':
            self.setup_passenger_ui(layout)
        else:
            self.setup_driver_ui(layout)

    def setup_passenger_ui(self, layout):
        title = QLabel("Request a Ride")
        set_title_label(title, size=14)
        layout.addWidget(title)

        self.from_uni_radio = QRadioButton("From University to My Area")
        self.from_area_radio = QRadioButton("From My Area to University")
        self.from_uni_radio.setChecked(True)
        layout.addWidget(self.from_uni_radio)
        layout.addWidget(self.from_area_radio)



        # Desired time removed — requests will use current time

        self.request_btn = QPushButton("Request Ride")
        self.request_btn.clicked.connect(self.on_request_ride_clicked)
        style_button(self.request_btn)
        layout.addWidget(self.request_btn)

        # Ensure passenger cannot request a new ride while they have an active one
        self.update_request_button_state()

        self.status_label = QLabel("Waiting for a driver to accept...")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

    def setup_driver_ui(self, layout):
        title = QLabel("Incoming Ride Requests")
        set_title_label(title, size=14)
        layout.addWidget(title)

        self.requests_list = QListWidget()
        layout.addWidget(self.requests_list)

        btn_row = QHBoxLayout()
        accept_btn = QPushButton("Accept")
        accept_btn.clicked.connect(self.on_accept_clicked)
        style_button(accept_btn, min_height=30)
        btn_row.addWidget(accept_btn)
        # 'Open' removed — drivers should use the 'Current Ride' tab
        deny_btn = QPushButton("Deny")
        deny_btn.clicked.connect(self.on_deny_clicked)
        style_button(deny_btn, min_height=30)
        btn_row.addWidget(deny_btn)
        layout.addLayout(btn_row)

        self.refresh_driver_requests()


    def current_role(self):
        return self.app_state.get('role', 'passenger')

    def on_request_ride_clicked(self):
        direction = "To University" if self.from_area_radio.isChecked() else "From University"
        now = datetime.now()
        day = now.strftime("%A")
        time = now.strftime("%H:%M")

        api = self.app_state.get("api")
        user_id = self.app_state.get("user_id")
        area = self.app_state.get("area") # Retrieve passenger's area
        if not api or not user_id or not area: # Check if area is available
            QMessageBox.warning(self, "Not ready", "Please log in again or ensure your area is set.")
            return

        try:
            response = api.broadcast_ride_request(passenger_id=user_id, direction=direction, day=day, time=time, area=area) # Pass area to API call
        except ApiClientError as exc:
            QMessageBox.critical(self, "Request failed", str(exc))
            return
        
        if response.get("type") == "BROADCAST_OK":
            self.status_label.setText("Request sent to available drivers. Waiting for responses...")
            self.status_label.setVisible(True)
            # Disable further requests while waiting for responses
            if hasattr(self, 'request_btn'):
                self.request_btn.setEnabled(False)
        elif response.get("type") == "NO_DRIVERS_FOUND":
            QMessageBox.information(self, "No drivers", "No available drivers found for the next 15 minutes.")
            # Allow the passenger to try again immediately
            if hasattr(self, 'request_btn'):
                self.request_btn.setEnabled(True)
            # make sure state reflects current server-side rides
            self.update_request_button_state()


    def on_accept_clicked(self):
        item = self.requests_list.currentItem()
        if not item:
            QMessageBox.information(self, "Select one", "Please select a request to accept.")
            return
        
        ride = item.data(Qt.UserRole)
        if not ride:
            return

        api = self.app_state.get("api")
        driver_id = self.app_state.get("user_id")
        if not api or not driver_id:
            QMessageBox.warning(self, "Not ready", "Please log in again.")
            return

        try:
            response = api.respond_to_ride(ride["ride_id"], "ACCEPTED")
        except ApiClientError as exc:
            QMessageBox.critical(self, "Unable to respond", str(exc))
            return

        if response.get("payload", {}).get("status") == "ACCEPTED":
            QMessageBox.information(self, "Ride Accepted", "You have accepted the ride.")
        else:
            QMessageBox.information(self, "Ride Closed", "This ride is no longer available.")

        # Refresh the driver requests list
        self.refresh_driver_requests()
        # Also refresh the Current Rides tab if the main page exposes it
        main_page = self.app_state.get("main_page")
        if main_page and hasattr(main_page, 'current_rides_tab'):
            try:
                # Refresh immediately and again after a short delay to allow the server to finish updates
                main_page.current_rides_tab.refresh_list()
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(350, lambda: main_page.current_rides_tab.refresh_list())
            except Exception:
                pass

    def on_open_clicked(self):
        # Open the driver's ride management dialog (shows accumulated accepted passengers)
        api = self.app_state.get("api")
        driver_id = self.app_state.get("user_id")
        if not api or not driver_id:
            QMessageBox.warning(self, "Not ready", "Please log in again.")
            return
        try:
            resp = api.fetch_rides(driver_id)
        except ApiClientError:
            QMessageBox.warning(self, "Unable to open", "Could not load your rides.")
            return
        rides = resp.get("payload", {}).get("rides", [])
        # Filter to rides where this user is driver and status is ACCEPTED or STARTED
        driver_rides = [r for r in rides if r.get("role") == "driver" and r.get("status") in ("ACCEPTED", "STARTED")]
        dlg = DriverRideMenu(self, api, driver_rides, go_to_progress=self.go_to_progress)
        dlg.exec_()

    def on_deny_clicked(self):
        item = self.requests_list.currentItem()
        if not item:
            QMessageBox.information(self, "Select one", "Please select a request to deny.")
            return

        ride = item.data(Qt.UserRole)
        if not ride:
            return
            
        api = self.app_state.get("api")
        driver_id = self.app_state.get("user_id")
        if not api or not driver_id:
            QMessageBox.warning(self, "Not ready", "Please log in again.")
            return

        try:
            api.respond_to_ride(ride["ride_id"], "DENIED")
        except ApiClientError as exc:
            QMessageBox.critical(self, "Unable to deny", str(exc))
        
        self.refresh_driver_requests()

    def refresh_driver_requests(self):
        if self.current_role() != 'driver':
            return
        api = self.app_state.get("api")
        user_id = self.app_state.get("user_id")
        if not api or not user_id:
            return
        try:
            response = api.fetch_ride_requests(user_id)
        except ApiClientError:
            return
        
        requests = response.get("payload", {}).get("requests", [])
        self.requests_list.clear()
        for req in requests:
            item = QListWidgetItem(f"Passenger: {req['passenger_name']} - {req['direction']} at {req['time']}")
            item.setData(Qt.UserRole, req)
            self.requests_list.addItem(item)


    def handle_event(self, event):
        role = self.current_role()
        if role == "driver":
            if event.type == "RIDE_REQUEST":
                self.refresh_driver_requests()
            elif event.type == "RIDE_UNAVAILABLE":
                ride_id = event.payload.get("ride_id")
                for i in range(self.requests_list.count()):
                    item = self.requests_list.item(i)
                    ride = item.data(Qt.UserRole)
                    if ride and ride["ride_id"] == ride_id:
                        self.requests_list.takeItem(i)
                        break
        elif role == "passenger":
            if event.type == "DRIVER_RESPONSE":
                payload = event.payload
                status = payload.get("status")
                if status == "ACCEPTED":
                    QMessageBox.information(self, "Ride update", "Driver accepted the request.")
                    # Hide waiting label and open progress page for passenger
                    if hasattr(self, 'status_label'):
                        self.status_label.setVisible(False)
                    # Fetch ride info and show progress
                    ride_id = payload.get("ride_id")
                    api = self.app_state.get("api")
                    user_id = self.app_state.get("user_id")
                    if api and user_id and ride_id:
                        try:
                            resp = api.fetch_rides(user_id)
                            rides = resp.get("payload", {}).get("rides", [])
                            for r in rides:
                                if r.get("ride_id") == ride_id:
                                    # Attach peer connection info from the driver response (if provided)
                                    r["driver_ip"] = payload.get("driver_ip")
                                    r["driver_port"] = payload.get("driver_port")
                                    r["partner_username"] = payload.get("driver_username")
                                    if self.go_to_progress:
                                        r["role"] = "passenger"
                                        self.go_to_progress(r)
                                    break
                        except ApiClientError:
                            pass
                elif status == "DENIED":
                    QMessageBox.information(self, "Ride update", "Driver denied the request.")
                    # Allow the passenger to make another request
                    if hasattr(self, 'status_label'):
                        self.status_label.setVisible(False)
                    self.update_request_button_state()



    def reset_form(self):
        """Clear form and matches list."""
        # Clearing widgets may be called when the UI was previously torn down;
        # guard against deleted C/C++ wrapped objects by catching runtime errors.
        if hasattr(self, 'matches_list'):
            try:
                self.matches_list.clear()
            except Exception:
                pass
        if hasattr(self, 'requests_list'):
            try:
                self.requests_list.clear()
            except Exception:
                pass
        try:
            if getattr(self, 'from_uni_radio', None) is not None:
                try:
                    self.from_uni_radio.setChecked(True)
                except Exception:
                    # widget may have been deleted by UI teardown
                    pass
        except Exception:
            pass
        self.driver_results = []

    def update_request_button_state(self):
        """Disable the request button if the passenger has any non-completed ride."""
        api = self.app_state.get("api")
        user_id = self.app_state.get("user_id")
        if not hasattr(self, 'request_btn') or not api or not user_id:
            return
        try:
            resp = api.fetch_rides(user_id)
        except ApiClientError:
            # conservatively allow requests if we cannot fetch rides
            self.request_btn.setEnabled(True)
            return
        rides = resp.get("payload", {}).get("rides", [])
        # Consider only truly active statuses that should block new requests.
        # CANCELLED or COMPLETED should allow the user to request again.
        active_statuses = {"PENDING", "ACCEPTED", "STARTED"}
        active = any(r.get("status") in active_statuses for r in rides)
        self.request_btn.setEnabled(not active)


class DriverRideMenu(QDialog):
    """Dialog that shows rides the driver has accepted (accumulated passengers)."""
    def __init__(self, parent, api, rides, go_to_progress=None):
        super().__init__(parent)
        self.api = api
        self.rides = rides or []
        self.go_to_progress = go_to_progress
        self.setWindowTitle("Your Accepted Passengers")
        self.resize(500, 300)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.list = QListWidget()
        layout.addWidget(self.list)
        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("Start Selected")
        self.start_btn.clicked.connect(self.on_start)
        style_button(self.start_btn)
        btn_row.addWidget(self.start_btn)
        # Open removed from driver dialog; main page handles progress
        self.remove_btn = QPushButton("Remove/Cancel Selected")
        self.remove_btn.clicked.connect(self.on_remove)
        style_button(self.remove_btn)
        btn_row.addWidget(self.remove_btn)
        layout.addLayout(btn_row)
        self.setLayout(layout)
        self.refresh_list()

    def refresh_list(self):
        self.list.clear()
        for r in self.rides:
            item = QListWidgetItem(f"{r.get('partner_name') or 'Passenger'} - {r.get('day')} {r.get('time')} - {r.get('status')}")
            item.setData(Qt.UserRole, r)
            self.list.addItem(item)

    def selected_ride(self):
        item = self.list.currentItem()
        if not item:
            QMessageBox.information(self, "Select one", "Please select a ride.")
            return None
        return item.data(Qt.UserRole)

    def on_start(self):
        r = self.selected_ride()
        if not r:
            return
        ride_id = r.get('ride_id')
        try:
            self.api.start_ride(ride_id)
        except ApiClientError as exc:
            QMessageBox.critical(self, "Unable to start", str(exc))
            return
        QMessageBox.information(self, "Started", "Ride started for selected passenger.")
        # open progress for this ride
        if self.go_to_progress:
            r['role'] = 'driver'
            self.go_to_progress(r)
        # update local list
        r['status'] = 'STARTED'
        self.refresh_list()

    def on_open(self):
        r = self.selected_ride()
        if not r:
            return
        if self.go_to_progress:
            r['role'] = 'driver'
            self.go_to_progress(r)

    def on_remove(self):
        r = self.selected_ride()
        if not r:
            return
        ride_id = r.get('ride_id')
        try:
            resp = self.api.cancel_ride(ride_id)
        except ApiClientError as exc:
            QMessageBox.critical(self, "Unable to cancel", str(exc))
            return
        if resp.get('type') == 'CANCEL_RIDE_OK':
            QMessageBox.information(self, "Removed", "Passenger removed / ride cancelled.")
            # remove from list
            self.rides = [x for x in self.rides if x.get('ride_id') != ride_id]
            self.refresh_list()
        else:
            QMessageBox.warning(self, "Unable", resp.get('payload', {}).get('reason', 'Unknown'))


class CurrentRidesTab(QWidget):
    """A tab showing the driver's current accepted rides (multiple passengers).
    Provides Start, Open, and Cancel actions for selected rides.
    """
    def __init__(self, app_state=None, go_to_progress=None):
        super().__init__()
        self.app_state = app_state or {}
        self.go_to_progress = go_to_progress
        self.init_ui()

    def init_ui(self):
        self.setLayout(QVBoxLayout())
        title = QLabel("Current Rides (Accepted)")
        set_title_label(title, size=14)
        self.layout().addWidget(title)

        self.rides_list = QListWidget()
        self.layout().addWidget(self.rides_list)

        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("Start All")
        self.start_btn.clicked.connect(self.on_start_all)
        style_button(self.start_btn)
        btn_row.addWidget(self.start_btn)
        # removed 'Open' — menu functions are on the main ProgressPage
        self.end_btn = QPushButton("End All")
        self.end_btn.clicked.connect(self.on_end_all)
        style_button(self.end_btn)
        btn_row.addWidget(self.end_btn)
        self.cancel_btn = QPushButton("Cancel Selected")
        self.cancel_btn.clicked.connect(self.on_cancel)
        style_button(self.cancel_btn)
        btn_row.addWidget(self.cancel_btn)
        self.layout().addLayout(btn_row)

    def refresh_list(self):
        api = self.app_state.get('api')
        user_id = self.app_state.get('user_id')
        if not api or not user_id:
            return
        try:
            resp = api.fetch_rides(user_id)
        except ApiClientError:
            return
        rides = resp.get('payload', {}).get('rides', [])
        # show only ACCEPTED rides here (once started they'll be removed from this list)
        driver_rides = [r for r in rides if r.get('role') == 'driver' and r.get('status') == 'ACCEPTED']
        self.rides_list.clear()
        for r in driver_rides:
            item = QListWidgetItem(f"{r.get('partner_name') or 'Passenger'} - {r.get('day')} {r.get('time')} - {r.get('status')}")
            item.setData(Qt.UserRole, r)
            self.rides_list.addItem(item)

    def selected_ride(self):
        item = self.rides_list.currentItem()
        if not item:
            QMessageBox.information(self, "Select one", "Please select a ride.")
            return None
        return item.data(Qt.UserRole)

    def on_start(self):
        # Deprecated: use on_start_all for batch start
        self.on_start_all()

    def on_open(self):
        r = self.selected_ride()
        if not r:
            return
        if self.go_to_progress:
            r['role'] = 'driver'
            self.go_to_progress(r)

    def on_cancel(self):
        r = self.selected_ride()
        if not r:
            return
        api = self.app_state.get('api')
        ride_id = r.get('ride_id')
        try:
            resp = api.cancel_ride(ride_id)
        except ApiClientError as exc:
            QMessageBox.critical(self, "Unable to cancel", str(exc))
            return
        if resp.get('type') == 'CANCEL_RIDE_OK':
            QMessageBox.information(self, "Cancelled", "Ride cancelled for that passenger.")
            self.refresh_list()
        else:
            QMessageBox.warning(self, "Unable", resp.get('payload', {}).get('reason', 'Unknown'))

    def on_start_all(self):
        """Start all accepted rides for this driver (batch start)."""
        api = self.app_state.get('api')
        user_id = self.app_state.get('user_id')
        if not api or not user_id:
            QMessageBox.warning(self, "Not ready", "Please log in again.")
            return
        try:
            resp = api.fetch_rides(user_id)
        except ApiClientError:
            QMessageBox.critical(self, "Unable", "Could not fetch rides")
            return
        rides = resp.get('payload', {}).get('rides', [])
        driver_rides = [r for r in rides if r.get('role') == 'driver' and r.get('status') == 'ACCEPTED']
        if not driver_rides:
            QMessageBox.information(self, "No rides", "No accepted rides to start.")
            return
        errors = []
        for r in driver_rides:
            ride_id = r.get('ride_id')
            try:
                api.start_ride(ride_id)
            except ApiClientError as exc:
                errors.append(str(exc))
        if errors:
            QMessageBox.warning(self, "Partial start", "Some rides could not be started: " + ", ".join(errors))
        else:
            QMessageBox.information(self, "Started", "All accepted rides marked as started.")
        # open progress for the first started ride
        first = driver_rides[0]
        if self.go_to_progress:
            first['role'] = 'driver'
            self.go_to_progress(first)
        self.refresh_list()

    def on_end_all(self):
        """Complete all started rides for this driver."""
        api = self.app_state.get('api')
        user_id = self.app_state.get('user_id')
        if not api or not user_id:
            QMessageBox.warning(self, "Not ready", "Please log in again.")
            return
        try:
            resp = api.fetch_rides(user_id)
        except ApiClientError:
            QMessageBox.critical(self, "Unable", "Could not fetch rides")
            return
        rides = resp.get('payload', {}).get('rides', [])
        driver_rides = [r for r in rides if r.get('role') == 'driver' and r.get('status') == 'STARTED']
        if not driver_rides:
            QMessageBox.information(self, "No rides", "No started rides to end.")
            return
        errors = []
        for r in driver_rides:
            ride_id = r.get('ride_id')
            try:
                api.complete_ride(ride_id)
            except ApiClientError as exc:
                errors.append(str(exc))
        if errors:
            QMessageBox.warning(self, "Partial complete", "Some rides could not be completed: " + ", ".join(errors))
        else:
            QMessageBox.information(self, "Completed", "All started rides marked as completed.")
        self.refresh_list()
