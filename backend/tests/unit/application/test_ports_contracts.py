"""Contract tests for INS-4 ports.

Each port is an abstract contract that infrastructure adapters must fully
implement (Liskov / Dependency Inversion). These tests pin the abstract method
set so an accidental change to a port surfaces here, and prove the ports cannot
be instantiated directly.
"""
import pytest

from src.application.ports.audit_repository import AuditRepository
from src.application.ports.changeset_repository import ChangeSetRepository
from src.application.ports.conflict_repository import ConflictRepository
from src.application.ports.file_storage_gateway import FileStorageGateway
from src.application.ports.queue_gateway import QueueGateway

PORT_CONTRACTS = [
    (ChangeSetRepository, {"has_been_applied", "record_applied", "get_applied"}),
    (ConflictRepository, {"save", "list_unresolved", "mark_resolved"}),
    (AuditRepository, {"append", "append_many", "list_for_inspection"}),
    (
        FileStorageGateway,
        {"put", "get", "exists", "generate_presigned_url", "delete"},
    ),
    (QueueGateway, {"enqueue"}),
]


@pytest.mark.parametrize(("port", "expected_methods"), PORT_CONTRACTS)
def test_port_is_abstract(port: type, expected_methods: set[str]) -> None:
    with pytest.raises(TypeError):
        port()  # type: ignore[abstract]


@pytest.mark.parametrize(("port", "expected_methods"), PORT_CONTRACTS)
def test_port_defines_expected_contract(port: type, expected_methods: set[str]) -> None:
    assert port.__abstractmethods__ == frozenset(expected_methods)
