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
    assert args.command is None

    # Test with project directory
    args = parse_args(["--project-dir", "/tmp/project"])
    assert args.project_dir == "/tmp/project"

    # Test with phase
    args = parse_args(["--phase", "green"])
    assert args.phase == "green"

    # Test with init command
    args = parse_args(["init"])
    assert args.command == "init"


def test_init_project(capsys: pytest.CaptureFixture):
    """Test init_project command."""
    from src.tdd_harness.cli import init_project

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        init_project(str(tmp_path))

        config_dir = tmp_path / ".tdd-harness"
        assert config_dir.exists()
        assert config_dir.is_dir()

        config_file = config_dir / "config.yaml"
        assert config_file.exists()
        assert "provider: openai" in config_file.read_text()

        prompts_dir = config_dir / "prompts"
        assert prompts_dir.exists()

        system_message = prompts_dir / "system_message.yaml"
        assert system_message.exists()
        assert "You are an AI developer" in system_message.read_text()

        compression_prompt = prompts_dir / "compression_prompt.yaml"
        assert compression_prompt.exists()
        assert "Summarize the following chat history" in compression_prompt.read_text()

        # Test running again aborts gracefully
        init_project(str(tmp_path))
        captured = capsys.readouterr()
        assert "already exists. Initialization aborted." in captured.out


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

            with patch("src.tdd_harness.cli.async_main"):
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


def test_main_missing_config(capsys: pytest.CaptureFixture) -> None:
    """
    Test main function when config directory is missing.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
    """
    with patch("src.tdd_harness.cli.resolve_config_directory") as mock_resolve:
        mock_resolve.side_effect = FileNotFoundError("Config directory not found")

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "run 'tdd-harness init'" in captured.out


@pytest.mark.asyncio
async def test_async_main_success():
    """Test async_main completes successfully."""
    from unittest.mock import AsyncMock

    from src.tdd_harness.cli import async_main

    with (
        patch("src.tdd_harness.cli.sys.exit") as mock_exit,
        patch("src.tdd_harness.cli.load_tdd_harness_config"),
        patch("src.tdd_harness.cli.MCPClient"),
        patch("src.tdd_harness.cli.ToolRegistry") as mock_registry,
        patch("src.tdd_harness.cli.TDDLoopController") as mock_controller_cls,
        patch("src.tdd_harness.cli.LLMClient"),
        patch("src.tdd_harness.cli.Prompt"),
        patch("src.tdd_harness.cli.Path.exists", return_value=True),
        patch("src.tdd_harness.cli.Path.glob") as mock_glob,
        patch("src.tdd_harness.cli.shutil.move") as mock_move,
    ):
        mock_registry_instance = MagicMock()
        mock_registry_instance.initialize = AsyncMock()
        mock_registry_instance.dispatch = AsyncMock()
        mock_registry.return_value = mock_registry_instance

        mock_controller_instance = MagicMock()
        mock_controller_instance.pre_flight_validation.return_value = True
        mock_controller_instance.run_blue_phase = AsyncMock()
        mock_controller_instance.run_red_phase = AsyncMock()
        mock_controller_instance.run_green_phase = AsyncMock()
        mock_controller_instance.run_magenta_loop = AsyncMock()
        mock_controller_cls.return_value = mock_controller_instance

        mock_task = MagicMock()
        mock_task.name = "0001-task.md"
        mock_glob.return_value = [mock_task]

        await async_main(Path("/tmp/config"))

        mock_controller_instance.pre_flight_validation.assert_called_once()
        mock_controller_instance.run_blue_phase.assert_awaited_once_with(mock_task)
        mock_controller_instance.run_red_phase.assert_awaited_once_with(mock_task)
        mock_controller_instance.run_green_phase.assert_awaited_once_with(mock_task)
        mock_controller_instance.run_magenta_loop.assert_awaited_once()
        mock_exit.assert_not_called()
        mock_move.assert_called_once()


@pytest.mark.asyncio
async def test_async_main_phase_green():
    """Test async_main starts at green phase when specified."""
    from unittest.mock import AsyncMock

    from src.tdd_harness.cli import async_main

    with (
        patch("src.tdd_harness.cli.sys.exit") as mock_exit,
        patch("src.tdd_harness.cli.load_tdd_harness_config"),
        patch("src.tdd_harness.cli.MCPClient"),
        patch("src.tdd_harness.cli.ToolRegistry") as mock_registry,
        patch("src.tdd_harness.cli.TDDLoopController") as mock_controller_cls,
        patch("src.tdd_harness.cli.LLMClient"),
        patch("src.tdd_harness.cli.Prompt"),
        patch("src.tdd_harness.cli.Path.exists", return_value=True),
        patch("src.tdd_harness.cli.Path.glob") as mock_glob,
        patch("src.tdd_harness.cli.shutil.move") as mock_move,
    ):
        mock_registry_instance = MagicMock()
        mock_registry_instance.initialize = AsyncMock()
        mock_registry_instance.dispatch = AsyncMock()
        mock_registry.return_value = mock_registry_instance

        mock_controller_instance = MagicMock()
        mock_controller_instance.pre_flight_validation.return_value = True
        mock_controller_instance.run_blue_phase = AsyncMock()
        mock_controller_instance.run_red_phase = AsyncMock()
        mock_controller_instance.run_green_phase = AsyncMock()
        mock_controller_instance.run_magenta_loop = AsyncMock()
        mock_controller_cls.return_value = mock_controller_instance

        mock_task = MagicMock()
        mock_task.name = "0001-task.md"
        mock_glob.return_value = [mock_task]

        await async_main(Path("/tmp/config"), phase="green")

        mock_controller_instance.run_blue_phase.assert_not_called()
        mock_controller_instance.run_red_phase.assert_not_called()
        mock_controller_instance.run_green_phase.assert_awaited_once_with(mock_task)
        mock_controller_instance.run_magenta_loop.assert_awaited_once()
        mock_exit.assert_not_called()
        mock_move.assert_called_once()


