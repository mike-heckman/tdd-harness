"""Tests for the runner module."""

from unittest.mock import patch

from src.tdd_harness.adapters.lcov_adapter import LcovAdapter
from src.tdd_harness.adapters.pytest_adapter import PytestAdapter
from src.tdd_harness.adapters.ruff_adapter import RuffAdapter
from src.tdd_harness.config import TddHarnessConfig
from src.tdd_harness.models.tool import ToolCallResponse
from src.tdd_harness.runner import (
    AdapterRegistry,
    orchestrate_defined,
    orchestrate_global,
    orchestrate_targeted,
    parse_active_languages,
    run_coverage,
    run_lint,
    run_test,
)


def test_parse_active_languages(tmp_path):
    lang_file = tmp_path / ".languages"
    lang_file.write_text("HAS_PY=true\nHAS_TS=false\n")

    active = parse_active_languages(tmp_path)
    assert active == ["python"]


def test_adapter_registry_discover():
    adapters = AdapterRegistry.get_adapters()
    assert len(adapters) > 0
    assert PytestAdapter in adapters
    assert RuffAdapter in adapters
    assert LcovAdapter in adapters


def test_adapter_registry_get_adapters_by_lang():
    adapters = AdapterRegistry.get_adapters(language="python")
    assert PytestAdapter in adapters


def test_orchestrate_targeted():
    config = TddHarnessConfig()
    with patch("src.tdd_harness.runner.AdapterRegistry.get_adapters") as mock_get_adapters:
        mock_get_adapters.return_value = [PytestAdapter]
        with patch.object(PytestAdapter, "run") as mock_run:
            mock_run.return_value = ToolCallResponse(success=True, output="Passed", errors=None)

            res = orchestrate_targeted(config, "test_file.py")
            assert "PytestAdapter" in res
            assert res["PytestAdapter"]["status"] == "success"


def test_orchestrate_defined():
    config = TddHarnessConfig()
    with patch("src.tdd_harness.runner.orchestrate_targeted") as mock_targeted:
        mock_targeted.return_value = {"PytestAdapter": {"status": "success"}}

        res = orchestrate_defined(config, "test_file.py::test_case")
        mock_targeted.assert_called_once_with(config, "test_file.py")
        assert res["PytestAdapter"]["status"] == "success"


def test_orchestrate_global(tmp_path):
    config = TddHarnessConfig()
    with patch("src.tdd_harness.runner.parse_active_languages", return_value=["python"]):
        with patch("src.tdd_harness.runner.AdapterRegistry.get_adapters") as mock_get_adapters:

            def side_effect(adapter_type, **kwargs):
                if "TestAdapter" in adapter_type.__name__:
                    return [PytestAdapter]
                if "CoverageAdapter" in adapter_type.__name__:
                    return [LcovAdapter]
                return []

            mock_get_adapters.side_effect = side_effect

            with (
                patch.object(PytestAdapter, "run") as mock_test_run,
                patch.object(LcovAdapter, "parse") as mock_cov_parse,
            ):
                mock_test_run.return_value = ToolCallResponse(success=True, output="Test OK")
                mock_cov_parse.return_value = ToolCallResponse(success=True, output="Cov OK")

                res = orchestrate_global(config, project_dir=tmp_path)
                assert "test_python_PytestAdapter" in res
                assert res["test_python_PytestAdapter"]["status"] == "success"
                assert "cov_python_LcovAdapter" in res
                assert res["cov_python_LcovAdapter"]["status"] == "success"


def test_legacy_run_lint():
    config = TddHarnessConfig()
    with patch("src.tdd_harness.runner.AdapterRegistry.get_adapters") as mock_get_adapters:
        mock_get_adapters.return_value = [RuffAdapter]
        with patch.object(RuffAdapter, "run") as mock_run:
            mock_run.return_value = ToolCallResponse(success=True, output="Lint passed", data={"return_code": 0})

            res = run_lint(config, file_path="test.py")
            assert res["status"] == "success"
            assert res["stdout"] == "Lint passed"


def test_legacy_wrappers():
    config = TddHarnessConfig()
    with patch("src.tdd_harness.runner.orchestrate_global") as mock_global:
        mock_global.return_value = {"test_python_PytestAdapter": {"status": "success"}}

        res1 = run_test(config)
        res2 = run_coverage(config)

        assert res1 == {"test_python_PytestAdapter": {"status": "success"}}
        assert res2 == {"test_python_PytestAdapter": {"status": "success"}}


def test_progressive_hints():
    from src.tdd_harness.runner import _apply_progressive_hints

    result = {"status": "failed", "stderr": "Error: Line too long E501"}
    tool_config = {"errors": [{"match": "E501", "hints": ["Try breaking the line", "Use a backslash or parenthesis"]}]}

    # 0 failures
    res0 = _apply_progressive_hints(dict(result), 0, tool_config)
    assert "Hint: Try breaking the line" in res0["stderr"]

    # 1 failure
    res1 = _apply_progressive_hints(dict(result), 1, tool_config)
    assert "Hint: Use a backslash or parenthesis" in res1["stderr"]

    # 5 failures (caps at max hints)
    res5 = _apply_progressive_hints(dict(result), 5, tool_config)
    assert "Hint: Use a backslash or parenthesis" in res5["stderr"]
