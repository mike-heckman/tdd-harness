from unittest.mock import patch

import pytest

from src.tdd_harness.config import TddHarnessConfig
from src.tdd_harness.controller import Phase, PhaseValidationError, TDDLoopController
from src.tdd_harness.registry import ToolRegistry


@pytest.fixture
def config():
    c = TddHarnessConfig()
    c.harness["coverage_threshold"] = 80.0
    c.harness["max_uncovered_lines"] = 50
    return c


@pytest.fixture
def controller(config):
    registry = ToolRegistry()
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


@patch("src.tdd_harness.controller.run_lint")
@patch("src.tdd_harness.controller.run_test")
@patch("src.tdd_harness.controller.run_coverage")
def test_pre_flight_validation(mock_cov, mock_test, mock_lint, controller):
    mock_lint.return_value = {"status": "success"}
    mock_test.return_value = {"pytest": {"status": "success"}}
    mock_cov.return_value = {"lcov": {"status": "success"}}

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
