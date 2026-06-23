import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tdd_harness.exceptions import PhaseValidationError
from src.tdd_harness.task_loader import TaskLoader


@pytest.fixture
def loader():
    mock_research_agent = MagicMock()
    mock_registry = MagicMock()
    # Need to be AsyncMocks for the async inner function
    mock_research_agent.ask = AsyncMock()
    mock_registry.dispatch = AsyncMock()
    return TaskLoader(mock_research_agent, mock_registry)


def test_validate_and_provision_task_missing_frontmatter(loader, tmp_path):
    task_file = tmp_path / "0001-task.md"
    task_file.write_text("No frontmatter")
    with pytest.raises(PhaseValidationError, match="Missing YAML frontmatter"):
        loader.validate_and_provision_task(task_file)


def test_validate_and_provision_task_valid(loader, tmp_path):
    task_file = tmp_path / "0002-task.md"
    task_file.write_text("""---
id: "123"
title: "Test"
success_criteria: []
dependencies:
  prod: []
  dev: []
---
## Context
Testing
""")
    with patch("src.tdd_harness.task_loader.install_dependencies") as mock_install:
        loader.validate_and_provision_task(task_file)
        mock_install.assert_not_called()


def test_process_ready_tasks_moves_error(loader, tmp_path):
    with patch("src.tdd_harness.task_loader.Path") as mock_path_cls:
        mock_ready = MagicMock()
        mock_error = MagicMock()

        def path_side_effect(arg):
            if str(arg) == "docs/tasks/ready":
                return mock_ready
            if str(arg) == "docs/tasks/error":
                return mock_error
            return Path(arg)

        mock_path_cls.side_effect = path_side_effect
        mock_ready.exists.return_value = True

        mock_task = MagicMock()
        mock_task.name = "0001-test.md"
        mock_task.stem = "0001-test"
        mock_ready.glob.return_value = [mock_task]

        with patch.object(loader, "validate_and_provision_task") as mock_validate:
            with patch("src.tdd_harness.task_loader.shutil.move") as mock_move:
                with patch("src.tdd_harness.task_loader.open") as mock_open:
                    mock_validate.side_effect = PhaseValidationError("Failed")
                    res = loader.process_ready_tasks()
                    assert res is False
                    mock_move.assert_called_once()
                    mock_open.assert_called_once()
                    mock_open.return_value.__enter__.return_value.write.assert_called_once_with("Failed")


def test_process_ready_tasks_no_dir(loader):
    with patch("src.tdd_harness.task_loader.Path") as mock_path_cls:
        mock_ready = MagicMock()
        mock_path_cls.return_value = mock_ready
        mock_ready.exists.return_value = False
        assert loader.process_ready_tasks() is True


def test_validate_and_provision_task_invalid_yaml(loader, tmp_path):
    task_file = tmp_path / "t.md"
    task_file.write_text("---\n[invalid yaml\n---\n## Context")
    with pytest.raises(PhaseValidationError, match="Invalid YAML parsing"):
        loader.validate_and_provision_task(task_file)


def test_validate_and_provision_task_not_dict(loader, tmp_path):
    task_file = tmp_path / "t.md"
    task_file.write_text("---\n- item\n---\n## Context")
    with pytest.raises(PhaseValidationError, match="YAML frontmatter must be a dictionary"):
        loader.validate_and_provision_task(task_file)


def test_validate_and_provision_task_missing_fields(loader, tmp_path):
    task_file = tmp_path / "t.md"
    task_file.write_text("---\nid: '123'\n---\n## Context")
    with pytest.raises(PhaseValidationError, match="Missing required field"):
        loader.validate_and_provision_task(task_file)


def test_validate_and_provision_task_invalid_format(loader, tmp_path):
    task_file = tmp_path / "t.md"
    task_file.write_text("---")
    with pytest.raises(PhaseValidationError, match="Invalid YAML frontmatter format"):
        loader.validate_and_provision_task(task_file)


def test_validate_and_provision_task_success_criteria_not_list(loader, tmp_path):
    task_file = tmp_path / "t.md"
    task_file.write_text("---\nid: '1'\ntitle: 't'\nsuccess_criteria: 'str'\n---\n## Context")
    with pytest.raises(PhaseValidationError, match="success_criteria must be a list"):
        loader.validate_and_provision_task(task_file)


def test_validate_and_provision_task_missing_context(loader, tmp_path):
    task_file = tmp_path / "t.md"
    task_file.write_text("---\nid: '1'\ntitle: 't'\nsuccess_criteria: []\n---\nNo context header")
    with pytest.raises(PhaseValidationError, match="Missing '## Context' Markdown header"):
        loader.validate_and_provision_task(task_file)


@pytest.mark.asyncio
async def test_validate_and_provision_task_with_deps(loader, tmp_path):
    task_file = tmp_path / "0002-task.md"
    task_file.write_text("""---
id: "123"
title: "Test"
success_criteria: []
dependencies:
  prod: ["requests"]
  dev: []
---
## Context
Testing
""")
    with patch(
        "src.tdd_harness.task_loader.install_dependencies", return_value="Successfully installed: requests"
    ) as mock_install:
        loader.validate_and_provision_task(task_file)
        mock_install.assert_called_once_with(["requests"])
        # Wait for the background task to complete
        await asyncio.sleep(0.01)
        loader.research_agent.ask.assert_called_once()
        loader.registry.dispatch.assert_called_once_with("index_folder", {"path": "docs/reference"})

    with patch("src.tdd_harness.task_loader.install_dependencies", return_value="Failed to install") as mock_install:
        with pytest.raises(PhaseValidationError, match="Failed to install"):
            loader.validate_and_provision_task(task_file)


def test_validate_and_provision_task_with_deps_sync(loader, tmp_path):
    task_file = tmp_path / "0003-task.md"
    task_file.write_text("""---
id: "123"
title: "Test"
success_criteria: []
dependencies:
  prod: ["requests"]
  dev: []
---
## Context
Testing
""")
    with patch("src.tdd_harness.task_loader.asyncio.get_running_loop", side_effect=RuntimeError):
        with patch("src.tdd_harness.task_loader.asyncio.run") as mock_run:
            with patch(
                "src.tdd_harness.task_loader.install_dependencies", return_value="Successfully installed: requests"
            ):
                loader.validate_and_provision_task(task_file)
                mock_run.assert_called_once()
