"""User domain entity.

The domain holds only the data that represents a user; password verification
and JWT issuance are NOT here — those are infrastructure concerns reached
through the ``PasswordHasher`` and ``TokenProvider`` ports. The acceptance
criteria of INS-14 explicitly require this separation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.domain.value_objects.ids import UserId


@dataclass
class User:
    """A persisted user. Identity is ``id``; ``email`` is unique by invariant."""

    id: UserId
    email: str
    password_hash: str
    role: str
    created_at: datetime
    updated_at: datetime