"""Messages tab UI and P2P/client messaging helpers.

Provides `MessagesTab` which handles contact list, chat UI, P2P sends and
server-relay fallback including inline display of small image attachments.
"""

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

from .ui_styles import set_title_label, style_button, style_input
from .api_client import ApiClientError
from .peer import peer_send
import base64
import mimetypes
from PyQt5.QtWidgets import QFileDialog


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

        attach_btn = QPushButton("Attach")
        attach_btn.clicked.connect(self.choose_attachment)
        style_button(attach_btn, min_height=30)
        row.addWidget(attach_btn)

        self.attachment_label = QLabel("")
        row.addWidget(self.attachment_label)

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
        try:
            print(f"[MessagesTab] refresh_contacts: loaded {len(contacts)} contacts")
        except Exception:
            pass
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

        # Attempt peer-to-peer send if we have peer info for this contact
        peer_ip = self.current_contact.get('peer_ip') or self.current_contact.get('peer_address')
        peer_port = self.current_contact.get('peer_port')

        # include attachment if present
        attachment_filename = getattr(self, '_attachment_filename', None)
        attachment_mime = getattr(self, '_attachment_mime', None)
        attachment_data = getattr(self, '_attachment_data', None)

        if peer_ip and peer_port:
            try:
                print(f"[MessagesTab] attempting P2P send to {peer_ip}:{peer_port}")
                peer_payload = {"from": self.app_state.get('username'), "body": text}
                if attachment_data:
                    peer_payload.update({"attachment_filename": attachment_filename, "attachment_mime": attachment_mime, "attachment_data": attachment_data})
                peer_send(peer_ip, int(peer_port), {"type": "CHAT_PEER", "payload": peer_payload})
                print(f"[MessagesTab] P2P send to {peer_ip}:{peer_port} succeeded")

                payload = {"sender_id": self.app_state.get("user_id"), "receiver_id": self.current_contact.get("id"), "body": text, "sent_at": ""}
                if attachment_data:
                    payload.update({"attachment_filename": attachment_filename, "attachment_mime": attachment_mime, "attachment_data": attachment_data})
                self._append_message(self.current_contact, payload)
                self.message_input.clear()
                # clear attachment after sending
                if hasattr(self, '_attachment_data'):
                    delattr(self, '_attachment_data')
                if hasattr(self, '_attachment_filename'):
                    delattr(self, '_attachment_filename')
                if hasattr(self, '_attachment_mime'):
                    delattr(self, '_attachment_mime')
                self.attachment_label.setText("")
                return
            except Exception:
                try:
                    print(f"[MessagesTab] P2P send to {peer_ip}:{peer_port} failed, falling back to server")
                except Exception:
                    pass

        # Fallback to server-relay
        try:
            response = api.send_message(
                self.current_contact["username"],
                text,
                attachment_filename=attachment_filename,
                attachment_mime=attachment_mime,
                attachment_data=attachment_data,
            )
        except ApiClientError as exc:
            QMessageBox.critical(self, "Unable to send", str(exc))
            return

        if response.get("type") == "SEND_MESSAGE_OK":
            payload = {
                "sender_id": self.app_state.get("user_id"),
                "receiver_id": self.current_contact.get("id"),
                "body": text,
                "sent_at": response.get("payload", {}).get("sent_at", "")
            }
            if attachment_data:
                payload.update({"attachment_filename": attachment_filename, "attachment_mime": attachment_mime, "attachment_data": attachment_data})
            self._append_message(self.current_contact, payload)
            self.message_input.clear()
            # clear attachment after sending
            if hasattr(self, '_attachment_data'):
                delattr(self, '_attachment_data')
            if hasattr(self, '_attachment_filename'):
                delattr(self, '_attachment_filename')
            if hasattr(self, '_attachment_mime'):
                delattr(self, '_attachment_mime')
            self.attachment_label.setText("")
        else:
            reason = response.get("payload", {}).get("reason", "")
            QMessageBox.warning(self, "Unable to send", f"Server rejected the message: {reason}")

    # Called by PeerServer when a peer sends a message directly
    def handle_peer_message(self, addr, msg):
        if not isinstance(msg, dict):
            return
        if msg.get('type') != 'CHAT_PEER':
            return
        payload = msg.get('payload', {})
        from_username = payload.get('from')
        body = payload.get('body')
        if not from_username or body is None:
            return
        contact = self._ensure_contact(from_username)
        entry = {
            'sender_id': None,
            'receiver_id': self.app_state.get('user_id'),
            'body': body,
            'sent_at': ''
        }
        # include attachments if provided by peer
        if 'attachment_filename' in payload:
            entry['attachment_filename'] = payload.get('attachment_filename')
        if 'attachment_mime' in payload:
            entry['attachment_mime'] = payload.get('attachment_mime')
        if 'attachment_data' in payload:
            entry['attachment_data'] = payload.get('attachment_data')
        if self.current_contact and self.current_contact.get('username') == from_username:
            self._append_message(contact or {'username': from_username}, entry)
        else:
            self.unread_contacts.add(from_username)
            if contact is None:
                contact = {'username': from_username, 'name': from_username}
            self.active_ride_contact = contact
            self.refresh_contacts(preserve_selection=True)

    def choose_attachment(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Select file to attach", "", "Images and Audio (*.png *.jpg *.jpeg *.bmp *.gif *.wav *.mp3);;All Files (*)")
        if not fname:
            return
        try:
            with open(fname, 'rb') as f:
                data = f.read()
            b64 = base64.b64encode(data).decode('ascii')
            mime, _ = mimetypes.guess_type(fname)
            if not mime:
                mime = 'application/octet-stream'
            # store for next send
            self._attachment_data = b64
            self._attachment_filename = fname.split('/')[-1].split('\\')[-1]
            self._attachment_mime = mime
            self.attachment_label.setText(f"Attached: {self._attachment_filename}")
        except Exception as e:
            QMessageBox.warning(self, "Attachment error", f"Unable to read file: {e}")

    def _append_message(self, contact, message_entry):
        user_id = self.app_state.get("user_id")
        sender_id = message_entry.get("sender_id")
        sent_at = message_entry.get("sent_at", "")
        prefix = "You" if sender_id == user_id else contact.get("name") or contact.get("username")
        # Render attachments inline for images, otherwise show placeholder
        body = message_entry.get('body') or ''
        attachment_mime = message_entry.get('attachment_mime')
        attachment_filename = message_entry.get('attachment_filename')
        attachment_data = message_entry.get('attachment_data')
        if attachment_data and attachment_mime and attachment_mime.startswith('image/'):
            try:
                img_html = f"<br><img src=\"data:{attachment_mime};base64,{attachment_data}\" width=300><br>" \
                    + (f"<i>{attachment_filename}</i><br>" if attachment_filename else "")
                line_html = f"[{sent_at}] <b>{prefix}:</b> {body}{img_html}"
                self.chat_history.append(line_html)
            except Exception:
                line = f"[{sent_at}] {prefix}: {body} [Image: {attachment_filename}]"
                self.chat_history.append(line)
        else:
            line = f"[{sent_at}] {prefix}: {body}"
            if attachment_data and attachment_filename:
                line += f" [Attachment: {attachment_filename}]"
            self.chat_history.append(line)
        try:
            log_line = None
            try:
                log_line = line
            except NameError:
                pass
            try:
                log_line = log_line or line_html
            except NameError:
                pass
            if not log_line:
                log_line = f"[{sent_at}] {prefix}: {body}"
            print(f"[MessagesTab] appended message to chat_history: {log_line}")
        except Exception:
            pass

    def handle_event(self, event):
        try:
            print(f"[MessagesTab] handle_event: {event.type} payload={event.payload}")
        except Exception:
            pass
        if event.type == "CHAT_MESSAGE":
            payload = event.payload
            username = payload.get("from")
            if not username:
                try:
                    print("[MessagesTab] CHAT_MESSAGE with no from field")
                except Exception:
                    pass
                return
            contact = self._ensure_contact(username)
            if not contact:
                try:
                    print(f"[MessagesTab] CHAT_MESSAGE from {username} but contact not found after ensure_contact")
                except Exception:
                    pass
                return
            entry = {
                "sender_id": payload.get("from_id"),
                "receiver_id": payload.get("to_id"),
                "body": payload.get("message"),
                "sent_at": payload.get("sent_at", "")
            }
            # include attachments if present
            if payload.get("attachment_filename"):
                entry["attachment_filename"] = payload.get("attachment_filename")
            if payload.get("attachment_mime"):
                entry["attachment_mime"] = payload.get("attachment_mime")
            if payload.get("attachment_data"):
                entry["attachment_data"] = payload.get("attachment_data")
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
            # Suppress alarming UI message; keep an internal debug print instead.
            try:
                print("[MessagesTab] Event: CONNECTION_LOST received — server connection lost")
            except Exception:
                pass

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
                # include peer info if available on the ride_info
                if ride_info.get('driver_ip'):
                    contact['peer_ip'] = ride_info.get('driver_ip')
                if ride_info.get('driver_port'):
                    contact['peer_port'] = ride_info.get('driver_port')
        if contact != self.active_ride_contact:
            self.active_ride_contact = contact
            self.refresh_contacts(preserve_selection=True)
        if contact and self.current_contact and self.current_contact.get("username") == contact["username"]:
            self.load_conversation(self.current_contact)

    def clear_active_ride(self):
        if self.active_ride_contact:
            self.active_ride_contact = None
            self.refresh_contacts(preserve_selection=True)
