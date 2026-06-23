from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tdd_harness.config import TddHarnessConfig
from src.tdd_harness.controller import TDDLoopController
from src.tdd_harness.exceptions import HarnessAbort, PhaseValidationError
from src.tdd_harness.phase import Phase
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
    from src.tdd_harness.config import HarnessContext
    from src.tdd_harness.context import ContextBuilder

    harness_ctx = HarnessContext()
    context_builder = ContextBuilder()
    with (
        patch("src.tdd_harness.controller.Prompt") as mock_prompt_ctrl,
        patch("src.tdd_harness.sub_agents.Prompt") as mock_prompt_sub,
    ):
        mock_prompt_ctrl.return_value = MagicMock()
        mock_prompt_sub.return_value = MagicMock()
        mock_llm_client = MagicMock()
        return TDDLoopController(config, registry, mock_llm_client, harness_ctx, context_builder)


@patch("src.tdd_harness.task_loader.TaskLoader.process_ready_tasks")
@patch("src.tdd_harness.controller.run_lint")
@patch("src.tdd_harness.controller.run_test_and_coverage")
def test_pre_flight_validation(mock_test_cov, mock_lint, mock_tasks, controller):
    mock_lint.return_value = {"status": "success"}
    mock_test_cov.return_value = {"test_python_pytest": {"status": "success"}, "cov_python_lcov": {"status": "success"}}
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
async def test_run_red_phase(controller, tmp_path):
    task_file = tmp_path / "task.md"
    task_file.write_text(
        "---\nsuccess_criteria:\n  - 'Do a thing'\ntarget_files:\n  - 'dummy.py'\n---\n## Context\nTest"
    )

    async def mock_chat(*args, **kwargs):
        controller._phase_successful = True

    with patch.object(controller.llm_client, "chat", new=mock_chat):
        with patch.object(controller, "read_file_safe", return_value="print('dummy')"):
            with patch("src.tdd_harness.controller.Path.exists", return_value=True):
                await controller.run_red_phase(task_file)

    assert controller.current_phase == Phase.RED


@pytest.mark.asyncio
async def test_run_red_phase_post_mortem_injection(controller, tmp_path):
    task_file = tmp_path / "task.md"
    task_file.write_text(
        "---\nsuccess_criteria:\n  - 'Do a thing'\ntarget_files:\n  - 'dummy.py'\n---\n## Context\nTest"
    )

    chat_call_count = 0

    async def mock_chat(*args, **kwargs):
        nonlocal chat_call_count
        chat_call_count += 1

        if chat_call_count == 1:
            # First turn: simulate a failure being appended
            controller.past_failure_summaries.append("Simulated test failure guidance")
        else:
            # Second turn: verify ContextBuilder has the failure
            cb = controller.context_builder
            feedback_contexts = [ctx for ctx in cb.get_context() if "Simulated test failure guidance" in ctx.text]
            assert len(feedback_contexts) == 1
            controller._phase_successful = True

    with patch.object(controller.llm_client, "chat", new=mock_chat):
        with patch.object(controller, "read_file_safe", return_value="print('dummy')"):
            with patch("src.tdd_harness.controller.Path.exists", return_value=True):
                await controller.run_red_phase(task_file)

    assert controller.current_phase == Phase.RED
    assert chat_call_count == 2


@pytest.mark.asyncio
async def test_run_green_phase(controller, tmp_path):
    task_file = tmp_path / "task.md"
    task_file.write_text(
        "---\nsuccess_criteria:\n  - 'Do a thing'\ntarget_files:\n  - 'dummy.py'\n---\n## Context\nTest"
    )

    async def mock_chat(*args, **kwargs):
        controller._phase_successful = True

    with patch.object(controller.llm_client, "chat", new=mock_chat):
        with patch.object(controller, "read_file_safe", return_value="print('dummy')"):
            with patch("src.tdd_harness.controller.Path.exists", return_value=True):
                await controller.run_green_phase(task_file)

    assert controller.current_phase == Phase.GREEN


