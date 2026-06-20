"""
Pytest adapter module.
"""

import json
import subprocess
from pathlib import Path

from src.tdd_harness.adapters.base import TestAdapter
from src.tdd_harness.models.tool import ToolCall, ToolCallResponse


class PytestAdapter(TestAdapter):
    """
    Test adapter for executing Pytest and parsing the report log.
    """

    supported_extensions: list[str] = [".py"]
    language: str = "python"

    def run(self, tool_call: ToolCall) -> ToolCallResponse:
        """
        Run pytest tests.
        """
        file_path = tool_call.arguments.get("file_path")
        coverage_dir = tool_call.arguments.get("coverage_dir")
        report_log_path = Path("temp/pytest-report.jsonl")

        # Ensure temp directory exists
        report_log_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = ["uv", "run", "pytest", "--report-log", str(report_log_path)]

        if coverage_dir:
            cov_file = Path(coverage_dir) / "pytest.lcov"
            cmd.extend(["--cov", f"--cov-report=lcov:{cov_file}"])

        if file_path:
            cmd.append(file_path)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            # Parse the report log if it exists
            errors = []
            if report_log_path.exists():
                with open(report_log_path) as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            record = json.loads(line)
                            if (
                                record.get("$report_type") == "TestReport"
                                and record.get("when") == "call"
                                and record.get("outcome") == "failed"
                            ):
                                # Extract exception details from the longrepr
                                longrepr = record.get("longrepr", {})
                                if isinstance(longrepr, dict):
                                    reprcrash = longrepr.get("reprcrash", {})
                                    err_msg = reprcrash.get("message", "Unknown error")
                                    errors.append(f"{record.get('nodeid')}: {err_msg}")
                                else:
                                    errors.append(f"{record.get('nodeid')}: {str(longrepr)}")
                        except json.JSONDecodeError:
                            continue

            return ToolCallResponse(
                success=(result.returncode == 0),
                output=result.stdout,
                errors=errors if errors else None,
                data={"return_code": result.returncode},
            )
        except Exception as e:
            return ToolCallResponse(success=False, output=None, errors=[str(e)], data={"error_type": type(e).__name__})
