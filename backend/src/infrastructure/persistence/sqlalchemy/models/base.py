"""Shared declarative base for all SQLAlchemy ORM models."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Single declarative base. Lives here so every model file imports it."""