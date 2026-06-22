from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tdd_harness.config import TddHarnessConfig
from src.tdd_harness.controller import Phase, PhaseValidationError, TDDLoopController
from src.tdd_harness.registry import ToolRegistry


@pytest.fixture(autouse=True)
def cleanup_reports():
    yield
    report_dir = Path("docs/tasks/reports")
    if report_dir.exists():
        for f in report_dir.glob("*_report_*.md"):
            f.unlink()


@pytest.fixture
def config():
    c = TddHarnessConfig()
    c.harness["coverage_threshold"] = 80.0
    c.harness["max_uncovered_lines"] = 50
    c.llm = {
        "api_key": "dummy-key",
        "base_url": "http://localhost:8000/v1",
        "model": "gpt-4o",
        "context_size": 8000,
        "minimum_available_context": 1000,
        "keep_turns": 2,
    }
    return c


@pytest.fixture
def controller(config):
    registry = ToolRegistry()
    with (
        patch("src.tdd_harness.controller.Prompt") as mock_prompt_ctrl,
        patch("src.tdd_harness.sub_agents.Prompt") as mock_prompt_sub,
    ):
        mock_prompt_ctrl.return_value = MagicMock()
        mock_prompt_sub.return_value = MagicMock()
        return TDDLoopController(config, registry)


def test_is_path_allowed_global_lockdown(controller):
    # Cannot write to .tdd-harness
    assert not controller._is_path_allowed(".tdd-harness/config.yaml", is_write=True)
    # Can read from .tdd-harness (if it exists, though typically restricted elsewhere, global rule only restricts writes)
    assert controller._is_path_allowed(".tdd-harness/config.yaml", is_write=False)

    # Cannot write to src/tdd_harness/
    assert not controller._is_path_allowed("src/tdd_harness/runner.py", is_write=True)


def test_is_path_allowed_phase_constraints(controller):
    # AMBER phase: src is rw, test is ro
    controller.current_phase = Phase.AMBER
    assert controller._is_path_allowed("src/app/main.py", is_write=True)
    assert not controller._is_path_allowed("tests/test_main.py", is_write=True)
    assert controller._is_path_allowed("tests/test_main.py", is_write=False)

    # RED phase: src is ro, test is rw
    controller.current_phase = Phase.RED
    assert not controller._is_path_allowed("src/app/main.py", is_write=True)
    assert controller._is_path_allowed("src/app/main.py", is_write=False)
    assert controller._is_path_allowed("tests/test_main.py", is_write=True)


@patch("src.tdd_harness.controller.TDDLoopController._process_ready_tasks")
@patch("src.tdd_harness.controller.run_lint")
@patch("src.tdd_harness.controller.run_test")
@patch("src.tdd_harness.controller.run_coverage")
def test_pre_flight_validation(mock_cov, mock_test, mock_lint, mock_tasks, controller):
    mock_lint.return_value = {"status": "success"}
    mock_test.return_value = {"pytest": {"status": "success"}}
    mock_cov.return_value = {"lcov": {"status": "success"}}
    mock_tasks.return_value = True

    assert controller.pre_flight_validation() is True
    assert controller.current_phase == Phase.AMBER


@patch("src.tdd_harness.controller.run_test")
def test_red_exit(mock_test, controller):
    # If all tests pass, Red exit should raise an error
    mock_test.return_value = {"pytest": {"status": "success"}}
    with pytest.raises(PhaseValidationError):
        controller.check_red_exit()

    # If a test fails, Red exit is valid
    mock_test.return_value = {"pytest": {"status": "failed"}}
    controller.check_red_exit()


@patch("src.tdd_harness.controller.run_test")
def test_green_exit(mock_test, controller):
    # If a test fails, Green exit should raise an error
    mock_test.return_value = {"pytest": {"status": "failed"}}
    with pytest.raises(PhaseValidationError):
        controller.check_green_exit()

    # If tests pass, Green exit is valid
    mock_test.return_value = {"pytest": {"status": "success"}}
    controller.check_green_exit()


def test_magenta_exit(controller):
    # Coverage below threshold
    with patch.object(controller, "check_green_exit"):
        with pytest.raises(PhaseValidationError, match="Coverage 70.0% is below threshold"):
            controller.check_magenta_exit(70.0, 10)

    # Uncovered lines above max
    with patch.object(controller, "check_green_exit"):
        with pytest.raises(PhaseValidationError, match="Uncovered lines 60 exceeds maximum"):
            controller.check_magenta_exit(85.0, 60)

    # Valid Magenta exit
    with patch.object(controller, "check_green_exit"):
        controller.check_magenta_exit(85.0, 10)


