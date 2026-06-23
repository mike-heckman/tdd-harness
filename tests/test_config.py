"""Tests for the config module."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import yaml

from src.tdd_harness.config import (
    ConfigResolver,
    PromptConfig,
    TddHarnessConfig,
    load_prompt_config,
    load_tdd_harness_config,
)


def test_resolve_config_directory_fallbacks():
    """Test that config directory resolution works with fallbacks."""
    # Test current working directory fallback
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        config_dir = tmp_path / ".tdd-harness"
        config_dir.mkdir()

        with patch("src.tdd_harness.config.Path.cwd") as mock_cwd:
            mock_cwd.return_value = tmp_path
            resolver = ConfigResolver()
            resolved = resolver.resolve()
            assert resolved == config_dir


def test_load_tdd_harness_config():
    """Test loading of tdd-harness configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        config_dir = tmp_path / ".tdd-harness"
        config_dir.mkdir()

        # Create a sample config file
        config_file = config_dir / "config.yaml"
        config_data = {
            "llm": {
                "provider": "openai",
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-4",
                "context_size": 8192,
                "minimum_available_context": 512,
                "keep_turns": 5,
            },
            "harness": {
                "commands": {
                    "lint": "./scripts/lint.sh",
                    "test": "./scripts/test.sh",
                    "coverage": "./scripts/coverage.sh",
                },
                "coverage_threshold": 0.8,
                "max_uncovered_lines": 10,
            },
            "mcp_servers": [],
            "extensions": [],
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = load_tdd_harness_config(config_dir)
        assert isinstance(config, TddHarnessConfig)
        assert config.llm["provider"] == "openai"
        assert config.harness["coverage_threshold"] == 0.8


def test_load_prompt_config():
    """Test loading of prompt configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        config_dir = tmp_path / ".tdd-harness"
        prompts_dir = config_dir / "prompts"
        prompts_dir.mkdir(parents=True)

        # Create a sample prompt file
        prompt_file = prompts_dir / "system_message.yaml"
        prompt_data = {"prompt": "You are a helpful AI assistant."}

        with open(prompt_file, "w") as f:
            yaml.dump(prompt_data, f)

        prompt_config = load_prompt_config("system_message", project_dir=tmp_path)
        assert isinstance(prompt_config, PromptConfig)
        assert prompt_config.prompt == "You are a helpful AI assistant."


def test_config_resolver_isolated_state():
    """Test that two ConfigResolver instances do not share cache state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        config_dir = tmp_path / ".tdd-harness"
        config_dir.mkdir()

        with patch("src.tdd_harness.config.Path.cwd") as mock_cwd:
            mock_cwd.return_value = tmp_path

            resolver_a = ConfigResolver()
            resolver_b = ConfigResolver()

            # Resolve with a to populate its cache
            resolved_a = resolver_a.resolve()
            assert resolved_a == config_dir
            assert len(resolver_a._cache) == 1

            # b should have empty cache
            assert len(resolver_b._cache) == 0
