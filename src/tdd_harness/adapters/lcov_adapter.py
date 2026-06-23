"""
Lcov adapter module.
"""

import subprocess

from ..models.tool import ToolCall, ToolCallResponse
from .base import CoverageAdapter


class LcovAdapter(CoverageAdapter):
    """
    Adapter for generating and parsing unified coverage data.
    """

    supported_extensions: list[str] = [".py"]
    language: str = "python"

    def run(self, tool_call: ToolCall) -> ToolCallResponse:
        """
        Run is not supported for coverage adapters.
        """
        return ToolCallResponse(success=False, output=None, errors=["run() is not supported"])

    def parse(self, tool_call: ToolCall) -> ToolCallResponse:
        """
        Parse coverage data from lcov files.
        """
        coverage_dir = tool_call.arguments.get("coverage_dir")
        cmd = ["uv", "run", "python", "./scripts/generate-unified-coverage.py"]

        if coverage_dir:
            cmd.extend(["--coverage-dir", coverage_dir])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            return ToolCallResponse(
                success=(result.returncode == 0),
                output=result.stdout,
                errors=[result.stderr] if result.stderr and result.returncode != 0 else None,
                data={"return_code": result.returncode},
            )
        except Exception as e:
            return ToolCallResponse(success=False, output=None, errors=[str(e)], data={"error_type": type(e).__name__})