def test_get_test_count(controller):
    from unittest.mock import mock_open

    log_data = '{"$report_type": "TestReport", "when": "call"}\n{"$report_type": "TestReport", "when": "setup"}\n'
    with patch("src.tdd_harness.controller.Path.exists", return_value=True):
        with patch("src.tdd_harness.controller.open", mock_open(read_data=log_data)):
            assert controller._get_test_count() == 1


@patch("src.tdd_harness.controller.TDDLoopController._get_test_count")
@patch("src.tdd_harness.controller.TDDLoopController.check_green_exit")
def test_blue_exit(mock_check_green, mock_get_test_count, controller):
    mock_get_test_count.return_value = 5
    with pytest.raises(PhaseValidationError, match="Test count decreased"):
        controller.check_blue_exit(10)

    mock_get_test_count.return_value = 10
    controller.check_blue_exit(10)


@pytest.mark.asyncio
@patch("src.tdd_harness.controller.run_test")
@patch("src.tdd_harness.controller.TDDLoopController._get_test_count", return_value=10)
async def test_run_blue_phase(mock_get_count, mock_run_test, controller, tmp_path):
    task_file = tmp_path / "task.md"
    task_file.write_text(
        "---\nsuccess_criteria:\n  - 'Do a thing'\ntarget_files:\n  - 'dummy.py'\n---\n## Context\nTest"
    )

    async def mock_chat(*args, **kwargs):
        controller._phase_successful = True

    with patch.object(controller.llm_client, "chat", new=mock_chat):
        with patch.object(controller, "read_file_safe", return_value="print('dummy')"):
            with patch("src.tdd_harness.controller.Path.exists", return_value=True):
                await controller.run_blue_phase(task_file)

    assert controller.current_phase == Phase.BLUE
    assert controller._initial_blue_test_count == 10


@pytest.mark.asyncio
@patch("src.tdd_harness.controller.run_lint")
@patch("src.tdd_harness.controller.orchestrate_targeted")
@patch("src.tdd_harness.controller.TDDLoopController._generate_post_mortem")
@patch("src.tdd_harness.controller.TDDLoopController._is_path_allowed", return_value=True)
async def test_stage_implementation_success(
    mock_is_path_allowed, mock_post_mortem, mock_orch, mock_lint, controller, tmp_path
):
    controller.current_phase = Phase.BLUE
    test_file = tmp_path / "test_file.py"
    test_file.write_text("print('hello')")

    # Mock successful lint and test
    mock_lint.return_value = {"status": "success"}
    mock_orch.return_value = {"pytest": {"status": "success"}}

    result = await controller.stage_implementation(str(test_file), "print('hello')")
    assert result == "Implementation staged successfully."
    assert not mock_post_mortem.called


@pytest.mark.asyncio
@patch("src.tdd_harness.controller.run_lint")
@patch("src.tdd_harness.controller.orchestrate_targeted")
@patch("src.tdd_harness.controller.TDDLoopController._generate_post_mortem")
@patch("src.tdd_harness.controller.TDDLoopController._is_path_allowed", return_value=True)
async def test_stage_implementation_lint_failure(
    mock_is_path_allowed, mock_post_mortem, mock_orch, mock_lint, controller, tmp_path
):
    controller.current_phase = Phase.BLUE
    test_file = tmp_path / "test_file.py"
    test_file.write_text("print('hello')")

    # Mock lint failure
    mock_lint.return_value = {"status": "failed", "stderr": "SyntaxError"}
    mock_post_mortem.return_value = "Fix syntax error."

    result = await controller.stage_implementation(str(test_file), "print('hello')")
    assert "Linting failed. Reverted file" in result
    assert "Post-Mortem Summary & Guidance:" in result
    assert "Fix syntax error." in result
    assert len(controller.past_failure_summaries) == 1
    assert controller.past_failure_summaries[0] == "Fix syntax error."


@pytest.mark.asyncio
@patch("src.tdd_harness.controller.run_lint")
@patch("src.tdd_harness.controller.orchestrate_targeted")
@patch("src.tdd_harness.controller.TDDLoopController._generate_post_mortem")
@patch("src.tdd_harness.controller.TDDLoopController._is_path_allowed", return_value=True)
async def test_stage_test_implementation_expected_error(
    mock_is_path_allowed, mock_post_mortem, mock_orch, mock_lint, controller, tmp_path
):
    controller.current_phase = Phase.RED
    test_file = tmp_path / "test_file.py"
    test_file.write_text("def test_fail(): assert False")

    # Mock successful lint and test failing with expected error
    mock_lint.return_value = {"status": "success"}
    mock_orch.return_value = {"pytest": {"status": "failed", "stderr": "AssertionError: 1 != 2"}}

    # Also patch yaml.dump safely so reasoning file works if needed
    with patch("src.tdd_harness.controller.yaml.dump"):
        result = await controller.stage_test_implementation(
            str(test_file), "def test_fail(): assert False", "test_fail", "concept"
        )
        assert result == "Test staged successfully."
        assert not mock_post_mortem.called


