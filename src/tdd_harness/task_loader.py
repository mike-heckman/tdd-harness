"""
Task loading and provisioning module for TDD harness.
"""

import asyncio
import shutil
from pathlib import Path
from typing import Any

import yaml

from .exceptions import PhaseValidationError
from .utils import install_dependencies


class TaskLoader:
    """
    Handles parsing and provisioning of task files.
    """

    def __init__(self, research_agent: Any, registry: Any):  # noqa: ANN401
        """
        Initialize the task loader.
        """
        self.research_agent = research_agent
        self.registry = registry

    def process_ready_tasks(self) -> bool:
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
                self.validate_and_provision_task(task_path)
            except PhaseValidationError as e:
                error_dir.mkdir(parents=True, exist_ok=True)
                dest = error_dir / task_path.name
                shutil.move(task_path, dest)
                with open(error_dir / f"{task_path.stem}.error.log", "w", encoding="utf-8") as f:
                    f.write(str(e))
                return False

        return True

    def validate_and_provision_task(self, task_path: Path) -> None:
        """
        Validates and provisions a task file.
        """
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
                res = install_dependencies(all_deps)
                if "Failed" in res:
                    raise PhaseValidationError(res)

                # Setup a short asyncio loop to run the subagent if not running
                async def run_cyan():
                    # We group all libraries into one prompt
                    libs_str = ", ".join(all_deps)
                    prompt = f"Please search the web for external reference documentation for the following libraries: {libs_str}. Then, use download_to_reference to securely store them in ./docs/reference/<library_name>/."
                    await self.research_agent.ask(prompt, self.registry)
                    try:
                        await self.registry.dispatch("index_folder", {"path": "docs/reference"})
                    except Exception:
                        pass

                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(run_cyan())
                except RuntimeError:
                    asyncio.run(run_cyan())
