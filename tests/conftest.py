import uuid

import pytest


@pytest.fixture(autouse=True)
def mock_session_uuid(monkeypatch):
    """
    Ensure all generated session IDs during tests are prefixed with 'test-'.
    """
    original_uuid4 = uuid.uuid4
    monkeypatch.setattr("src.tdd_harness.config.uuid4", lambda: f"test-{original_uuid4()}")
