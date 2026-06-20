from unittest.mock import MagicMock, patch

from src.tdd_harness.adapters.lcov_adapter import LcovAdapter
from src.tdd_harness.models.tool import ToolCall


def test_lcov_adapter_success():
    adapter = LcovAdapter()
    call = ToolCall(tool_name="coverage", arguments={})

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="Coverage 100%", stderr="")

        response = adapter.parse(call)

        assert response.success is True
        assert response.output == "Coverage 100%"
        assert response.errors is None


def test_lcov_adapter_failure():
    adapter = LcovAdapter()
    call = ToolCall(tool_name="coverage", arguments={})

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Script failed")

        response = adapter.parse(call)

        assert response.success is False
        assert "Script failed" in response.errors[0]
