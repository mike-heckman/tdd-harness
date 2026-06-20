"""
Ruff adapter module.
"""

import json
import subprocess

from src.tdd_harness.adapters.base import LintAdapter
from src.tdd_harness.models.tool import ToolCall, ToolCallResponse


class RuffAdapter(LintAdapter):
    """
    Adapter for linting with Ruff.
    """

    supported_extensions: list[str] = [".py"]
    language: str = "python"

    def run(self, tool_call: ToolCall) -> ToolCallResponse:
        """
        Run ruff linter.
        """
        file_path = tool_call.arguments.get("file_path")
        directories = tool_call.arguments.get("directories")

        cmd = ["uv", "run", "ruff", "check", "--output-format", "json"]

        if file_path:
            cmd.append(file_path)
        elif directories and isinstance(directories, list):
            cmd.extend(directories)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            errors = []
            try:
                if result.stdout.strip():
                    lint_results = json.loads(result.stdout)
                    for lint in lint_results:
                        msg = f"{lint.get('filename')}:{lint.get('location', {}).get('row', 0)} - {lint.get('message')}"
                        errors.append(msg)
            except json.JSONDecodeError:
                errors.append(f"Failed to parse Ruff JSON output. Raw output: {result.stdout}")

            return ToolCallResponse(
                success=(result.returncode == 0),
                output=result.stdout,
                errors=errors if errors else None,
                data={"return_code": result.returncode},
            )
        except Exception as e:
            return ToolCallResponse(success=False, output=None, errors=[str(e)], data={"error_type": type(e).__name__})