@pytest.mark.asyncio
@patch("src.tdd_harness.controller.run_lint")
@patch("src.tdd_harness.controller.TDDLoopController.check_green_exit")
async def test_success_approve(mock_check_green, mock_lint, controller, tmp_path):
    controller.current_phase = Phase.GREEN
    mock_lint.return_value = {"status": "success"}

    from unittest.mock import AsyncMock

    controller.review_agent.review = AsyncMock(return_value="APPROVE")

    result = await controller.success("Implement feature", task_file=None)
    assert result == "Phase completed successfully."


@pytest.mark.asyncio
@patch("src.tdd_harness.controller.run_lint")
@patch("src.tdd_harness.controller.TDDLoopController.check_green_exit")
async def test_success_reject(mock_check_green, mock_lint, controller, tmp_path):
    controller.current_phase = Phase.GREEN
    mock_lint.return_value = {"status": "success"}

    from unittest.mock import AsyncMock

    controller.review_agent.review = AsyncMock(return_value="REJECT: Missing edge cases.")

    result = await controller.success("Implement feature", task_file=None)
    assert "Validation failed: Review Sub-Agent Rejected the implementation" in result
    assert "REJECT: Missing edge cases." in result


@patch("subprocess.check_call")
def test_install_dependencies(mock_call, controller):
    res = controller.install_dependencies(["testpkg"])
    mock_call.assert_called_once()
    assert "Successfully installed" in res


@patch("subprocess.check_call")
def test_install_dependencies_fail(mock_call, controller):
    import subprocess

    mock_call.side_effect = subprocess.CalledProcessError(1, "cmd")
    res = controller.install_dependencies(["testpkg"])
    assert "Failed to install dependencies" in res


def test_validate_and_provision_task_missing_frontmatter(controller, tmp_path):
    task_file = tmp_path / "0001-task.md"
    task_file.write_text("No frontmatter")
    with pytest.raises(PhaseValidationError, match="Missing YAML frontmatter"):
        controller._validate_and_provision_task(task_file)


def test_validate_and_provision_task_valid(controller, tmp_path):
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
    # Shouldn't raise
    with patch.object(controller, "install_dependencies") as mock_install:
        controller._validate_and_provision_task(task_file)
        mock_install.assert_not_called()


def test_process_ready_tasks_moves_error(controller, tmp_path):
    # Setup ready and error dirs
    with patch("src.tdd_harness.controller.Path") as mock_path_cls:
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

        # mock a task
        mock_task = MagicMock()
        mock_task.name = "0001-test.md"
        mock_task.stem = "0001-test"
        mock_ready.glob.return_value = [mock_task]

        with patch.object(controller, "_validate_and_provision_task") as mock_validate:
            with patch("src.tdd_harness.controller.shutil.move") as mock_move:
                with patch("src.tdd_harness.controller.open"):
                    mock_validate.side_effect = PhaseValidationError("Failed")
                    res = controller._process_ready_tasks()
                    assert res is False
                    mock_move.assert_called_once()


@pytest.mark.asyncio
async def test_execute_tool_thrashing_abort(controller):
    from src.tdd_harness.registry import ToolCallResult

    # Mock dispatch to return a failure
    controller.registry.dispatch = AsyncMock(return_value=ToolCallResult(content=None, success=False, error="Fail"))

    # Mock should_abort to return True
    with patch.object(controller.tracker, "should_abort", return_value=True):
        with pytest.raises(SystemExit):
            await controller.execute_tool("my_tool", {"arg": "val"})


@pytest.mark.asyncio
async def test_execute_tool_success_record(controller):
    from src.tdd_harness.registry import ToolCallResult

    # Mock dispatch to return success
    controller.registry.dispatch = AsyncMock(return_value=ToolCallResult(content="OK", success=True, error=None))

    with patch.object(controller.tracker, "record_tool_call") as mock_record:
        res = await controller.execute_tool("my_tool", {"arg": "val"})
        assert res == "OK"
        mock_record.assert_called_once()
