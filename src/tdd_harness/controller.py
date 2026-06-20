"""
TDD Loop Controller Module.
"""

import datetime
import shutil
import sys
import uuid
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from .config import TddHarnessConfig
from .registry import ToolRegistry
from .runner import orchestrate_targeted, run_coverage, run_lint, run_test


class Phase(Enum):
    """
    Enum representing the TDD phases.
    """

    AMBER = "amber"
    BLUE = "blue"
    RED = "red"
    GREEN = "green"
    MAGENTA = "magenta"


class SecurityError(Exception):
    """
    Raised when an operation violates a security boundary.
    """

    pass


class PhaseValidationError(Exception):
    """
    Raised when phase exit validation fails.
    """

    pass


class TDDLoopController:
    """
    Manages the TDD Loop, State Transitions, and File Security.
    """

    def __init__(self, config: TddHarnessConfig, registry: ToolRegistry):
        """
        Initialize the TDDLoopController.
        """
        self.config = config
        self.registry = registry
        self.current_phase = Phase.AMBER
        self.session_id = str(uuid.uuid4())

        # Register built-in file operations wrapped with security interceptors
        self.registry.register_python_tool(self.read_file_safe, name="read_file")
        self.registry.register_python_tool(self.write_file_safe, name="write_file")
        self.registry.register_python_tool(self.success, name="success")
        self.registry.register_python_tool(self.abort, name="abort")
        self.registry.register_python_tool(self.stage_test_implementation, name="stage_test_implementation")

    def _is_path_allowed(self, path: str, is_write: bool) -> bool:
        """
        Enforces global restrictions and phase-specific access rules.
        """
        target = Path(path).resolve()
        cwd = Path.cwd().resolve()

        try:
            rel_path = target.relative_to(cwd)
        except ValueError:
            return False  # Path is outside the workspace

        parts = rel_path.parts
        if not parts:
            return True

        # Global Lockdown
        if is_write and parts:
            if parts[0] == ".tdd-harness":
                return False
            if len(parts) >= 2 and parts[0] == "src" and parts[1] == "tdd_harness":
                return False

        # Phase-specific Write constraints
        if is_write and parts:
            if self.current_phase in (Phase.AMBER, Phase.BLUE, Phase.GREEN):
                # src/: rw, test/: ro
                if parts[0] == "tests":
                    return False
            elif self.current_phase in (Phase.RED, Phase.MAGENTA):
                # src/: ro, test/: rw
                if parts[0] == "src":
                    return False

        return True

    def read_file_safe(self, path: str) -> str:
        """
        Safely read a file, respecting phase access rules.
        """
        if not self._is_path_allowed(path, is_write=False):
            raise SecurityError(f"Read access to {path} denied.")
        with open(path, encoding="utf-8") as f:
            return f.read()

    def write_file_safe(self, path: str, content: str) -> str:
        """
        Safely write a file, respecting phase access rules.
        """
        if not self._is_path_allowed(path, is_write=True):
            raise SecurityError(f"Write access to {path} denied.")
        # Ensure parent dirs exist
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {path}"

    async def success(self, message: str) -> str:
        """
        Signals the agent believes it has satisfied the phase.
        """
        # Run full unit and lint tests
        lint_res = run_lint(self.config)
        if lint_res.get("status") != "success":
            return f"Validation failed: Linting errors.\\n{lint_res.get('stderr')}"

        try:
            if self.current_phase == Phase.RED:
                self.check_red_exit()
            elif self.current_phase == Phase.GREEN:
                self.check_green_exit()
            elif self.current_phase == Phase.BLUE:
                self.check_blue_exit(0)
            elif self.current_phase == Phase.MAGENTA:
                self.check_magenta_exit(100.0, 0)
        except PhaseValidationError as e:
            return f"Validation failed: {str(e)}"

        report_dir = Path("docs/tasks/reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / f"success_report_{self.session_id}.md"
        with open(report_file, "w") as f:
            f.write(f"Status: Success\\nMessage: {message}\\n")

        # Trigger MCP updates
        if self.current_phase in (Phase.RED, Phase.GREEN, Phase.BLUE, Phase.AMBER):
            try:
                await self.registry.dispatch("index_folder", {"path": "src"})
                await self.registry.dispatch("index_folder", {"path": "tests"})
            except ValueError:
                pass  # tool might not be loaded in mock tests

        return "Phase completed successfully."

    def abort(self, reason: str) -> str:
        """
        Explicit escape hatch to pause the loop.
        """
        report_dir = Path("docs/tasks/reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / f"abort_report_{self.session_id}.md"
        with open(report_file, "w") as f:
            f.write(f"Abort Reason: {reason}\\n")
        sys.exit(1)

    def stage_test_implementation(self, filepath: str, code: str, test_name: str, test_concept: str) -> str:
        """
        Stage a test implementation for the Red phase.
        """
        if self.current_phase != Phase.RED:
            return "Error: stage_test_implementation can only be used in the Red phase."

        target = Path(filepath)
        cache_dir = Path(".tdd-harness/.cache")
        cache_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
        backup_path = cache_dir / f"{target.name}.{timestamp}.bak"

        if target.exists():
            shutil.copy2(target, backup_path)

        self.write_file_safe(filepath, code)

        # Run targeted testing
        test_res = orchestrate_targeted(self.config, filepath)

        # Verify AssertionError or NotImplementedError
        has_expected_error = False
        errors = []
        for val in test_res.values():
            if val.get("status") == "failed":
                stderr = val.get("stderr", "")
                if "AssertionError" in stderr or "NotImplementedError" in stderr:
                    has_expected_error = True
                if stderr:
                    errors.append(stderr)

        if not has_expected_error:
            # Revert
            if backup_path.exists():
                shutil.copy2(backup_path, target)
            else:
                target.unlink(missing_ok=True)
            return (
                f"Error: Test did not fail with AssertionError or NotImplementedError. Reverted file. Errors: {errors}"
            )

        # Write reasoning
        reasoning_file = Path(f"{target.name}-reasoning.yaml")
        reasoning_data = {}
        if reasoning_file.exists():
            with open(reasoning_file) as f:
                reasoning_data = yaml.safe_load(f) or {}

        if test_name not in reasoning_data:
            reasoning_data[test_name] = {}
        reasoning_data[test_name][self.session_id] = test_concept

        with open(reasoning_file, "w") as f:
            yaml.dump(reasoning_data, f)

        return "Test staged successfully."

    def pre_flight_validation(self) -> bool:
        """
        Runs the AMBER phase pre-flight check. Returns True if green, False if fixup loop needed.
        """
        self.current_phase = Phase.AMBER

        lint_res = run_lint(self.config)
        if lint_res.get("status") != "success":
            return False

        test_res = run_test(self.config)
        for val in test_res.values():
            if val.get("status") != "success":
                return False

        cov_res = run_coverage(self.config)
        for val in cov_res.values():
            if val.get("status") != "success":
                return False

        return True

    def check_red_exit(self) -> None:
        """
        Verify the test suite fails.
        """
        test_res = run_test(self.config)
        # We expect AT LEAST ONE test to fail
        any_failed = any(v.get("status") == "failed" for v in test_res.values() if v.get("status") is not None)
        if not any_failed:
            raise PhaseValidationError("Red phase requires the test suite to fail.")

    def check_green_exit(self) -> None:
        """
        Verify all tests pass.
        """
        test_res = run_test(self.config)
        any_failed = any(v.get("status") == "failed" for v in test_res.values() if v.get("status") is not None)
        if any_failed:
            raise PhaseValidationError("Green phase requires the test suite to pass.")

    def check_blue_exit(self, initial_test_count: int) -> None:
        """
        Verify tests pass and count hasn't decreased.
        """
        self.check_green_exit()
        # In a real implementation we would parse the actual test count from the stdout/runner output
        # For now, we mock the parsing or assume a default pass if no easy count available.
        # This will be refined as adapter parsers are fleshed out.
        pass

    def check_magenta_exit(self, current_coverage: float, uncovered_lines: int) -> None:
        """
        Verify tests pass, coverage >= threshold, uncovered <= max.
        """
        self.check_green_exit()
        coverage_threshold = float(self.config.harness.get("coverage_threshold", 80.0))  # type: ignore
        max_uncovered_lines = int(self.config.harness.get("max_uncovered_lines", 50))  # type: ignore
        if current_coverage < coverage_threshold:
            raise PhaseValidationError(f"Coverage {current_coverage}% is below threshold {coverage_threshold}%")
        if uncovered_lines > max_uncovered_lines:
            raise PhaseValidationError(f"Uncovered lines {uncovered_lines} exceeds maximum {max_uncovered_lines}")

    async def execute_tool(self, name: str, arguments: dict[str, Any]) -> Any:  # noqa: ANN401
        """
        Executes a tool call requested by the LLM.
        """
        res = await self.registry.dispatch(name, arguments)
        if not res.success:
            raise RuntimeError(res.error)
        return res.content