@pytest.mark.asyncio
async def test_run_green_phase_post_mortem_injection(controller, tmp_path):
    task_file = tmp_path / "task.md"
    task_file.write_text(
        "---\nsuccess_criteria:\n  - 'Do a thing'\ntarget_files:\n  - 'dummy.py'\n---\n## Context\nTest"
    )

    chat_call_count = 0

    async def mock_chat(*args, **kwargs):
        nonlocal chat_call_count
        chat_call_count += 1

        if chat_call_count == 1:
            # First turn: simulate a failure being appended
            controller.past_failure_summaries.append("Simulated test failure guidance")
        else:
            # Second turn: verify ContextBuilder has the failure
            cb = controller.context_builder
            feedback_contexts = [ctx for ctx in cb.get_context() if "Simulated test failure guidance" in ctx.text]
            assert len(feedback_contexts) == 1
            controller._phase_successful = True

    with patch.object(controller.llm_client, "chat", new=mock_chat):
        with patch.object(controller, "read_file_safe", return_value="print('dummy')"):
            with patch("src.tdd_harness.controller.Path.exists", return_value=True):
                await controller.run_green_phase(task_file)

    assert controller.current_phase == Phase.GREEN
    assert chat_call_count == 2


@pytest.mark.asyncio
@patch("src.tdd_harness.controller.run_lint")
@patch("src.tdd_harness.controller.orchestrate_targeted")
@patch("src.tdd_harness.controller.TDDLoopController._generate_post_mortem")
@patch("src.tdd_harness.security.SecurityInterceptor.is_path_allowed", return_value=True)
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
@patch("src.tdd_harness.security.SecurityInterceptor.is_path_allowed", return_value=True)
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
@patch("src.tdd_harness.security.SecurityInterceptor.is_path_allowed", return_value=True)
async def test_stage_implementation_crash_safe(mock_is_path_allowed, mock_lint, controller, tmp_path):
    controller.current_phase = Phase.BLUE
    test_file = tmp_path / "test_file.py"
    test_file.write_text("print('hello')")

    # Mock lint throwing an unhandled exception
    mock_lint.side_effect = RuntimeError("Crash during linting")

    with pytest.raises(RuntimeError, match="Crash during linting"):
        await controller.stage_implementation(str(test_file), "print('hello_new')")

    # Verify file was reverted
    assert test_file.read_text() == "print('hello')"


@pytest.mark.asyncio
@patch("src.tdd_harness.controller.run_lint")
@patch("src.tdd_harness.controller.orchestrate_targeted")
@patch("src.tdd_harness.controller.TDDLoopController._generate_post_mortem")
@patch("src.tdd_harness.security.SecurityInterceptor.is_path_allowed", return_value=True)
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


@pytest.mark.asyncio
async def test_execute_tool_thrashing_abort(controller):
    from src.tdd_harness.registry import ToolCallResult

    # Mock dispatch to return a failure
    controller.registry.dispatch = AsyncMock(return_value=ToolCallResult(content=None, success=False, error="Fail"))

    # Mock should_abort to return True
    with patch.object(controller.tracker, "should_abort", return_value=True):
        with pytest.raises(HarnessAbort):
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


@pytest.mark.asyncio
@patch("src.tdd_harness.controller.orchestrate_global")
async def test_run_magenta_loop_success(mock_orchestrate, controller):
    with patch("src.tdd_harness.controller.Path.exists", return_value=True):
        with patch("src.tdd_harness.controller.LcovParser") as mock_parser_cls:
            mock_parser = MagicMock()
            mock_parser_cls.return_value = mock_parser
            # First it has missing coverage, then empty
            mock_parser.get_missing_coverage.side_effect = [{"src/dummy.py": [10, 11]}, {}]
            mock_parser.file_stats = {"src/dummy.py": {"lines": {10: 0, 11: 0}}}

            async def mock_chat(*args, **kwargs):
                controller._phase_successful = True

            with patch.object(controller.llm_client, "chat", new=mock_chat):
                with patch.object(controller, "read_file_safe", return_value="print('dummy')"):
                    with patch.object(controller, "check_magenta_exit", side_effect=PhaseValidationError("Failed")):
                        await controller.run_magenta_loop()

    assert controller.current_phase == Phase.MAGENTA


