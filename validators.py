"""validators.py

Small validation helpers for the frontend.
"""
import re

# Simple, pragmatic email validator. This is not fully RFC-complete but
# rejects obviously-invalid strings and accepts most normal addresses.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email: str) -> bool:
    """Return True if `email` looks like a valid email address.

    Uses a lightweight regex safe for client-side validation. For strict
    validation rely on server-side checks.
    """
    if not email or not isinstance(email, str):
        return False
    return _EMAIL_RE.fullmatch(email.strip()) is not None
