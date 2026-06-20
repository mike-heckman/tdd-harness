import json
from unittest.mock import MagicMock, patch

from src.tdd_harness.adapters.ruff_adapter import RuffAdapter
from src.tdd_harness.models.tool import ToolCall


def test_ruff_adapter_success():
    adapter = RuffAdapter()
    call = ToolCall(tool_name="lint", arguments={})

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        response = adapter.run(call)

        assert response.success is True
        assert response.errors is None
        mock_run.assert_called_once()


def test_ruff_adapter_failure():
    adapter = RuffAdapter()
    call = ToolCall(tool_name="lint", arguments={"file_path": "main.py"})

    with patch("subprocess.run") as mock_run:
        lint_output = json.dumps(
            [{"filename": "main.py", "location": {"row": 10}, "message": "F401 'os' imported but unused"}]
        )
        mock_run.return_value = MagicMock(returncode=1, stdout=lint_output)

        response = adapter.run(call)

        assert response.success is False
        assert len(response.errors) == 1
        assert "main.py:10 - F401 'os' imported but unused" in response.errors[0]


def test_ruff_adapter_invalid_json():
    adapter = RuffAdapter()
    call = ToolCall(tool_name="lint", arguments={})

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="not json")

        response = adapter.run(call)

        assert response.success is False
        assert "Failed to parse Ruff JSON output" in response.errors[0]
