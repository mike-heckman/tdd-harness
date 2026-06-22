"""
Configuration loader and validator for tdd-harness.
"""

import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml
from pydantic import BaseModel, Field


class ToolConfigFile(BaseModel):
    """
    Configuration model for a tool definition file.
    """

    config: dict[str, object] = Field(default_factory=lambda: {"restart_policy": "exit"})
    tools: dict[str, list[str]] = Field(default_factory=dict)


class TddHarnessConfig(BaseModel):
    """
    Configuration model for tdd-harness.
    """

    llm: dict[str, object] = Field(default_factory=dict)
    harness: dict[str, object] = Field(default_factory=dict)
    mcp_servers: list[dict[str, object]] = Field(default_factory=list)
    extensions: list[dict[str, object]] = Field(default_factory=list)
    tool_configs: dict[str, ToolConfigFile] = Field(default_factory=dict)


class PromptConfig(BaseModel):
    """
    Configuration model for prompt files.
    """

    prompt: str


class HarnessContext:
    """
    Singleton for managing project context and temporary directory paths.
    """

    _instance = None
    session_id: str
    project_dir: Path

    def __new__(cls, *args: Any, **kwargs: Any) -> "HarnessContext":
        """
        Create or return the singleton instance.
        """
        if not cls._instance:
            cls._instance = super().__new__(cls)
            prefix = "test-" if "pytest" in sys.modules else ""
            cls._instance.session_id = f"{prefix}{uuid4()}"
            cls._instance.project_dir = Path.cwd()
        return cls._instance

    @property
    def backup_dir(self) -> Path:
        """
        Return the session backup directory.
        """
        return self.project_dir / ".tdd-harness" / self.session_id / "backups"

    @property
    def reasoning_dir(self) -> Path:
        """
        Return the session reasoning directory.
        """
        return self.project_dir / ".tdd-harness" / self.session_id / "reasoning"

    @property
    def reports_dir(self) -> Path:
        """
        Return the session reports directory.
        """
        return self.project_dir / ".tdd-harness" / self.session_id / "reports"


CACHE_TDD_DIRECTORIES: list[Path] = []


def build_cache_tdd_directories(project_dir: str | Path | None = None, force: bool = False) -> list[Path]:
    """
    Build a cached list of .tdd-harness directories to search for configuration files.
    """
    global CACHE_TDD_DIRECTORIES

    if CACHE_TDD_DIRECTORIES:
        if force:
            CACHE_TDD_DIRECTORIES.clear()
        else:
            return CACHE_TDD_DIRECTORIES

    if project_dir:
        config_dir = Path(project_dir) / ".tdd-harness"
        if config_dir.exists():
            CACHE_TDD_DIRECTORIES.append(config_dir)

    # Fallback to current working directory
    cwd_config = Path.cwd() / ".tdd-harness"
    if cwd_config.exists() and cwd_config not in CACHE_TDD_DIRECTORIES:
        CACHE_TDD_DIRECTORIES.append(cwd_config)

    # Fallback to user home directory
    home_config = Path.home() / ".tdd-harness"
    if home_config.exists() and home_config not in CACHE_TDD_DIRECTORIES:
        CACHE_TDD_DIRECTORIES.append(home_config)

    if CACHE_TDD_DIRECTORIES:
        return CACHE_TDD_DIRECTORIES

    raise FileNotFoundError("No .tdd-harness directory found in any fallback location.")


def resolve_config_directory(project_dir: str | None = None) -> Path:
    """
    Resolve the path to the .tdd-harness directory with fallbacks.
    """
    return build_cache_tdd_directories(project_dir)[0]


def load_tdd_harness_config(config_dir: Path) -> TddHarnessConfig:
    """
    Load the main tdd-harness configuration.
    """
    config_file = config_dir / "config.yaml"
    if not config_file.exists():
        raise FileNotFoundError(f"Config file {config_file} not found.")

    with open(config_file) as f:
        config_data = yaml.safe_load(f) or {}

    tool_configs = {}
    tools_dir = config_dir / "tools"
    if tools_dir.exists() and tools_dir.is_dir():
        for tool_file in tools_dir.glob("*.yaml"):
            with open(tool_file) as tf:
                tool_data = yaml.safe_load(tf) or {}
                if "config" not in tool_data:
                    tool_data["config"] = {"restart_policy": "exit"}
                elif "restart_policy" not in tool_data["config"]:
                    tool_data["config"]["restart_policy"] = "exit"
                tool_configs[tool_file.stem] = tool_data

    config_data["tool_configs"] = tool_configs
    return TddHarnessConfig(**config_data)


def load_prompt_config(prompt_name: str, project_dir: str | Path | None = None) -> PromptConfig:
    """
    Load a specific prompt configuration by checking resolution fallbacks.
    """
    prompt_file = None
    for config_dir in build_cache_tdd_directories(project_dir):
        candidate = config_dir / "prompts" / f"{prompt_name}.yaml"
        if candidate.exists():
            prompt_file = candidate
            break

    if not prompt_file:
        raise FileNotFoundError(f"Prompt file {prompt_name}.yaml not found in any fallback location.")

    with open(prompt_file) as f:
        prompt_data = yaml.safe_load(f)

    return PromptConfig(**prompt_data)
