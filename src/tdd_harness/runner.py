"""
Subprocess command runner and test orchestrator for tdd-harness.
"""

import importlib
import pkgutil
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .adapters import __name__ as adapters_pkg_name
from .adapters import base
from .config import TddHarnessConfig
from .models.tool import ToolCall


class AdapterRegistry:
    """
    Registry to natively locate and provide all toolchain adapters.

    This class handles the dynamic discovery of Adapter subclasses within
    the adapters module, enabling a zero-config architecture.
    """

    _adapters: list[type[base.Adapter]] = []

    @classmethod
    def discover(cls) -> None:
        """
        Discover all adapter subclasses by importing all modules in adapters package.

        Iterates over the adapters package using pkgutil to ensure all subclasses
        are loaded into memory, allowing __subclasses__() to find them.
        """
        if cls._adapters:
            return

        # Import all modules in adapters package to trigger subclass registration
        package_path = Path(__file__).parent / "adapters"
        for _, modname, _ in pkgutil.iter_modules([str(package_path)], adapters_pkg_name + "."):
            importlib.import_module(modname)

        def get_subclasses(c: type) -> list[type]:
            """
            Recursively find all subclasses of a given class.

            Args:
                c: The base class to inspect.

            Returns:
                A list of all discovered subclasses.
            """
            subclasses = c.__subclasses__()
            for d in list(subclasses):
                subclasses.extend(get_subclasses(d))
            return subclasses

        all_subclasses = get_subclasses(base.Adapter)
        cls._adapters = [
            c for c in all_subclasses if getattr(c, "language", None) and not getattr(c, "__abstractmethods__", None)
        ]

    @classmethod
    def get_adapters(
        cls, adapter_type: type[base.Adapter] = base.Adapter, extension: str | None = None, language: str | None = None
    ) -> list[type[base.Adapter]]:
        """
        Retrieve adapters matching criteria.

        Args:
            adapter_type: The base adapter type to filter by (e.g. TestAdapter).
            extension: The file extension the adapter must support.
            language: The programming language the adapter must target.

        Returns:
            A list of adapter classes matching the provided constraints.
        """
        cls.discover()
        matches = []
        for adapter_cls in cls._adapters:
            if not issubclass(adapter_cls, adapter_type):
                continue
            if extension and extension not in adapter_cls.supported_extensions:
                continue
            if language and language != adapter_cls.language:
                continue
            matches.append(adapter_cls)
        return matches


