"""Base UI utilities for the AUBus client.

Provides a simple `BaseWindow` with common header and content area used by pages.
"""

from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel

class BaseWindow(QMainWindow):
    def __init__(self, title="My App"):
        super().__init__()
        self.setWindowTitle(title)

        # Central widget
        self.central = QWidget()
        self.layout = QVBoxLayout(self.central)

        # Common header section
        self.header = QLabel("This is the header")
        self.layout.addWidget(self.header)

        # Placeholder for child content
        self.content = QWidget()
        self.layout.addWidget(self.content)

        self.setCentralWidget(self.central)

    # Method to set child content
    def set_content(self, widget):
        self.layout.replaceWidget(self.content, widget)
        self.content.deleteLater()
        self.content = widget
