import json
from unittest.mock import MagicMock, patch

from src.tdd_harness.adapters.pytest_adapter import PytestAdapter
from src.tdd_harness.models.tool import ToolCall


def test_pytest_adapter_success():
    adapter = PytestAdapter()
    call = ToolCall(tool_name="test", arguments={"file_path": "tests/test_dummy.py"})

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="All tests passed")

        with patch("pathlib.Path.exists", return_value=False):
            response = adapter.run(call)

            assert response.success is True
            assert response.output == "All tests passed"
            assert response.errors is None
            assert response.data["return_code"] == 0
            mock_run.assert_called_once()


def test_pytest_adapter_failure_with_log():
    adapter = PytestAdapter()
    call = ToolCall(tool_name="test", arguments={})

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="Failed")

        with patch("pathlib.Path.exists", return_value=True):
            log_content = (
                json.dumps(
                    {
                        "$report_type": "TestReport",
                        "when": "call",
                        "outcome": "failed",
                        "nodeid": "test_app.py::test_fail",
                        "longrepr": {"reprcrash": {"message": "AssertionError: expected 1 got 2"}},
                    }
                )
                + "\n"
            )

            from io import StringIO

            with patch("builtins.open", return_value=StringIO(log_content)):
                response = adapter.run(call)

                assert response.success is False
                assert len(response.errors) == 1
                assert "test_app.py::test_fail: AssertionError: expected 1 got 2" in response.errors[0]


def test_pytest_adapter_exception():
    adapter = PytestAdapter()
    call = ToolCall(tool_name="test", arguments={})

    with patch("subprocess.run", side_effect=Exception("mock error")):
        response = adapter.run(call)

        assert response.success is False
        assert "mock error" in response.errors[0]