def parse_active_languages(project_dir: Path | None = None) -> list[str]:
    """
    Parse .languages file to determine active languages.

    Args:
        project_dir: The directory containing the .languages file. Defaults to cwd.

    Returns:
        A list of active language identifiers (e.g. 'python').
    """
    if project_dir:
        lang_file = Path(project_dir) / ".languages"
    else:
        lang_file = Path.cwd() / ".languages"

    active = []
    if lang_file.exists():
        with open(lang_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("HAS_") and "=" in line:
                    key, val = line.split("=", 1)
                    if val.lower() == "true":
                        if key == "HAS_PY":
                            active.append("python")
                        elif key == "HAS_TS":
                            active.append("typescript")
                        elif key == "HAS_JS":
                            active.append("javascript")
    return active


def orchestrate_targeted(
    config: TddHarnessConfig, target_path: str
) -> dict[str, Any]:  # Reason: Any used for dynamic json output values
    """
    Targeted execution: routes to specific adapters based on file extension.

    Args:
        config: The harness configuration object.
        target_path: The file path to execute tools against.

    Returns:
        A dictionary mapping adapter names to their execution results.
    """
    ext = Path(target_path).suffix
    test_adapters = AdapterRegistry.get_adapters(adapter_type=base.TestAdapter, extension=ext)

    results = {}
    for adapter_cls in test_adapters:
        adapter = adapter_cls()
        response = adapter.run(ToolCall(tool_name="test", arguments={"file_path": target_path}))
        results[adapter_cls.__name__] = {
            "status": "success" if response.success else "failed",
            "stdout": response.output or "",
            "stderr": "\n".join(response.errors) if response.errors else "",
        }
    return results


def orchestrate_defined(
    config: TddHarnessConfig, target_node: str
) -> dict[str, Any]:  # Reason: Any used for dynamic json output values
    """
    Defined execution: parses a node ID to route based on extension.

    Args:
        config: The harness configuration object.
        target_node: A pytest-like node ID (e.g., file.py::test_case).

    Returns:
        A dictionary mapping adapter names to their execution results.
    """
    file_part = target_node.split("::")[0]
    return orchestrate_targeted(config, file_part)


def orchestrate_global(
    config: TddHarnessConfig, project_dir: Path | None = None
) -> dict[str, Any]:  # Reason: Any used for dynamic json output values
    """
    Global execution: runs all adapters for active languages found in .languages.

    This function will generate coverage artifacts natively within a single pass.

    Args:
        config: The harness configuration object.
        project_dir: The project root directory. Defaults to cwd.

    Returns:
        A dictionary containing both test and coverage execution results.
    """
    active_langs = parse_active_languages(project_dir)
    results = {}

    Path("temp").mkdir(exist_ok=True)
    cov_dir = tempfile.mkdtemp(dir="temp/")

    try:
        # Run tests for all active languages
        for lang in active_langs:
            test_adapters = AdapterRegistry.get_adapters(adapter_type=base.TestAdapter, language=lang)
            for adapter_cls in test_adapters:
                adapter = adapter_cls()
                response = adapter.run(ToolCall(tool_name="test", arguments={"coverage_dir": cov_dir}))
                results[f"test_{lang}_{adapter_cls.__name__}"] = {
                    "status": "success" if response.success else "failed",
                    "stdout": response.output or "",
                    "stderr": "\n".join(response.errors) if response.errors else "",
                }

        # Produce unified coverage using coverage adapters
        for lang in active_langs:
            cov_adapters = AdapterRegistry.get_adapters(adapter_type=base.CoverageAdapter, language=lang)
            for adapter_cls in cov_adapters:
                adapter = adapter_cls()
                response = adapter.parse(ToolCall(tool_name="coverage", arguments={"coverage_dir": cov_dir}))  # type: ignore
                results[f"cov_{lang}_{adapter_cls.__name__}"] = {
                    "status": "success" if response.success else "failed",
                    "stdout": response.output or "",
                    "stderr": "\n".join(response.errors) if response.errors else "",
                }
    finally:
        shutil.rmtree(cov_dir, ignore_errors=True)

    return results


# Legacy wrapper implementations routing via the new orchestrated execution
def run_test_and_coverage(config: TddHarnessConfig, file_path: str | None = None) -> dict[str, Any]:  # Reason: Any
    """
    Legacy wrapper for test and coverage.
    """
    if file_path:
        return orchestrate_targeted(config, file_path)
    return orchestrate_global(config)


def run_lint(
    config: TddHarnessConfig, directories: list | None = None, file_path: str | None = None
) -> dict[str, Any]:  # Reason: Any
    """
    Legacy wrapper for lint.
    """
    # Lint specifically routes based on file_path extension or runs global lint
    if file_path:
        ext = Path(file_path).suffix
        adapters = AdapterRegistry.get_adapters(adapter_type=base.LintAdapter, extension=ext)
    else:
        active_langs = parse_active_languages()
        adapters = []
        for lang in active_langs:
            adapters.extend(AdapterRegistry.get_adapters(adapter_type=base.LintAdapter, language=lang))

    # Default fallback to python if no languages file found during legacy calls
    if not adapters:
        adapters = AdapterRegistry.get_adapters(adapter_type=base.LintAdapter, language="python")

    results = {}
    for adapter_cls in adapters:
        adapter = adapter_cls()
        args = {}
        if file_path:
            args["file_path"] = file_path
        if directories:
            args["directories"] = directories
        response = adapter.run(ToolCall(tool_name="lint", arguments=args))

        # Legacy returns single result format
        return {
            "status": "success" if response.success else "failed",
            "return_code": response.data.get("return_code", 0) if response.data else 0,
            "stdout": response.output or "",
            "stderr": "\n".join(response.errors) if response.errors else "",
        }
    return results


def run_test(config: TddHarnessConfig) -> dict[str, Any]:  # Reason: Any
    """
    Legacy wrapper for run test.
    """
    return run_test_and_coverage(config)


def run_coverage(config: TddHarnessConfig) -> dict[str, Any]:  # Reason: Any
    """
    Legacy wrapper for run coverage.
    """
    return run_test_and_coverage(config)
