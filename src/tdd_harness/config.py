"""
Configuration loader and validator for tdd-harness.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class TddHarnessConfig(BaseModel):
    """
    Configuration model for tdd-harness.
    """

    llm: dict[str, object] = Field(default_factory=dict)
    harness: dict[str, object] = Field(default_factory=dict)
    mcp_servers: list[dict[str, object]] = Field(default_factory=list)
    extensions: list[dict[str, object]] = Field(default_factory=list)


class PromptConfig(BaseModel):
    """
    Configuration model for prompt files.
    """

    prompt: str


def resolve_config_directory(project_dir: str | None = None) -> Path:
    """
    Resolve the path to the .tdd-harness directory with fallbacks.
    """
    if project_dir:
        config_dir = Path(project_dir) / ".tdd-harness"
        if config_dir.exists():
            return config_dir

    # Fallback to current working directory
    cwd_config = Path.cwd() / ".tdd-harness"
    if cwd_config.exists():
        return cwd_config

    # Fallback to user home directory
    home_config = Path.home() / ".tdd-harness"
    if home_config.exists():
        return home_config

    raise FileNotFoundError("No .tdd-harness directory found in any fallback location.")


def load_tdd_harness_config(config_dir: Path) -> TddHarnessConfig:
    """
    Load the main tdd-harness configuration.
    """
    config_file = config_dir / "config.yaml"
    if not config_file.exists():
        raise FileNotFoundError(f"Config file {config_file} not found.")

    with open(config_file) as f:
        config_data = yaml.safe_load(f)

    return TddHarnessConfig(**config_data)


def load_prompt_config(config_dir: Path, prompt_name: str) -> PromptConfig:
    """
    Load a specific prompt configuration.
    """
    prompt_file = config_dir / "prompts" / f"{prompt_name}.yaml"
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file {prompt_file} not found.")

    with open(prompt_file) as f:
        prompt_data = yaml.safe_load(f)

    return PromptConfig(**prompt_data)
