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
