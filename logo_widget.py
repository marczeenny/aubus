# logo_widget.py
# Reusable small logo widget for AUBus UI.
# Tries to load an image file 'aubus_logo.png' from current dir; if missing uses text.

from PyQt5.QtWidgets import QLabel, QSizePolicy # type: ignore
from PyQt5.QtGui import QPixmap, QFont # type: ignore
from PyQt5.QtCore import Qt, QSize # type: ignore
import os

# Maroon used across the UI
AUBUS_MAROON = "#800020"


class ResponsiveLogo(QLabel):
    """A QLabel that displays an image logo (preferred) or text and rescales
    the pixmap/font automatically when the widget is resized. This provides a
    consistent appearance on different devices and DPI settings.

    Usage: create via `ResponsiveLogo(logo_path=..., preferred_height=80)` or
    use the helper `get_logo_label` below.
    """

    def __init__(self, logo_path=None, preferred_height: int = 100, fallback_text: str = "AUBus"):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self._preferred_height = int(preferred_height)
        self._fallback_text = fallback_text
        self._updating = False  # Guard against recursive resizeEvent

        # Resolve logo path relative to this file if given as a filename
        if logo_path:
            if not os.path.isabs(logo_path):
                module_dir = os.path.dirname(__file__)
                logo_path = os.path.join(module_dir, logo_path)

        self._original_pixmap = None
        if logo_path and os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            if not pix.isNull():
                self._original_pixmap = pix

        if not self._original_pixmap:
            # text fallback
            self.setText(self._fallback_text)
            f = QFont("Verdana", max(12, int(self._preferred_height * 0.4)))
            f.setBold(True)
            self.setFont(f)
            self.setStyleSheet(f"color: {AUBUS_MAROON};")
        else:
            # set an initial pixmap scaled to preferred height
            self._update_pixmap(self._preferred_height)

    def _update_pixmap(self, target_height: int):
        if not self._original_pixmap or target_height < 10:
            return
        # maintain aspect ratio, use smooth transformation for quality
        scaled = self._original_pixmap.scaledToHeight(target_height, Qt.SmoothTransformation)
        self.setPixmap(scaled)
        # keep a small vertical padding so layouts don't clip the image
        self.setMinimumHeight(min(target_height + 4, scaled.height() + 4))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Guard against recursive updates triggered by setPixmap/setMinimumHeight
        if self._updating:
            return
        self._updating = True
        try:
            # if we have an image, scale it to fit within current height while
            # preserving aspect ratio. If not, adjust the font size for fallback text.
            h = max(10, self.height())
            if self._original_pixmap:
                self._update_pixmap(h)
            else:
                # scale fallback font size based on height
                font_size = max(10, int(h * 0.4))
                f = self.font() or QFont("Verdana")
                f.setPointSize(font_size)
                f.setBold(True)
                self.setFont(f)
        finally:
            self._updating = False


def get_logo_label(size=100, logo_path: str = "aubus_logo.png"):
    """Helper to create a `ResponsiveLogo` instance.

    - `size` is the preferred initial height in pixels.
    - `logo_path` is the path (relative to this module) of the logo image.
      If the image is missing, a text fallback is used.
    """
    return ResponsiveLogo(logo_path=logo_path, preferred_height=size)

