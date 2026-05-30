import dataclasses
from uuid import uuid4

import pytest

from src.domain.policies.conflict import (
    Conflict,
    ConflictPolicy,
    ConflictType,
    ResolutionStrategy,
)
from src.domain.value_objects.version import Version


def test_detect_no_conflict_when_base_matches_current():
    assert ConflictPolicy.detect(Version(3), Version(3)) is None


def test_detect_concurrent_modification_when_base_behind_current():
    result = ConflictPolicy.detect(Version(2), Version(5))
    assert result is ConflictType.CONCURRENT_MODIFICATION


def test_detect_stale_client_when_base_ahead_of_current():
    result = ConflictPolicy.detect(Version(6), Version(4))
    assert result is ConflictType.STALE_CLIENT


def test_conflict_between_returns_none_when_versions_match():
    assert Conflict.between(uuid4(), "inspection", Version(1), Version(1)) is None


def test_conflict_between_builds_conflict_on_concurrent_modification():
    entity_id = uuid4()
    conflict = Conflict.between(entity_id, "inspection", Version(2), Version(5))

    assert conflict is not None
    assert conflict.entity_id == entity_id
    assert conflict.entity_type == "inspection"
    assert conflict.base_version == Version(2)
    assert conflict.current_version == Version(5)
    assert conflict.type is ConflictType.CONCURRENT_MODIFICATION


def test_conflict_between_builds_conflict_on_stale_client():
    conflict = Conflict.between(uuid4(), "observation", Version(9), Version(4))

    assert conflict is not None
    assert conflict.type is ConflictType.STALE_CLIENT


def test_conflict_is_immutable():
    conflict = Conflict.between(uuid4(), "inspection", Version(0), Version(1))
    assert conflict is not None
    with pytest.raises(dataclasses.FrozenInstanceError):
        conflict.entity_type = "tampered"  # type: ignore[misc]


def test_resolution_strategy_values():
    assert {s.value for s in ResolutionStrategy} == {
        "keep_server",
        "keep_client",
        "manual_merge",
    }
