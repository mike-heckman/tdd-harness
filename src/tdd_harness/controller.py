"""
TDD Loop Controller Module.
"""

import asyncio
import difflib
import hashlib
import json
import logging
import shutil
import subprocess
import sys
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from .config import HarnessContext, TddHarnessConfig
from .context import Context, ContextBuilder, ContextType
from .coverage_parser import LcovParser
from .llm import LLMClient
from .models.tool import ToolCall, ToolCallResponse
from .prompt import Prompt
from .registry import ToolRegistry
from .runner import orchestrate_global, orchestrate_targeted, run_lint, run_test, run_test_and_coverage
from .sub_agents import PostMortemSubAgent, ResearchSubAgent, ReviewSubAgent
from .tool_schemas import get_tools_for_phase
from .tracker import AntiThrashingTracker

logger = logging.getLogger(__name__)


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

    Design Pattern: Orchestrator / State Machine
    Responsibility: Coordinates state transitions between TDD phases and delegates
    execution to dedicated runner adapters and sub-agents, adhering to the Single
    Responsibility Principle.
    """

    def __init__(self, config: TddHarnessConfig, registry: ToolRegistry, llm_client: LLMClient):
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

        self.current_phase = Phase.AMBER
        self.harness_ctx = HarnessContext()
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

        # Register built-in file operations wrapped with security interceptors
        self.registry.register_python_tool(self.read_file_safe, name="read_file")
        self.registry.register_python_tool(self.write_file_safe, name="write_file")
        self.registry.register_python_tool(self.success, name="success")
        self.registry.register_python_tool(self.abort, name="abort")
        self.registry.register_python_tool(self.stage_implementation, name="stage_implementation")
        self.registry.register_python_tool(self.stage_test_implementation, name="stage_test_implementation")
        self.registry.register_python_tool(self.ask_researcher, name="ask_researcher")
        self.registry.register_python_tool(self.install_dependencies, name="install_dependencies")
        self.registry.register_python_tool(self.search_web, name="search_web")
        self.registry.register_python_tool(self.download_to_reference, name="download_to_reference")

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
            p0 = parts[0].lower()
            if p0 in (".tdd-harness", ".git"):
                return False
            if len(parts) >= 2 and p0 == "src" and parts[1].lower() == "tdd_harness":
                return False

        # Phase-specific Write constraints
        if is_write and parts:
            p0 = parts[0].lower()
            if self.current_phase in (Phase.AMBER, Phase.BLUE, Phase.GREEN):
                # src/: rw, test/: ro
                if p0 == "tests":
                    return False
            elif self.current_phase in (Phase.RED, Phase.MAGENTA):
                # src/: ro, test/: rw
                if p0 == "src":
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
        sys.exit(1)

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

        if not self._process_ready_tasks():
            return False

        return True

    def install_dependencies(self, packages: list[str]) -> str:
        """
        Installs the missing dependencies into the virtual environment.
        """
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", *packages])
            return f"Successfully installed: {', '.join(packages)}"
        except subprocess.CalledProcessError as e:
            return f"Failed to install dependencies: {e}"

    def search_web(self, query: str) -> str:
        """
        Searches the web using duckduckgo-search.
        """
        try:
            from duckduckgo_search import DDGS  # type: ignore

            results = DDGS().text(query, max_results=5)
            if results:
                return "\\n".join([f"- [{r['title']}]({r['href']})" for r in results])
            return "No results found."
        except ImportError:
            return "duckduckgo-search not installed"

    def download_to_reference(self, url: str, library_name: str, filename: str) -> str:
        """
        Downloads a webpage, converts to markdown, and saves to docs/reference/{library_name}/{filename}.md.
        """
        try:
            import requests  # type: ignore
            from bs4 import BeautifulSoup  # type: ignore
            from markdownify import markdownify  # type: ignore

            resp = requests.get(url, timeout=10)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.content, "html.parser")
            md = markdownify(str(soup), heading_style="ATX")

            target_dir = Path("docs") / "reference" / library_name
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / f"{filename}.md"
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(md)
            return f"Successfully saved to {target_path}"
        except ImportError:
            return "Missing requests, beautifulsoup4, or markdownify"
        except Exception as e:
            return f"Error downloading: {e}"

    def _process_ready_tasks(self) -> bool:
        """
        Validates tasks in docs/tasks/ready/ asciibetically.
        """
        ready_dir = Path("docs/tasks/ready")
        error_dir = Path("docs/tasks/error")
        if not ready_dir.exists():
            return True

        tasks = sorted(ready_dir.glob("*.md"))
        for task_path in tasks:
            try:
                self._validate_and_provision_task(task_path)
            except PhaseValidationError as e:
                error_dir.mkdir(parents=True, exist_ok=True)
                dest = error_dir / task_path.name
                shutil.move(task_path, dest)
                with open(error_dir / f"{task_path.stem}.error.log", "w", encoding="utf-8") as f:
                    f.write(str(e))
                return False

        return True

    def _validate_and_provision_task(self, task_path: Path) -> None:
        content = task_path.read_text(encoding="utf-8")
        if not content.startswith("---"):
            raise PhaseValidationError("Missing YAML frontmatter.")

        parts = content.split("---", 2)
        if len(parts) < 3:
            raise PhaseValidationError("Invalid YAML frontmatter format.")

        try:
            frontmatter = yaml.safe_load(parts[1])
        except yaml.YAMLError as e:
            raise PhaseValidationError(f"Invalid YAML parsing: {e}") from e

        if not isinstance(frontmatter, dict):
            raise PhaseValidationError("YAML frontmatter must be a dictionary.")

        for field in ["id", "title", "success_criteria"]:
            if field not in frontmatter:
                raise PhaseValidationError(f"Missing required field in frontmatter: {field}")

        if not isinstance(frontmatter.get("success_criteria"), list):
            raise PhaseValidationError("success_criteria must be a list.")

        if "## Context" not in parts[2]:
            raise PhaseValidationError("Missing '## Context' Markdown header.")

        deps_block = frontmatter.get("dependencies", {})
        if isinstance(deps_block, dict):
            all_deps = deps_block.get("prod", []) + deps_block.get("dev", [])
            if all_deps:
                res = self.install_dependencies(all_deps)
                if "Failed" in res:
                    raise PhaseValidationError(res)

                # Setup a short asyncio loop to run the subagent if not running
                async def run_cyan():
                    # We group all libraries into one prompt
                    libs_str = ", ".join(all_deps)
                    prompt = f"Please search the web for external reference documentation for the following libraries: {libs_str}. Then, use download_to_reference to securely store them in ./docs/reference/<library_name>/."
                    await self.ask_researcher(prompt)
                    try:
                        await self.registry.dispatch("index_folder", {"path": "docs/reference"})
                    except Exception:
                        pass

                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(run_cyan())
                except RuntimeError:
                    asyncio.run(run_cyan())

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

        cb = ContextBuilder()
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

        cb = ContextBuilder()
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

        cb = ContextBuilder()
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

                cb = ContextBuilder()
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