@pytest.mark.asyncio
async def test_async_main_pre_flight_failure():
    """Test async_main exits on pre-flight failure."""
    from unittest.mock import AsyncMock

    from src.tdd_harness.cli import async_main

    with (
        patch("src.tdd_harness.cli.sys.exit") as mock_exit,
        patch("src.tdd_harness.cli.load_tdd_harness_config"),
        patch("src.tdd_harness.cli.MCPClient"),
        patch("src.tdd_harness.cli.ToolRegistry") as mock_registry,
        patch("src.tdd_harness.cli.TDDLoopController") as mock_controller_cls,
        patch("src.tdd_harness.cli.LLMClient"),
        patch("src.tdd_harness.cli.Prompt"),
    ):
        mock_exit.side_effect = SystemExit(1)
        mock_registry_instance = MagicMock()
        mock_registry_instance.initialize = AsyncMock()
        mock_registry.return_value = mock_registry_instance

        mock_controller_instance = MagicMock()
        mock_controller_instance.pre_flight_validation.return_value = False
        mock_controller_cls.return_value = mock_controller_instance

        with pytest.raises(SystemExit) as exc_info:
            await async_main(Path("/tmp/config"))

        assert exc_info.value.code == 1
        mock_exit.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_async_main_no_tasks():
    """Test async_main exits when no tasks found."""
    from unittest.mock import AsyncMock

    from src.tdd_harness.cli import async_main

    with (
        patch("src.tdd_harness.cli.sys.exit") as mock_exit,
        patch("src.tdd_harness.cli.load_tdd_harness_config"),
        patch("src.tdd_harness.cli.MCPClient"),
        patch("src.tdd_harness.cli.ToolRegistry") as mock_registry,
        patch("src.tdd_harness.cli.TDDLoopController") as mock_controller_cls,
        patch("src.tdd_harness.cli.LLMClient"),
        patch("src.tdd_harness.cli.Prompt"),
        patch("src.tdd_harness.cli.Path.exists", return_value=True),
        patch("src.tdd_harness.cli.Path.glob", return_value=[]),
    ):
        mock_exit.side_effect = SystemExit(1)
        mock_registry_instance = MagicMock()
        mock_registry_instance.initialize = AsyncMock()
        mock_registry_instance.dispatch = AsyncMock()
        mock_registry.return_value = mock_registry_instance

        mock_controller_instance = MagicMock()
        mock_controller_instance.pre_flight_validation.return_value = True
        mock_controller_cls.return_value = mock_controller_instance

        with pytest.raises(SystemExit) as exc_info:
            await async_main(Path("/tmp/config"))

        assert exc_info.value.code == 1
        mock_exit.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_async_main_value_error():
    """Test async_main ignores ValueError on index_repo."""
    from unittest.mock import AsyncMock

    from src.tdd_harness.cli import async_main

    with (
        patch("src.tdd_harness.cli.sys.exit") as mock_exit,
        patch("src.tdd_harness.cli.load_tdd_harness_config"),
        patch("src.tdd_harness.cli.MCPClient"),
        patch("src.tdd_harness.cli.ToolRegistry") as mock_registry,
        patch("src.tdd_harness.cli.TDDLoopController") as mock_controller_cls,
        patch("src.tdd_harness.cli.LLMClient"),
        patch("src.tdd_harness.cli.Prompt"),
        patch("src.tdd_harness.cli.Path.exists", return_value=True),
        patch("src.tdd_harness.cli.Path.glob") as mock_glob,
        patch("src.tdd_harness.cli.shutil.move"),
    ):
        mock_registry_instance = MagicMock()
        mock_registry_instance.initialize = AsyncMock()
        mock_registry_instance.dispatch = AsyncMock(side_effect=ValueError)
        mock_registry.return_value = mock_registry_instance

        mock_controller_instance = MagicMock()
        mock_controller_instance.pre_flight_validation.return_value = True
        mock_controller_instance.run_blue_phase = AsyncMock()
        mock_controller_instance.run_red_phase = AsyncMock()
        mock_controller_instance.run_green_phase = AsyncMock()
        mock_controller_instance.run_magenta_loop = AsyncMock()
        mock_controller_cls.return_value = mock_controller_instance

        mock_task = MagicMock()
        mock_task.name = "0001-task.md"
        mock_glob.return_value = [mock_task]

        await async_main(Path("/tmp/config"))

        mock_exit.assert_not_called()
