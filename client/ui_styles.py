"""UI styling helpers used across the client.

Defines common colors, button styles, and helper functions to keep a
consistent look-and-feel across the app.
"""

from PyQt5.QtGui import QFont # type: ignore
from PyQt5.QtWidgets import QPushButton, QLabel # type: ignore
from PyQt5.QtCore import Qt # type: ignore

# Primary color used across the UI
PRIMARY_COLOR = "#800020"

# Button CSS: maroon background, white text, rounded corners
BUTTON_CSS = f"""
QPushButton {{
  background-color: {PRIMARY_COLOR};
  color: white;
  border-radius: 8px;
  padding: 8px 12px;
}}
QPushButton:hover {{
  background-color: #a00035;
}}
"""


def style_button(btn: QPushButton, min_height: int = 36):
    """Apply a consistent style to buttons."""
    btn.setStyleSheet(BUTTON_CSS)
    try:
        btn.setMinimumHeight(min_height)
    except Exception:
        pass
    try:
        btn.setCursor(Qt.PointingHandCursor)
    except Exception:
        pass


def set_title_label(lbl: QLabel, size: int = 16):
    """Set font and color for title-like labels."""
    f = QFont("Verdana", size)
    f.setBold(True)
    lbl.setFont(f)
    lbl.setStyleSheet(f"color: {PRIMARY_COLOR};")


def style_input(widget, min_height: int = 32, width: int = 260, font_size: int = 12, center: bool = True):
    """Apply consistent styling to input widgets (QLineEdit, QSpinBox, QTextEdit).

    - `min_height` and `width` control size to match buttons visually.
    - `center` sets the text alignment to centered for single-line inputs.
    """
    css = f"""
    QLineEdit, QSpinBox, QTextEdit {{
      border: 1px solid #ccc;
      border-radius: 6px;
      padding: 6px 8px;
      font-size: {font_size}px;
    }}
    """
    try:
        widget.setStyleSheet(css)
    except Exception:
        pass
    try:
        widget.setMinimumHeight(min_height)
    except Exception:
        pass
    try:
        widget.setFixedWidth(width)
    except Exception:
        pass
    if center:
        # QLineEdit and QSpinBox support setAlignment
        try:
            widget.setAlignment(Qt.AlignCenter)
        except Exception:
            # QTextEdit uses setAlignment via cursor; ignore if not supported
            pass
