#!/usr/bin/env python3
"""Admin auth tokens for Konfig/Debug WebSocket actions."""
import os
import secrets
import time
import logging
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


class AuthManager:
    TOKEN_TTL = 3600

    def __init__(self, env_path=None):
        self.logger = logging.getLogger(__name__)
        if load_dotenv:
            path = env_path or Path(__file__).parent / ".env"
            load_dotenv(path)
        self.password = os.environ.get("MOISE_ADMIN_PASSWORD", "moise")
        self._tokens = {}  # token -> expiry

    def login(self, password):
        if password != self.password:
            return None
        token = secrets.token_urlsafe(24)
        self._tokens[token] = time.time() + self.TOKEN_TTL
        self.logger.info("Admin login successful")
        return {"token": token, "ttl": self.TOKEN_TTL}

    def validate(self, token):
        if not token:
            return False
        expiry = self._tokens.get(token)
        if expiry is None:
            return False
        if time.time() > expiry:
            self._tokens.pop(token, None)
            return False
        # Sliding renewal
        self._tokens[token] = time.time() + self.TOKEN_TTL
        return True
