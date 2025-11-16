from PyQt5.QtCore import Qt # type: ignore
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QHBoxLayout,
    QMessageBox,
    QListWidgetItem,
)  # type: ignore

from ui_styles import set_title_label, style_button, style_input
from api_client import ApiClientError


class MessagesTab(QWidget):
    def __init__(self, app_state=None):
        super().__init__()
        self.app_state = app_state or {}
        self.contacts_data = []
        self.username_lookup = {}
        self.unread_contacts = set()
        self.current_contact = None
        self.active_ride_contact = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        title = QLabel("Messages")
        set_title_label(title, size=14)
        layout.addWidget(title)

        self.status_label = QLabel("Select a contact to chat.")
        layout.addWidget(self.status_label)

        container = QHBoxLayout()
        self.contacts = QListWidget()
        self.contacts.currentItemChanged.connect(self.on_contact_selected)
        container.addWidget(self.contacts, 1)

        right = QVBoxLayout()
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        right.addWidget(self.chat_history, 4)

        row = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type a message...")
        style_input(self.message_input, width=340)
        row.addWidget(self.message_input)
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send_message)
        style_button(send_btn, min_height=30)
        row.addWidget(send_btn)
        right.addLayout(row)
        container.addLayout(right, 3)

        layout.addLayout(container)
        self.setLayout(layout)

    def refresh_contacts(self, preserve_selection=True):
        api = self.app_state.get("api")
        user_id = self.app_state.get("user_id")
        if not api or not user_id:
            self.status_label.setText("Sign in to chat with your rides.")
            self.contacts.clear()
            self.contacts_data = []
            self.username_lookup = {}
            self.current_contact = None
            return
        current_username = self.current_contact["username"] if self.current_contact and preserve_selection else None
        try:
            response = api.list_contacts(user_id)
        except ApiClientError as exc:
            self.status_label.setText(f"Unable to load contacts: {exc}")
            return
        contacts = response.get("payload", {}).get("contacts", [])
        if self.active_ride_contact:
            username = self.active_ride_contact.get("username")
            if username:
                existing = next((c for c in contacts if c.get("username") == username), None)
                if existing:
                    existing.update(self.active_ride_contact)
                    self.active_ride_contact = existing
                else:
                    contacts.append(dict(self.active_ride_contact))
                    self.active_ride_contact = contacts[-1]
        else:
            self.active_ride_contact = None
        self.contacts_data = contacts
        self.username_lookup = {c["username"]: c for c in contacts if c.get("username")}
        self.contacts.clear()
        for contact in contacts:
            self._add_contact_item(contact)
        if not contacts:
            self.status_label.setText("No contacts yet. Complete a ride with someone to unlock chat.")
            self.chat_history.clear()
        elif current_username and current_username in self.username_lookup:
            self._select_contact_by_username(current_username)

    def _add_contact_item(self, contact):
        label = self._contact_label(contact)
        item = QListWidgetItem(label)
        item.setData(Qt.UserRole, contact)
        self.contacts.addItem(item)

    def _contact_label(self, contact):
        label = f"{contact.get('name')} ({contact.get('username')})"
        if contact.get("username") in self.unread_contacts:
            label += " (new)"
        return label

    def _select_contact_by_username(self, username):
        for row in range(self.contacts.count()):
            item = self.contacts.item(row)
            contact = item.data(Qt.UserRole)
            if contact and contact.get("username") == username:
                self.contacts.setCurrentItem(item)
                break

    def on_contact_selected(self, cur, prev):
        if not cur:
            self.chat_history.clear()
            self.current_contact = None
            return
        contact = cur.data(Qt.UserRole)
        if not contact:
            return
        self.current_contact = contact
        self.unread_contacts.discard(contact["username"])
        cur.setText(self._contact_label(contact))
        self.load_conversation(contact)

    def load_conversation(self, contact):
        api = self.app_state.get("api")
        user_id = self.app_state.get("user_id")
        partner_id = contact.get("id")
        if not api or not user_id or not partner_id:
            return
        try:
            response = api.fetch_messages(user_id, partner_id)
        except ApiClientError as exc:
            self.chat_history.setText(f"Unable to load messages: {exc}")
            return
        messages = response.get("payload", {}).get("messages", [])
        self.chat_history.clear()
        for msg in messages:
            self._append_message(contact, msg)

    def send_message(self):
        if not self.current_contact:
            QMessageBox.information(self, "Select contact", "Choose someone to chat with.")
            return
        text = self.message_input.text().strip()
        if not text:
            return
        api = self.app_state.get("api")
        if not api:
            QMessageBox.warning(self, "Not ready", "Please log in again.")
            return
        try:
            response = api.send_message(self.current_contact["username"], text)
        except ApiClientError as exc:
            QMessageBox.critical(self, "Unable to send", str(exc))
            return
        if response.get("type") == "SEND_MESSAGE_OK":
            payload = {
                "sender_id": self.app_state.get("user_id"),
                "receiver_id": self.current_contact["id"],
                "body": text,
                "sent_at": response.get("payload", {}).get("sent_at", "")
            }
            self._append_message(self.current_contact, payload)
            self.message_input.clear()
        else:
            reason = response.get("payload", {}).get("reason", "")
            QMessageBox.warning(self, "Unable to send", f"Server rejected the message: {reason}")

    def _append_message(self, contact, message_entry):
        user_id = self.app_state.get("user_id")
        sender_id = message_entry.get("sender_id")
        sent_at = message_entry.get("sent_at", "")
        prefix = "You" if sender_id == user_id else contact.get("name") or contact.get("username")
        line = f"[{sent_at}] {prefix}: {message_entry.get('body')}"
        self.chat_history.append(line)

    def handle_event(self, event):
        if event.type == "CHAT_MESSAGE":
            payload = event.payload
            username = payload.get("from")
            if not username:
                return
            contact = self._ensure_contact(username)
            if not contact:
                return
            entry = {
                "sender_id": payload.get("from_id"),
                "receiver_id": payload.get("to_id"),
                "body": payload.get("message"),
                "sent_at": payload.get("sent_at", "")
            }
            if self.current_contact and self.current_contact.get("username") == username:
                self._append_message(contact, entry)
            else:
                self.unread_contacts.add(username)
                self.refresh_contacts()
        elif event.type == "CONTACTS":
            self.refresh_contacts()
        elif event.type == "MESSAGES" and self.current_contact:
            self.load_conversation(self.current_contact)
        elif event.type == "CONNECTION_LOST":
            self.status_label.setText("Connection lost. Messages may be delayed.")

    def _ensure_contact(self, username):
        contact = self.username_lookup.get(username)
        if contact:
            return contact
        if self.active_ride_contact and self.active_ride_contact.get("username") == username:
            return self.active_ride_contact
        self.refresh_contacts(preserve_selection=True)
        return self.username_lookup.get(username)

    def set_active_ride(self, ride_info):
        contact = None
        if ride_info:
            partner_id = ride_info.get("partner_id")
            username = ride_info.get("partner_username")
            name = ride_info.get("partner_name") or username
            if partner_id and username:
                contact = {"id": partner_id, "username": username, "name": name}
        if contact != self.active_ride_contact:
            self.active_ride_contact = contact
            self.refresh_contacts(preserve_selection=True)
        if contact and self.current_contact and self.current_contact.get("username") == contact["username"]:
            self.load_conversation(self.current_contact)

    def clear_active_ride(self):
        if self.active_ride_contact:
            self.active_ride_contact = None
            self.refresh_contacts(preserve_selection=True)
