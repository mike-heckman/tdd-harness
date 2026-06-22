"""
Unit tests for the Prompt class.
"""

import hashlib
from pathlib import Path

import pytest
import yaml

from src.tdd_harness.context import ContextType
from src.tdd_harness.prompt import Prompt


@pytest.fixture
def mock_config_dir(tmp_path: Path) -> Path:
    """Fixture to set up a dummy .tdd-harness config directory with a test prompt."""
    config_dir = tmp_path / ".tdd-harness"
    config_dir.mkdir()
    prompts_dir = config_dir / "prompts"
    prompts_dir.mkdir()

    # Write a dummy prompt
    prompt_file = prompts_dir / "test_prompt.yaml"
    prompt_file.write_text("prompt: |-\n  This is a test prompt.\n")
    return config_dir


@pytest.fixture
def mock_project_dir(tmp_path: Path) -> Path:
    """Fixture to set up the project directory."""
    return tmp_path


def test_prompt_initialization_computes_hash(mock_project_dir: Path, mock_config_dir: Path) -> None:
    """Test that initializing a Prompt computes the correct SHA256 hash."""
    prompt = Prompt("test_prompt", project_dir=mock_project_dir)
    expected_hash = hashlib.sha256(b"This is a test prompt.").hexdigest()

    assert prompt.prompt_text == "This is a test prompt."
    assert prompt.prompt_hash == expected_hash


def test_prompt_cache_creation(mock_project_dir: Path, mock_config_dir: Path) -> None:
    """Test that a new Prompt creates the .prompt-cache.yaml file with the correct structure."""
    prompt = Prompt("test_prompt", project_dir=mock_project_dir)

    cache_file = mock_project_dir / ".prompt-cache.yaml"
    assert cache_file.exists()

    with open(cache_file) as f:
        cache_data = yaml.safe_load(f)

    assert "prompt_caches" in cache_data
    assert "test_prompt" in cache_data["prompt_caches"]
    assert cache_data["prompt_caches"]["test_prompt"]["prompt_hash"] == prompt.prompt_hash
    assert cache_data["prompt_caches"]["test_prompt"]["token_counts"] == {}


def test_prompt_cache_hit_preserves_tokens(mock_project_dir: Path, mock_config_dir: Path) -> None:
    """Test that initializing a Prompt with an existing, valid cache preserves token counts."""
    # First init creates the cache
    prompt = Prompt("test_prompt", project_dir=mock_project_dir)
    prompt.update_token_size("test-model", 42)

    # Second init should read the cache and keep the token counts
    prompt2 = Prompt("test_prompt", project_dir=mock_project_dir)
    assert prompt2.token_size("test-model") == 42


def test_prompt_hash_invalidation_clears_tokens(mock_project_dir: Path, mock_config_dir: Path) -> None:
    """Test that changing the prompt text invalidates the hash and clears token counts."""
    # First init creates the cache
    prompt = Prompt("test_prompt", project_dir=mock_project_dir)
    prompt.update_token_size("test-model", 42)

    # Change the prompt text
    prompt_file = mock_config_dir / "prompts" / "test_prompt.yaml"
    prompt_file.write_text("prompt: |-\n  This is a CHANGED prompt.\n")

    # Second init should notice the hash change and clear tokens
    prompt2 = Prompt("test_prompt", project_dir=mock_project_dir)
    assert prompt2.token_size("test-model") is None

    expected_new_hash = hashlib.sha256(b"This is a CHANGED prompt.").hexdigest()
    assert prompt2.prompt_hash == expected_new_hash


def test_get_system_message(mock_project_dir: Path, mock_config_dir: Path) -> None:
    """Test that get_system_message returns a valid Context object."""
    prompt = Prompt("test_prompt", project_dir=mock_project_dir)
    prompt.update_token_size("test-model", 42)

    # Test without model
    ctx = prompt.get_system_message()

    assert ctx.text == "This is a test prompt."
    assert ctx.context_type == ContextType.SYSTEM
    assert ctx.metadata["prompt_name"] == "test_prompt"
    assert "prompt_hash" in ctx.metadata
    assert ctx.token_count == len(ctx.text) // 4
    assert ctx.is_count_estimated is True

    # Test with model
    ctx_with_model = prompt.get_system_message(model="test-model")
    assert ctx_with_model.token_count == 42
    assert ctx_with_model.is_count_estimated is False
