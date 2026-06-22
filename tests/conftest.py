import pytest

from src.tdd_harness.config import CACHE_TDD_DIRECTORIES


@pytest.fixture(autouse=True)
def reset_global_config_cache():
    """
    Automatically reset the global config cache before and after every test.
    This ensures that mock project directories don't bleed across tests.
    """
    CACHE_TDD_DIRECTORIES.clear()
    yield
    CACHE_TDD_DIRECTORIES.clear()
