from pathlib import Path

import pytest

from src.tdd_harness.exceptions import SecurityError
from src.tdd_harness.phase import Phase
from src.tdd_harness.security import SecurityInterceptor


@pytest.fixture
def interceptor():
    return SecurityInterceptor()


def test_is_path_allowed_global_lockdown(interceptor):
    assert not interceptor.is_path_allowed(".tdd-harness/config.yaml", is_write=True)
    assert interceptor.is_path_allowed(".tdd-harness/config.yaml", is_write=False)
    assert not interceptor.is_path_allowed("src/tdd_harness/runner.py", is_write=True)
    assert not interceptor.is_path_allowed(".TDD-HARNESS/config.yaml", is_write=True)
    assert not interceptor.is_path_allowed("SRC/TDD_HARNESS/runner.py", is_write=True)
    assert not interceptor.is_path_allowed(".git/config", is_write=True)


def test_is_path_allowed_phase_constraints(interceptor):
    interceptor.current_phase = Phase.AMBER
    assert interceptor.is_path_allowed("src/app/main.py", is_write=True)
    assert not interceptor.is_path_allowed("tests/test_main.py", is_write=True)
    assert interceptor.is_path_allowed("tests/test_main.py", is_write=False)

    interceptor.current_phase = Phase.RED
    assert not interceptor.is_path_allowed("src/app/main.py", is_write=True)
    assert interceptor.is_path_allowed("src/app/main.py", is_write=False)
    assert interceptor.is_path_allowed("tests/test_main.py", is_write=True)


def test_is_path_allowed_outside_workspace(interceptor, tmp_path):
    outside = tmp_path.parent / "outside.txt"
    assert not interceptor.is_path_allowed(str(outside), is_write=False)


def test_is_path_allowed_empty_parts(interceptor, tmp_path):
    cwd = Path.cwd().resolve()
    assert interceptor.is_path_allowed(str(cwd), is_write=False)


def test_is_path_allowed_phase_specific(interceptor):
    interceptor.current_phase = Phase.RED
    assert not interceptor.is_path_allowed("src/app.py", is_write=True)
    interceptor.current_phase = Phase.GREEN
    assert not interceptor.is_path_allowed("tests/test_app.py", is_write=True)


def test_is_path_allowed_phase_specific_lower(interceptor):
    interceptor.current_phase = Phase.GREEN
    assert not interceptor.is_path_allowed("TESTS/test_app.py", is_write=True)
    interceptor.current_phase = Phase.RED
    assert not interceptor.is_path_allowed("SRC/app.py", is_write=True)


def test_is_path_allowed_global_lockdown_git(interceptor):
    assert not interceptor.is_path_allowed(".GIT/config", is_write=True)
    assert not interceptor.is_path_allowed(".git/HEAD", is_write=True)
    assert interceptor.is_path_allowed(".git/config", is_write=False)


def test_read_file_safe_denied(interceptor):
    interceptor.current_phase = Phase.RED
    from unittest.mock import patch

    with pytest.raises(SecurityError, match="Read access"):
        with patch.object(interceptor, "is_path_allowed", return_value=False):
            interceptor.read_file_safe("some_file.py")


def test_read_file_safe_success(interceptor, tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello")
    from unittest.mock import patch

    with patch.object(interceptor, "is_path_allowed", return_value=True):
        assert interceptor.read_file_safe(str(f)) == "hello"


def test_write_file_safe_denied(interceptor):
    from unittest.mock import patch

    with pytest.raises(SecurityError, match="Write access"):
        with patch.object(interceptor, "is_path_allowed", return_value=False):
            interceptor.write_file_safe("some_file.py", "content")


def test_write_file_safe_success(interceptor, tmp_path):
    f = tmp_path / "test.txt"
    from unittest.mock import patch

    with patch.object(interceptor, "is_path_allowed", return_value=True):
        res = interceptor.write_file_safe(str(f), "hello")
        assert "Successfully wrote to" in res
        assert f.read_text() == "hello"
