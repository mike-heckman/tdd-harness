"""
TDD Loop Controller Module.
"""

import difflib
import hashlib
import json
import logging
import shutil
from pathlib import Path
from typing import Any

import yaml

from .config import HarnessContext, TddHarnessConfig
from .context import Context, ContextBuilder, ContextType
from .coverage_parser import LcovParser
from .exceptions import HarnessAbort, PhaseValidationError
from .llm import LLMClient
from .models.tool import ToolCall, ToolCallResponse
from .phase import Phase
from .prompt import Prompt
from .registry import ToolRegistry
from .runner import orchestrate_global, orchestrate_targeted, run_lint, run_test, run_test_and_coverage
from .security import SecurityInterceptor
from .sub_agents import PostMortemSubAgent, ResearchSubAgent, ReviewSubAgent
from .task_loader import TaskLoader
from .tool_schemas import get_tools_for_phase
from .tracker import AntiThrashingTracker
from .utils import download_to_reference, install_dependencies, search_web

logger = logging.getLogger(__name__)


class TDDLoopController:
    """
    Manages the TDD Loop, State Transitions, and File Security.

    Design Pattern: Orchestrator / State Machine
    Responsibility: Coordinates state transitions between TDD phases and delegates
    execution to dedicated runner adapters and sub-agents, adhering to the Single
    Responsibility Principle.
    """

    def __init__(
        self,
        config: TddHarnessConfig,
        registry: ToolRegistry,
        llm_client: LLMClient,
        harness_ctx: HarnessContext,
        context_builder: ContextBuilder,
        security_interceptor: SecurityInterceptor | None = None,
        task_loader: TaskLoader | None = None,
    ):
        """
        Initialize the TDDLoopController.
        """
        self.config = config
        self.registry = registry

        at_config_raw = {}
        if hasattr(self.config, "harness") and isinstance(self.config.harness, dict):
            at_config_raw = self.config.harness.get("anti_thrashing", {})
        at_config: dict[str, Any] = at_config_raw if isinstance(at_config_raw, dict) else {}
        self.tracker = AntiThrashingTracker(**at_config)
        self.registry.tracker = self.tracker

        self._current_phase = Phase.AMBER

        self.harness_ctx = harness_ctx
        self.context_builder = context_builder
        self.session_id = self.harness_ctx.session_id

        self.past_failure_summaries: list[str] = []
        self.session_modified_files: set[str] = set()
        self._phase_successful = False
        self._initial_blue_test_count = 0

        self.llm_client = llm_client
        self.review_agent = ReviewSubAgent(self.llm_client)
        self.post_mortem_agent = PostMortemSubAgent(self.llm_client)
        self.research_agent = ResearchSubAgent(self.llm_client)
        self._post_mortem_cache: dict[str, str] = {}

        self.security_interceptor = security_interceptor or SecurityInterceptor(initial_phase=self._current_phase)
        self.task_loader = task_loader or TaskLoader(self.research_agent, self.registry)
        self.security_interceptor.current_phase = self._current_phase

        # Register built-in file operations wrapped with security interceptors
        self.registry.register_python_tool(self.security_interceptor.read_file_safe, name="read_file")
        self.registry.register_python_tool(self.security_interceptor.write_file_safe, name="write_file")
        self.registry.register_python_tool(self.success, name="success")
        self.registry.register_python_tool(self.abort, name="abort")
        self.registry.register_python_tool(self.stage_implementation, name="stage_implementation")
        self.registry.register_python_tool(self.stage_test_implementation, name="stage_test_implementation")
        self.registry.register_python_tool(self.ask_researcher, name="ask_researcher")
        self.registry.register_python_tool(install_dependencies, name="install_dependencies")
        self.registry.register_python_tool(search_web, name="search_web")
        self.registry.register_python_tool(download_to_reference, name="download_to_reference")

    @property
    def current_phase(self) -> Phase:
        """
        Get the current phase.
        """
        return self._current_phase

    @current_phase.setter
    def current_phase(self, phase: Phase) -> None:
        self._current_phase = phase
        self.security_interceptor.current_phase = phase

    def read_file_safe(self, path: str) -> str:
        """
        Read a file safely based on the current phase.
        """
        return self.security_interceptor.read_file_safe(path)

    def write_file_safe(self, path: str, content: str) -> str:
        """
        Write a file safely based on the current phase.
        """
        return self.security_interceptor.write_file_safe(path, content)

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
                self.check_blue_exit(getattr(self, "_initial_blue_test_count", 0))
            elif self.current_phase == Phase.MAGENTA:
                self.check_magenta_exit(100.0, 0)
        except PhaseValidationError as e:
            return f"Validation failed: {str(e)}"

        # Invoke Review Sub-Agent
        diffs = []
        backup_dir = self.harness_ctx.backup_dir
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

        reviewer_response = await self.review_agent.review(
            task_content, modified_files_list, unified_diff, self.registry
        )

        if reviewer_response.startswith("REJECT"):
            return f"Validation failed: Review Sub-Agent Rejected the implementation.\\nCritique: {reviewer_response}"

        report_dir = self.harness_ctx.reports_dir
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / f"success_report_{self.current_phase.name.lower()}_{self.session_id}.md"
        with open(report_file, "w") as f:
            f.write(f"Status: Success\\nMessage: {message}\\n")

        # Trigger MCP updates
        if self.current_phase in (Phase.RED, Phase.GREEN, Phase.BLUE, Phase.AMBER):
            try:
                await self.registry.dispatch("index_folder", {"path": "src"})
                await self.registry.dispatch("index_folder", {"path": "tests"})
            except ValueError:
                pass  # tool might not be loaded in mock tests

        self._phase_successful = True
        return "Phase completed successfully."

    def abort(self, reason: str) -> str:
        """
        Explicit escape hatch to pause the loop.
        """
        report_dir = self.harness_ctx.reports_dir
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / f"abort_report_{self.current_phase.name.lower()}_{self.session_id}.md"
        with open(report_file, "w") as f:
            f.write(f"Abort Reason: {reason}\\n")
        raise HarnessAbort(reason)

    async def _generate_post_mortem(self, filepath: str, raw_error: str) -> str:
        """
        Generates a post-mortem summary for a failure using a secondary LLM call.
        """
        cache_key = hashlib.sha256(f"{filepath}:{raw_error}".encode()).hexdigest()
        if cache_key in getattr(self, "_post_mortem_cache", {}):
            return self._post_mortem_cache[cache_key]

        code = self.read_file_safe(filepath)
        pm = await self.post_mortem_agent.generate(filepath, code, raw_error)

        if not hasattr(self, "_post_mortem_cache"):
            self._post_mortem_cache = {}
        self._post_mortem_cache[cache_key] = pm
        return pm

    async def stage_implementation(self, filepath: str, code: str) -> str:
        """
        Stage an implementation for the Blue or Green phase.
        """
        if self.current_phase not in (Phase.BLUE, Phase.GREEN):
            return "Error: stage_implementation can only be used in the Blue or Green phase."

        target = Path(filepath)
        backup_dir = self.harness_ctx.backup_dir
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"{target.name}.bak"

        if target.exists() and not backup_path.exists():
            shutil.copy2(target, backup_path)

        self.session_modified_files.add(filepath)
        self.write_file_safe(filepath, code)

        try:
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
        except Exception:
            if backup_path.exists():
                shutil.copy2(backup_path, target)
            else:
                target.unlink(missing_ok=True)
            raise

    async def stage_test_implementation(self, filepath: str, code: str, test_name: str, test_concept: str) -> str:
        """
        Stage a test implementation for the Red phase.
        """
        if self.current_phase != Phase.RED:
            return "Error: stage_test_implementation can only be used in the Red phase."

        target = Path(filepath)
        backup_dir = self.harness_ctx.backup_dir
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"{target.name}.bak"

        if target.exists() and not backup_path.exists():
            shutil.copy2(target, backup_path)

        self.session_modified_files.add(filepath)
        self.write_file_safe(filepath, code)

        try:
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
        except Exception:
            if backup_path.exists():
                shutil.copy2(backup_path, target)
            else:
                target.unlink(missing_ok=True)
            raise

        # Write reasoning
        reasoning_dir = self.harness_ctx.reasoning_dir
        reasoning_dir.mkdir(parents=True, exist_ok=True)
        reasoning_file = reasoning_dir / f"{target.name}.yaml"
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
        return await self.research_agent.ask(query, self.registry)

    def pre_flight_validation(self) -> bool:
        """
        Runs the AMBER phase pre-flight check. Returns True if green, False if fixup loop needed.
        """
        self.current_phase = Phase.AMBER

        lint_res = run_lint(self.config)
        if lint_res.get("status") != "success":
            return False

        res = run_test_and_coverage(self.config)
        for key, val in res.items():
            if key.startswith("test_") and val.get("status") != "success":
                return False
            if key.startswith("cov_") and val.get("status") != "success":
                return False

        if not self.task_loader.process_ready_tasks():
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

    def _get_test_count(self) -> int:
        """
        Helper to parse the pytest report log and return the test count.

        Returns:
            The number of tests executed as an integer.
        """
        report_log_path = self.harness_ctx.reports_dir / "pytest-report.jsonl"
        count = 0
        if report_log_path.exists():
            with open(report_log_path, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                        if record.get("$report_type") == "TestReport" and record.get("when") == "call":
                            count += 1
                    except json.JSONDecodeError:
                        continue
        return count

    def check_blue_exit(self, initial_test_count: int) -> None:
        """
        Verify tests pass and count hasn't decreased.
        """
        self.check_green_exit()
        current_test_count = self._get_test_count()
        if current_test_count < initial_test_count:
            raise PhaseValidationError(f"Test count decreased from {initial_test_count} to {current_test_count}.")

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
        tool_call = ToolCall(tool_name=name, arguments=arguments)

        try:
            res = await self.registry.dispatch(name, arguments)
        except Exception as e:
            tool_response = ToolCallResponse(success=False, output=str(e))
            self.tracker.record_tool_call(tool_call, tool_response)
            if self.tracker.should_abort():
                self.abort("Anti-thrashing limits exceeded.")
            raise e

        tool_response = ToolCallResponse(
            success=res.success, output=str(res.content) if res.content is not None else str(res.error)
        )
        self.tracker.record_tool_call(tool_call, tool_response)

        if self.tracker.should_abort():
            self.abort("Anti-thrashing limits exceeded.")

        if not res.success:
            raise RuntimeError(res.error)
        return res.content

    async def run_blue_phase(self, task_file: Path) -> None:
        """
        Orchestrates the Blue (Structural Blueprint) phase end-to-end.
        """
        self.current_phase = Phase.BLUE
        self._phase_successful = False

        # 1. Capture initial test count
        run_test(self.config)
        self._initial_blue_test_count = self._get_test_count()

        # 2. Assemble Context
        task_content = task_file.read_text(encoding="utf-8")
        if "---" in task_content:
            parts = task_content.split("---", 2)
            frontmatter = yaml.safe_load(parts[1])
            context_text = parts[2].strip()
        else:
            frontmatter = {}
            context_text = task_content

        success_criteria = frontmatter.get("success_criteria", [])

        cb = self.context_builder
        cb.clear()

        # Add phase instructions
        try:
            phase_prompt = Prompt("blue_phase_prompt").get_system_message()
            cb.add_context(phase_prompt)
        except FileNotFoundError:
            logger.warning("No prompt found for blue phase.")

        cb.add_context(
            Context(text=f"<task_context>\n{context_text}\n</task_context>", context_type=ContextType.TASK_CONTEXT)
        )
        for criteria in success_criteria:
            cb.add_context(Context(text=f"<criteria>\n{criteria}\n</criteria>", context_type=ContextType.TASK_CRITERIA))

        target_files = frontmatter.get("target_files", [])
        for file in target_files:
            file_path = Path(file)
            if file_path.exists():
                source = self.read_file_safe(str(file_path))
                cb.add_context(
                    Context(
                        text=f'<file name="{file}">\n```python\n{source}\n```\n</file>',
                        context_type=ContextType.FILE_SOURCE,
                    )
                )

        tools = get_tools_for_phase(self.current_phase.value)

        self.tracker.reset()

        # 3. Tool-call loop
        self._blue_loop_active = True
        while self._blue_loop_active:
            await self.llm_client.chat(contexts=[], tools=tools, registry=self.registry)

            if self._phase_successful:
                self._blue_loop_active = False
                break

            if self.tracker.should_abort():
                self.abort("Anti-thrashing limits exceeded.")

    async def run_red_phase(self, task_file: Path) -> None:
        """
        Orchestrates the Red (Test Generation) phase end-to-end.
        """
        self.current_phase = Phase.RED
        self._phase_successful = False

        # Assemble Context
        task_content = task_file.read_text(encoding="utf-8")
        if "---" in task_content:
            parts = task_content.split("---", 2)
            frontmatter = yaml.safe_load(parts[1])
            context_text = parts[2].strip()
        else:
            frontmatter = {}
            context_text = task_content

        success_criteria = frontmatter.get("success_criteria", [])

        cb = self.context_builder
        cb.clear()

        # Add phase instructions
        try:
            phase_prompt = Prompt("red_phase_prompt").get_system_message()
            cb.add_context(phase_prompt)
        except FileNotFoundError:
            logger.warning("No prompt found for red phase.")

        cb.add_context(
            Context(text=f"<task_context>\n{context_text}\n</task_context>", context_type=ContextType.TASK_CONTEXT)
        )
        for criteria in success_criteria:
            cb.add_context(Context(text=f"<criteria>\n{criteria}\n</criteria>", context_type=ContextType.TASK_CRITERIA))

        target_files = frontmatter.get("target_files", [])
        for file in target_files:
            file_path = Path(file)
            if file_path.exists():
                source = self.read_file_safe(str(file_path))
                cb.add_context(
                    Context(
                        text=f'<file name="{file}">\n```python\n{source}\n```\n</file>',
                        context_type=ContextType.FILE_SOURCE,
                    )
                )

        tools = get_tools_for_phase(self.current_phase.value)

        self.tracker.reset()
        self.past_failure_summaries.clear()

        # Tool-call loop
        self._red_loop_active = True
        last_failure_count = 0
        while self._red_loop_active:
            # Inject new post-mortem summaries if any
            if len(self.past_failure_summaries) > last_failure_count:
                for pm in self.past_failure_summaries[last_failure_count:]:
                    cb.add_context(
                        Context(text=f"Post-Mortem Guidance:\n{pm}", context_type=ContextType.POST_MORTEM_SUMMARY)
                    )
                last_failure_count = len(self.past_failure_summaries)

            await self.llm_client.chat(contexts=[], tools=tools, registry=self.registry)

            if self._phase_successful:
                self._red_loop_active = False
                break

            if self.tracker.should_abort():
                self.abort("Anti-thrashing limits exceeded.")

    async def run_green_phase(self, task_file: Path) -> None:
        """
        Orchestrates the Green (Develop Implementation) phase end-to-end.
        """
        self.current_phase = Phase.GREEN
        self._phase_successful = False

        # Assemble Context
        task_content = task_file.read_text(encoding="utf-8")
        if "---" in task_content:
            parts = task_content.split("---", 2)
            frontmatter = yaml.safe_load(parts[1])
            context_text = parts[2].strip()
        else:
            frontmatter = {}
            context_text = task_content

        success_criteria = frontmatter.get("success_criteria", [])

        cb = self.context_builder
        cb.clear()

        # Add phase instructions
        try:
            phase_prompt = Prompt("green_phase_prompt").get_system_message()
            cb.add_context(phase_prompt)
        except FileNotFoundError:
            logger.warning("No prompt found for green phase.")

        cb.add_context(
            Context(text=f"<task_context>\n{context_text}\n</task_context>", context_type=ContextType.TASK_CONTEXT)
        )
        for criteria in success_criteria:
            cb.add_context(Context(text=f"<criteria>\n{criteria}\n</criteria>", context_type=ContextType.TASK_CRITERIA))

        target_files = frontmatter.get("target_files", [])
        for file in target_files:
            file_path = Path(file)
            if file_path.exists():
                source = self.read_file_safe(str(file_path))
                cb.add_context(
                    Context(
                        text=f'<file name="{file}">\n```python\n{source}\n```\n</file>',
                        context_type=ContextType.FILE_SOURCE,
                    )
                )

        # Load Test Concepts
        reasoning_dir = self.harness_ctx.reasoning_dir
        if reasoning_dir.exists():
            reasoning_files = list(reasoning_dir.glob("*.yaml"))
        else:
            reasoning_files = []
        for r_file in reasoning_files:
            try:
                with open(r_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                    for test_name, sessions in data.items():
                        for _sess_id, concept in sessions.items():
                            if _sess_id == self.session_id:
                                cb.add_context(
                                    Context(
                                        text=f"Test Concept ({test_name}): {concept}",
                                        context_type=ContextType.TEST_CONCEPTS,
                                    )
                                )
            except Exception as e:
                logger.warning(f"Failed to load reasoning file {r_file}: {e}")

        tools = get_tools_for_phase(self.current_phase.value)

        self.tracker.reset()
        self.past_failure_summaries.clear()

        # Tool-call loop
        self._green_loop_active = True
        last_failure_count = 0
        while self._green_loop_active:
            # Inject new post-mortem summaries if any
            if len(self.past_failure_summaries) > last_failure_count:
                for pm in self.past_failure_summaries[last_failure_count:]:
                    cb.add_context(
                        Context(text=f"Post-Mortem Guidance:\n{pm}", context_type=ContextType.POST_MORTEM_SUMMARY)
                    )
                last_failure_count = len(self.past_failure_summaries)

            await self.llm_client.chat(contexts=[], tools=tools, registry=self.registry)

            if self._phase_successful:
                self._green_loop_active = False
                break

            if self.tracker.should_abort():
                self.abort("Anti-thrashing limits exceeded.")

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
                total_lines = sum(len(stats.get("lines", {})) for stats in parser.file_stats.values())
                covered_lines = sum(
                    sum(1 for hits in stats.get("lines", {}).values() if hits > 0)
                    for stats in parser.file_stats.values()
                )
                total_missing = sum(len(m) for m in missing_coverage.values())

                current_coverage = (covered_lines / total_lines * 100) if total_lines > 0 else 100.0

                try:
                    self.check_magenta_exit(current_coverage, total_missing)
                    break
                except PhaseValidationError:
                    pass

                cb = self.context_builder
                cb.clear()

                try:
                    phase_prompt = Prompt("magenta_phase_prompt").get_system_message()
                    cb.add_context(phase_prompt)
                except FileNotFoundError:
                    logger.warning("No prompt found for magenta phase.")

                context_text = f"File: {file_path} is missing test coverage for lines: {missing_lines}. Please write additional tests to cover these lines."
                cb.add_context(Context(text=context_text, context_type=ContextType.TASK_CONTEXT))

                source = self.read_file_safe(file_path)
                cb.add_context(
                    Context(text=f"File: {file_path}\n```python\n{source}\n```", context_type=ContextType.FILE_SOURCE)
                )

                tools = get_tools_for_phase(self.current_phase.value)

                self.tracker.reset()
                self.past_failure_summaries.clear()
                self._phase_successful = False

                self._magenta_loop_active = True
                last_failure_count = 0
                while self._magenta_loop_active:
                    if len(self.past_failure_summaries) > last_failure_count:
                        for pm in self.past_failure_summaries[last_failure_count:]:
                            cb.add_context(
                                Context(
                                    text=f"Post-Mortem Guidance:\n{pm}", context_type=ContextType.POST_MORTEM_SUMMARY
                                )
                            )
                        last_failure_count = len(self.past_failure_summaries)

                    await self.llm_client.chat(contexts=[], tools=tools, registry=self.registry)

                    if self._phase_successful:
                        self._magenta_loop_active = False
                        break

                    if self.tracker.should_abort():
                        self.abort("Anti-thrashing limits exceeded.")

                # After LLM action, re-run global coverage to verify
                orchestrate_global(self.config, Path.cwd())

                parser = LcovParser(Path.cwd())
                parser.parse_file(coverage_file)
                new_missing = parser.get_missing_coverage()
                missing_coverage = new_missing

                if file_path not in new_missing or not new_missing[file_path]:
                    break  # Coverage fixed for this file

                # Update missing lines for next attempt
                missing_lines = new_missing[file_path]
                attempts += 1

            if attempts >= max_attempts:
                report_dir = self.harness_ctx.reports_dir
                report_dir.mkdir(parents=True, exist_ok=True)
                report_file = report_dir / f"abort_report_{self.current_phase.name.lower()}_{self.session_id}.md"
                with open(report_file, "w") as f:
                    f.write(
                        f"Abort Reason: LLM failed to increase coverage for {file_path} after {max_attempts} attempts.\\n"
                    )
                self.abort(f"LLM failed to increase coverage for {file_path} after {max_attempts} attempts.")
