"""bcrypt-backed password hasher.

We use ``bcrypt`` directly instead of ``passlib`` because passlib 1.7.4 (the
current PyPI release) is incompatible with bcrypt 5.x: its backend probe
issues an 80-byte test password, which bcrypt 5 rejects with
``ValueError("password cannot be longer than 72 bytes")``. ``bcrypt`` works
cleanly and is the modern recommendation. The dependency declaration for
``passlib[bcrypt]`` in pyproject is kept for now — INS-12 (quality final) is
the right ticket to clean it up project-wide.
"""

from __future__ import annotations

import bcrypt

from src.application.ports.password_hasher import PasswordHasher

# 12 is the OWASP-recommended cost factor as of 2025 for bcrypt-based password
# storage. Higher slows logins, lower weakens security.
_DEFAULT_ROUNDS = 12


class BcryptPasswordHasher(PasswordHasher):
    def __init__(self, rounds: int = _DEFAULT_ROUNDS) -> None:
        self._rounds = rounds

    def hash(self, plain_password: str) -> str:
        salt = bcrypt.gensalt(rounds=self._rounds)
        return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8"),
            )
        except ValueError:
            # Malformed hash on disk — treat as a non-match instead of crashing.
            return False