@pytest.mark.asyncio
@patch("src.tdd_harness.controller.orchestrate_global")
async def test_run_magenta_loop_abort(mock_orchestrate, controller):
    with patch("src.tdd_harness.controller.Path.exists", return_value=True):
        with patch("src.tdd_harness.controller.LcovParser") as mock_parser_cls:
            mock_parser = MagicMock()
            mock_parser_cls.return_value = mock_parser
            # Always missing coverage
            mock_parser.get_missing_coverage.return_value = {"src/dummy.py": [10, 11]}
            mock_parser.file_stats = {"src/dummy.py": {"lines": {10: 0, 11: 0}}}

            async def mock_chat(*args, **kwargs):
                controller._phase_successful = True

            with patch.object(controller.llm_client, "chat", new=mock_chat):
                with patch.object(controller, "read_file_safe", return_value="print('dummy')"):
                    with patch.object(controller, "check_magenta_exit", side_effect=PhaseValidationError("Failed")):
                        with pytest.raises(HarnessAbort):
                            await controller.run_magenta_loop()


def test_abort(controller):
    with pytest.raises(HarnessAbort):
        controller.abort("testing abort")


@pytest.mark.asyncio
@patch("src.tdd_harness.controller.run_lint")
async def test_success_lint_failure(mock_lint, controller):
    mock_lint.return_value = {"status": "failed", "stderr": "Bad lint"}
    res = await controller.success("msg")
    assert "Linting errors" in res


@pytest.mark.asyncio
@patch("src.tdd_harness.controller.run_lint")
@patch.object(TDDLoopController, "check_red_exit", side_effect=PhaseValidationError("Red failed"))
async def test_success_validation_failure(mock_red_exit, mock_lint, controller):
    controller.current_phase = Phase.RED
    mock_lint.return_value = {"status": "success"}
    res = await controller.success("msg")
    assert "Validation failed: Red failed" in res


@pytest.mark.asyncio
@patch("src.tdd_harness.controller.run_lint")
@patch.object(TDDLoopController, "check_green_exit")
async def test_success_with_diffs(mock_check_green, mock_lint, controller, tmp_path):
    from unittest.mock import PropertyMock

    controller.current_phase = Phase.GREEN
    mock_lint.return_value = {"status": "success"}
    controller.review_agent.review = AsyncMock(return_value="APPROVE")

    backup_dir = tmp_path / "backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    with patch(
        "src.tdd_harness.controller.HarnessContext.backup_dir", new_callable=PropertyMock, return_value=backup_dir
    ):
        f1 = tmp_path / "f1.py"
        f1.write_text("new")
        (backup_dir / "f1.py.bak").write_text("old")

        f2 = tmp_path / "f2.py"
        f2.write_text("new_only")

        controller.session_modified_files.update([str(f1), str(f2)])

        res = await controller.success("msg")
        assert res == "Phase completed successfully."
        args, _ = controller.review_agent.review.call_args
        unified_diff = args[2]
        assert "-old" in unified_diff or "new_only" in unified_diff


