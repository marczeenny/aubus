# logo_widget.py
# Reusable small logo widget for AUBus UI.
# Tries to load an image file 'aubus_logo.png' from current dir; if missing uses text.

from PyQt5.QtWidgets import QLabel # type: ignore
from PyQt5.QtGui import QPixmap, QFont # type: ignore
import os

AUBUS_MAROON = "#800020"

def get_logo_label(size=100):
    """
    Returns a QLabel widget containing the AUBus logo (image if available,
    otherwise text). 'size' controls the pixmap height (keeps aspect ratio).
    """
    lbl = QLabel()
    logo_path = "aubus_logo.png"  # put the generated logo file here for best results

    if os.path.exists(logo_path):
        pix = QPixmap(logo_path)
        if not pix.isNull():
            pix = pix.scaledToHeight(size)
            lbl.setPixmap(pix)
            lbl.setFixedHeight(size + 10)
            return lbl

    # Fallback: text-based logo
    lbl.setText("AUBus")
    f = QFont("Verdana", 24)
    f.setBold(True)
    lbl.setFont(f)
    lbl.setStyleSheet(f"color: {AUBUS_MAROON};")
    return lbl
