# messages_tab.py
# Simple chat UI skeleton. Lists contacts and allows sending messages (local demo only).
# In the final system this will connect to peers (driver/passenger) via P2P sockets.

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QLineEdit, QPushButton, QTextEdit, QHBoxLayout # type: ignore
from PyQt5.QtGui import QFont  # type: ignore
from logo_widget import AUBUS_MAROON

class MessagesTab(QWidget):
    def __init__(self, app_state=None):
        super().__init__()
        self.app_state = app_state or {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        title = QLabel("Messages")
        title.setFont(QFont("Verdana", 14))
        title.setStyleSheet(f"color: {AUBUS_MAROON};")
        layout.addWidget(title)

        # left: contacts, right: chat
        container = QHBoxLayout()
        self.contacts = QListWidget()
        # demo contacts (in real app: fill from previous rides)
        for i in range(1,6):
            self.contacts.addItem(f"User{i}")
        self.contacts.currentItemChanged.connect(self.on_contact_selected)
        container.addWidget(self.contacts, 1)

        right = QVBoxLayout()
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        right.addWidget(self.chat_history, 4)

        row = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type a message...")
        row.addWidget(self.message_input)
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send_message)
        row.addWidget(send_btn)
        right.addLayout(row)
        container.addLayout(right, 3)

        layout.addLayout(container)
        self.setLayout(layout)

    def on_contact_selected(self, cur, prev):
        if cur:
            self.chat_history.setText(f"Chat with {cur.text()} (demo).")

    def send_message(self):
        cur = self.contacts.currentItem()
        if not cur:
            return
        text = self.message_input.text().strip()
        if not text:
            return
        # Append locally to chat history
        self.chat_history.append(f"You: {text}")
        self.message_input.clear()
        # TODO: send message to peer via peer-to-peer socket when connected.