@pytest.mark.asyncio
@patch("src.tdd_harness.controller.run_lint")
@patch("src.tdd_harness.controller.orchestrate_targeted")
@patch("src.tdd_harness.controller.TDDLoopController._generate_post_mortem")
@patch("src.tdd_harness.security.SecurityInterceptor.is_path_allowed", return_value=True)
async def test_stage_test_implementation_wrong_error(
    mock_is_path_allowed, mock_post_mortem, mock_orch, mock_lint, controller, tmp_path
):
    controller.current_phase = Phase.RED
    test_file = tmp_path / "test_file.py"
    test_file.write_text("def test_fail(): pass")

    mock_lint.return_value = {"status": "success"}
    mock_orch.return_value = {"pytest": {"status": "failed", "stderr": "SyntaxError: oops"}}
    mock_post_mortem.return_value = "Syntax error instead of assertion"

    result = await controller.stage_test_implementation(str(test_file), "def test_fail(): pass", "test_fail", "concept")
    assert "Test did not fail with AssertionError" in result


@pytest.mark.asyncio
async def test_ask_researcher(controller):
    controller.research_agent.ask = AsyncMock(return_value="Researched")
    res = await controller.ask_researcher("q")
    assert res == "Researched"


@pytest.mark.asyncio
async def test_generate_post_mortem(controller):
    controller.post_mortem_agent.generate = AsyncMock(return_value="PM")
    with patch.object(controller, "read_file_safe", return_value="code"):
        res = await controller._generate_post_mortem("file.py", "err")
        assert res == "PM"
        # Second call should use cache
        res2 = await controller._generate_post_mortem("file.py", "err")
        assert res2 == "PM"
        assert controller.post_mortem_agent.generate.call_count == 1


@pytest.mark.asyncio
async def test_stage_implementation_wrong_phase(controller):
    controller.current_phase = Phase.RED
    res = await controller.stage_implementation("f.py", "c")
    assert "can only be used in the Blue or Green" in res


@pytest.mark.asyncio
async def test_stage_test_implementation_wrong_phase(controller):
    controller.current_phase = Phase.GREEN
    res = await controller.stage_test_implementation("f.py", "c", "t", "c")
    assert "can only be used in the Red" in res


@pytest.mark.asyncio
@patch("src.tdd_harness.controller.run_lint")
@patch("src.tdd_harness.security.SecurityInterceptor.is_path_allowed", return_value=True)
async def test_stage_test_implementation_crash_safe(mock_is_path_allowed, mock_lint, controller, tmp_path):
    controller.current_phase = Phase.RED
    test_file = tmp_path / "test_file.py"
    test_file.write_text("print('hello')")

    # Mock lint throwing an unhandled exception
    mock_lint.side_effect = RuntimeError("Crash during linting")

    with pytest.raises(RuntimeError, match="Crash during linting"):
        await controller.stage_test_implementation(str(test_file), "print('hello_new')", "t", "c")

    # Verify file was reverted
    assert test_file.read_text() == "print('hello')"


@pytest.mark.asyncio
@patch("src.tdd_harness.controller.run_lint")
@patch("src.tdd_harness.controller.TDDLoopController.check_green_exit")
async def test_success_fallback_task_file(mock_check_green, mock_lint, controller, tmp_path):
    controller.current_phase = Phase.GREEN
    mock_lint.return_value = {"status": "success"}

    from unittest.mock import AsyncMock

    controller.review_agent.review = AsyncMock(return_value="APPROVE")

    # Mock ready dir and task file
    ready_dir = tmp_path / "docs" / "tasks" / "ready"
    ready_dir.mkdir(parents=True, exist_ok=True)
    (ready_dir / "0001-task.md").write_text("Fallback task content")

    with patch("src.tdd_harness.controller.Path") as mock_path_cls:
        # Simple side effect that resolves the glob to our tmp task
        def path_side_effect(arg):
            if str(arg) == "docs/tasks/ready":
                p = MagicMock()
                p.exists.return_value = True
                p.glob.return_value = [ready_dir / "0001-task.md"]
                return p
            return Path(arg)

        mock_path_cls.side_effect = path_side_effect

        result = await controller.success("Implement feature", task_file=None)
        assert result == "Phase completed successfully."

        # Verify the fallback content was read
        args, _ = controller.review_agent.review.call_args
        assert args[0] == "Fallback task content"
