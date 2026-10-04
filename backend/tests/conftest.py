import pytest

from app.db.snapshots import get_snapshot_repository
from app.main import app


class DiscardSnapshots:
    def put(self, kind: str, resource_key: str, payload: bytes) -> None:
        pass


@pytest.fixture(autouse=True)
def isolate_http_snapshots():
    app.dependency_overrides[get_snapshot_repository] = lambda: DiscardSnapshots()
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_snapshot_repository, None)
