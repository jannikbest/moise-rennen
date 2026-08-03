"""User register-or-login with scrypt-hashed 4-digit PINs."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import time
from typing import Tuple

from store import Store

NAME_RE = re.compile(r"^[A-Za-z0-9ÄÖÜäöüß _.-]{1,12}$")
PIN_RE = re.compile(r"^\d{4}$")


def normalize_name(name: str) -> str:
    return (name or "").strip()


def name_key(name: str) -> str:
    return normalize_name(name).casefold()


def _hash_pin(pin: str, salt: bytes) -> str:
    digest = hashlib.scrypt(
        pin.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
        dklen=32,
    )
    return digest.hex()


def register_or_login(store: Store, name: str, pin: str) -> Tuple[bool, str, str]:
    """Returns (ok, error_code, display_name). error: invalid|wrong_pin|name_taken."""
    display = normalize_name(name)
    if not NAME_RE.match(display) or not PIN_RE.match(pin or ""):
        return False, "invalid", ""

    key = name_key(display)
    users = store.users
    existing = users.get(key)

    if existing is None:
        # Name already used by another casing? keys are casefold so unique.
        for u in users.values():
            if isinstance(u, dict) and name_key(u.get("name", "")) == key:
                return False, "name_taken", ""
        salt = secrets.token_bytes(16)
        store.set_user(
            key,
            {
                "name": display,
                "salt": salt.hex(),
                "hash": _hash_pin(pin, salt),
                "created": int(time.time()),
            },
        )
        return True, "", display

    salt = bytes.fromhex(existing["salt"])
    expected = existing["hash"]
    actual = _hash_pin(pin, salt)
    if not hmac.compare_digest(expected, actual):
        return False, "wrong_pin", ""
    return True, "", existing.get("name") or display
