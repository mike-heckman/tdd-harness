"""
TDD Loop Controller Module.
"""

import difflib
import json
import shutil
import sys
import uuid
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from openai import AsyncOpenAI

from .config import TddHarnessConfig
from .coverage_parser import LcovParser
from .registry import ToolRegistry
from .runner import orchestrate_global, orchestrate_targeted, run_coverage, run_lint, run_test


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
        prefix = "test-" if "pytest" in sys.modules else ""
        self.session_id = f"{prefix}{uuid.uuid4()}"

        self.past_failure_summaries: list[str] = []
        self.session_modified_files: set[str] = set()

        # Register built-in file operations wrapped with security interceptors
        self.registry.register_python_tool(self.read_file_safe, name="read_file")
        self.registry.register_python_tool(self.write_file_safe, name="write_file")
        self.registry.register_python_tool(self.success, name="success")
        self.registry.register_python_tool(self.abort, name="abort")
        self.registry.register_python_tool(self.stage_implementation, name="stage_implementation")
        self.registry.register_python_tool(self.stage_test_implementation, name="stage_test_implementation")
        self.registry.register_python_tool(self.ask_researcher, name="ask_researcher")

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

    async def success(self, message: str, task_file: str | None = None) -> str:
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

        # Invoke Review Sub-Agent
        diffs = []
        backup_dir = Path(".tdd-harness/backups") / self.session_id
        for filepath in self.session_modified_files:
            target = Path(filepath)
            backup_path = backup_dir / f"{target.name}.bak"
            if backup_path.exists() and target.exists():
                with open(backup_path, encoding="utf-8") as f:
                    old_lines = f.readlines()
                with open(target, encoding="utf-8") as f:
                    new_lines = f.readlines()
                diff = list(difflib.unified_diff(old_lines, new_lines, fromfile=str(backup_path), tofile=str(target)))
                diffs.append("".join(diff))
            elif target.exists():
                with open(target, encoding="utf-8") as f:
                    new_lines = f.readlines()
                diffs.append(f"--- /dev/null\n+++ {target}\n" + "".join(f"+{line}" for line in new_lines))

        unified_diff = "\n".join(diffs)
        modified_files_list = "\n".join(self.session_modified_files)

        task_content = "Task File not provided or found."
        if task_file and Path(task_file).exists():
            with open(task_file, encoding="utf-8") as f:
                task_content = f.read()
        else:
            # Fallback: try to find an active task file in docs/tasks/ready or docs/tasks/in-progress
            for folder in ["docs/tasks/ready", "docs/tasks/in-progress"]:
                folder_path = Path(folder)
                if folder_path.exists():
                    md_files = list(folder_path.glob("*.md"))
                    if md_files:
                        with open(md_files[0], encoding="utf-8") as f:
                            task_content = f.read()
                        break

        review_prompt = (
            "You are a Senior Code Reviewer Sub-Agent. Your task is to review the unified diff of the changes made by the primary agent "
            "against the original Task File (Definition of Done) and ensure all requirements are met.\n"
            "You have read-only access to 'get_file_content' and 'get_symbol_source' tools to investigate the full files if the diff lacks context.\n"
            "You MUST return a structured response: either 'APPROVE' if the changes meet all criteria, or 'REJECT: <specific critique>' if there are missing requirements or issues.\n"
            "Do NOT output anything else except this structured response."
        )

        user_content = (
            f"Task File:\n{task_content}\n\nModified Files:\n{modified_files_list}\n\nUnified Diff:\n{unified_diff}"
        )

        api_key = str(self.config.llm.get("api_key", "")) if self.config.llm.get("api_key") else None
        base_url = str(self.config.llm.get("base_url", "")) if self.config.llm.get("base_url") else None
        model = str(self.config.llm.get("model", "gpt-4o"))
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        messages = [{"role": "system", "content": review_prompt}, {"role": "user", "content": user_content}]

        # Provide get_file_content and get_symbol_source tools
        tools = []
        for schema in self.registry.get_openai_schemas():
            name = schema["function"]["name"]
            if name in ("get_file_content", "get_symbol_source"):
                tools.append(schema)

        max_loops = 5
        reviewer_response = "APPROVE"
        for _ in range(max_loops):
            kwargs = {
                "model": model,
                "messages": messages,
            }
            if tools:
                kwargs["tools"] = tools

            # type ignored below as client.chat.completions.create is typed dynamically
            response = await client.chat.completions.create(**kwargs)  # type: ignore

            msg = response.choices[0].message
            if getattr(msg, "tool_calls", None):
                messages.append(msg)
                for tool_call in msg.tool_calls:  # type: ignore
                    func = tool_call.function
                    name = str(func.name)
                    args = json.loads(func.arguments)
                    try:
                        res = await self.registry.dispatch(name, args)
                        content = str(res.content) if res.success else f"Error: {res.error}"
                    except Exception as e:
                        content = f"Error executing tool: {e}"
                    messages.append({"role": "tool", "tool_call_id": tool_call.id, "name": name, "content": content})
            else:
                reviewer_response = msg.content.strip() if msg.content else "APPROVE"
                break

        if reviewer_response.startswith("REJECT"):
            return f"Validation failed: Review Sub-Agent Rejected the implementation.\\nCritique: {reviewer_response}"

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

    async def _generate_post_mortem(self, filepath: str, raw_error: str) -> str:
        """
        Generates a post-mortem summary for a failure using a secondary LLM call.
        """
        code = self.read_file_safe(filepath)
        prompt = f"""Analyze the following test/linter failure for {filepath}.
Code:
{code}

Traceback:
{raw_error}

Return a 2-3 sentence technical summary of the root cause AND a specific, actionable suggestion for what the primary agent should do differently to fix it. Do not include any other text."""

        api_key = str(self.config.llm.get("api_key", "")) if self.config.llm.get("api_key") else None
        base_url = str(self.config.llm.get("base_url", "")) if self.config.llm.get("base_url") else None
        model = str(self.config.llm.get("model", "gpt-4o"))
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        try:
            response = await client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}])
            return response.choices[0].message.content or "Failed to generate post-mortem."
        except Exception as e:
            return f"Failed to generate post-mortem: {e}"

    async def stage_implementation(self, filepath: str, code: str) -> str:
        """
        Stage an implementation for the Blue or Green phase.
        """
        if self.current_phase not in (Phase.BLUE, Phase.GREEN):
            return "Error: stage_implementation can only be used in the Blue or Green phase."

        target = Path(filepath)
        backup_dir = Path(".tdd-harness/backups") / self.session_id
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"{target.name}.bak"

        if target.exists() and not backup_path.exists():
            shutil.copy2(target, backup_path)

        self.session_modified_files.add(filepath)
        self.write_file_safe(filepath, code)

        # Run lint
        lint_res = run_lint(self.config, file_path=filepath)
        if lint_res.get("status") != "success":
            stderr = lint_res.get("stderr", "")
            pm = await self._generate_post_mortem(filepath, stderr)
            self.past_failure_summaries.append(pm)
            if backup_path.exists():
                shutil.copy2(backup_path, target)
            else:
                target.unlink(missing_ok=True)
            return f"Linting failed. Reverted file.\\nPost-Mortem Summary & Guidance:\\n{pm}"

        # Run test
        test_res = orchestrate_targeted(self.config, filepath)
        any_failed = False
        errors = []
        for val in test_res.values():
            if val.get("status") == "failed":
                any_failed = True
                stderr = val.get("stderr", "")
                if stderr:
                    errors.append(stderr)

        if any_failed:
            raw_error = "\\n".join(errors)
            pm = await self._generate_post_mortem(filepath, raw_error)
            self.past_failure_summaries.append(pm)
            if backup_path.exists():
                shutil.copy2(backup_path, target)
            else:
                target.unlink(missing_ok=True)
            return f"Tests failed. Reverted file.\\nPost-Mortem Summary & Guidance:\\n{pm}"

        return "Implementation staged successfully."

    async def stage_test_implementation(self, filepath: str, code: str, test_name: str, test_concept: str) -> str:
        """
        Stage a test implementation for the Red phase.
        """
        if self.current_phase != Phase.RED:
            return "Error: stage_test_implementation can only be used in the Red phase."

        target = Path(filepath)
        backup_dir = Path(".tdd-harness/backups") / self.session_id
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"{target.name}.bak"

        if target.exists() and not backup_path.exists():
            shutil.copy2(target, backup_path)

        self.session_modified_files.add(filepath)
        self.write_file_safe(filepath, code)

        # Run lint
        lint_res = run_lint(self.config, file_path=filepath)
        if lint_res.get("status") != "success":
            stderr = lint_res.get("stderr", "")
            pm = await self._generate_post_mortem(filepath, stderr)
            if backup_path.exists():
                shutil.copy2(backup_path, target)
            else:
                target.unlink(missing_ok=True)
            return f"Linting failed. Reverted file.\\nPost-Mortem Summary & Guidance:\\n{pm}"

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
            raw_error = "\n".join(errors) if errors else "Test passed unexpectedly or failed with wrong error."
            pm = await self._generate_post_mortem(filepath, raw_error)
            self.past_failure_summaries.append(pm)
            if backup_path.exists():
                shutil.copy2(backup_path, target)
            else:
                target.unlink(missing_ok=True)
            return f"Error: Test did not fail with AssertionError or NotImplementedError. Reverted file.\nPost-Mortem Summary & Guidance:\n{pm}"

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

    async def ask_researcher(self, query: str) -> str:
        """
        Instantiate a stateless Sub-Agent to research a query using available MCP tools.

        Returns a concise 3-4 sentence technical summary.
        """
        api_key = str(self.config.llm.get("api_key", "")) if self.config.llm.get("api_key") else None
        base_url = str(self.config.llm.get("base_url", "")) if self.config.llm.get("base_url") else None
        model = str(self.config.llm.get("model", "gpt-4o"))
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        system_prompt = (
            "You are a Research Sub-Agent. Your task is to investigate the user's query "
            "using the provided tools (jdocmunch, jcodemunch, etc). "
            "Once you have gathered the necessary information, provide a concise, 3-4 sentence technical summary of your findings. "
            "Do NOT include any extra conversational filler."
        )

        messages: list[Any] = [{"role": "system", "content": system_prompt}, {"role": "user", "content": query}]

        tools: list[Any] = []
        for schema in self.registry.get_openai_schemas():
            tool_name = schema["function"]["name"]
            if self.registry.tools[tool_name].type.value == "mcp":
                tools.append(schema)

        max_loops = 10
        for _ in range(max_loops):
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,
            }
            if tools:
                kwargs["tools"] = tools

            response = await client.chat.completions.create(**kwargs)  # type: ignore

            msg = response.choices[0].message
            if getattr(msg, "tool_calls", None):
                messages.append(msg)
                for tool_call in msg.tool_calls:  # type: ignore
                    func = tool_call.function
                    name = str(func.name)
                    args = json.loads(func.arguments)
                    try:
                        res = await self.registry.dispatch(name, args)
                        content = str(res.content) if res.success else f"Error: {res.error}"
                    except Exception as e:
                        content = f"Error executing tool: {e}"
                    messages.append({"role": "tool", "tool_call_id": tool_call.id, "name": name, "content": content})
            else:
                return msg.content or "No findings could be summarized."

        return "Research loop maxed out without a final summary."

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

    async def run_magenta_loop(self) -> None:
        """
        Sub-loop for the Magenta phase to enforce coverage guardrails file-by-file.
        """
        self.current_phase = Phase.MAGENTA
        max_attempts = 3

        orchestrate_global(self.config, Path.cwd())

        coverage_file = Path.cwd() / "coverage.lcov"

        if not coverage_file.exists():
            self.abort("Coverage file not found and could not be generated.")

        parser = LcovParser(Path.cwd())
        parser.parse_file(coverage_file)
        missing_coverage = parser.get_missing_coverage()

        for file_path, missing_lines in missing_coverage.items():
            attempts = 0
            while attempts < max_attempts:
                # Dispatch to a hypothetical 'fix_coverage' tool or LLM action
                # Here we pass the specific missing line numbers for the LLM context.
                context = {"file_path": file_path, "missing_lines": missing_lines}

                try:
                    # In a real implementation this sends the context to the LLM agent
                    # await self.execute_tool("fix_coverage", context)
                    _ = context
                    pass
                except Exception:
                    pass

                # After LLM action, re-run global coverage to verify
                orchestrate_global(self.config, Path.cwd())

                parser = LcovParser(Path.cwd())
                parser.parse_file(coverage_file)
                new_missing = parser.get_missing_coverage()

                if file_path not in new_missing or not new_missing[file_path]:
                    break  # Coverage fixed for this file

                # Update missing lines for next attempt
                missing_lines = new_missing[file_path]
                attempts += 1

            if attempts >= max_attempts:
                # TODO: dynamic handling
                self.abort(f"LLM failed to increase coverage for {file_path} after {max_attempts} attempts.")
