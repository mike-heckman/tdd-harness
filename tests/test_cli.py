"""Tests for the CLI module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.tdd_harness.cli import main, parse_args


def test_parse_args():
    """Test argument parsing."""
    # Test default arguments
    args = parse_args([])
    assert args.project_dir is None
    assert args.phase is None

    # Test with project directory
    args = parse_args(["--project-dir", "/tmp/project"])
    assert args.project_dir == "/tmp/project"

    # Test with phase
    args = parse_args(["--phase", "green"])
    assert args.phase == "green"


def test_main_with_clean_git():
    """Test main function with clean git status."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Create a git repository
        (tmp_path / ".git").mkdir()

        # Create a .tdd-harness directory
        config_dir = tmp_path / ".tdd-harness"
        config_dir.mkdir()

        with patch("src.tdd_harness.cli.resolve_config_directory") as mock_resolve:
            mock_resolve.return_value = config_dir

            with patch("subprocess.run") as mock_run:
                # Mock successful git status check
                mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

                # This should not raise an exception
                try:
                    main()
                except SystemExit:
                    pytest.fail("main() should not exit with SystemExit")


def test_main_with_dirty_git():
    """Test main function with dirty git status."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Create a git repository
        (tmp_path / ".git").mkdir()

        # Create a .tdd-harness directory
        config_dir = tmp_path / ".tdd-harness"
        config_dir.mkdir()

        with patch("src.tdd_harness.cli.resolve_config_directory") as mock_resolve:
            mock_resolve.return_value = config_dir

            with patch("subprocess.run") as mock_run:
                # Mock dirty git status check
                mock_run.return_value = MagicMock(stdout=" M file.py", stderr="", returncode=0)

                # This should exit with error code 1
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 1
