"""Unit tests for :class:`BcryptPasswordHasher`."""

from __future__ import annotations

from src.infrastructure.auth.password_hasher import BcryptPasswordHasher


class TestBcryptPasswordHasher:
    def test_hash_then_verify_succeeds(self) -> None:
        hasher = BcryptPasswordHasher(rounds=4)  # cheap rounds for tests
        h = hasher.hash("hunter2")
        assert hasher.verify("hunter2", h) is True

    def test_verify_wrong_password_fails(self) -> None:
        hasher = BcryptPasswordHasher(rounds=4)
        h = hasher.hash("hunter2")
        assert hasher.verify("wrong", h) is False

    def test_hash_is_not_plaintext(self) -> None:
        hasher = BcryptPasswordHasher(rounds=4)
        h = hasher.hash("hunter2")
        assert "hunter2" not in h
        assert h.startswith("$2")  # bcrypt prefix

    def test_two_hashes_of_same_password_differ(self) -> None:
        hasher = BcryptPasswordHasher(rounds=4)
        assert hasher.hash("hunter2") != hasher.hash("hunter2")

    def test_malformed_hash_is_not_a_match(self) -> None:
        hasher = BcryptPasswordHasher(rounds=4)
        assert hasher.verify("anything", "not-a-real-hash") is False