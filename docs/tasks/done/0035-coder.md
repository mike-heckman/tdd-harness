---
id: "0035"
title: "Replace pip with uv in install_dependencies"
dependencies:
  prod: []
  dev: []
target_files:
  - "src/tdd_harness/controller.py"
success_criteria:
  - "Replace `subprocess.check_call([sys.executable, '-m', 'pip', 'install', *packages])` in `controller.py:install_dependencies()` (L454) with `subprocess.check_call(['uv', 'pip', 'install', *packages])`."
  - "Verify the command executes correctly within the project's uv-managed virtual environment."
  - "Update any existing tests for `install_dependencies` to assert the new `uv` command invocation."
  - "All existing tests must continue to pass."
---
# Unit of Work: Replace pip with uv in install_dependencies

## Context
The project mandates `uv` as the package manager (per `.agent-context.md` and the `pyproject.toml` configuration), yet the `install_dependencies` tool in `controller.py` uses `subprocess.check_call([sys.executable, "-m", "pip", "install", ...])`. This could install packages outside the `uv`-managed virtual environment, causing dependency drift and violating the project's own toolchain standards.

**Source:** [Claude Opus Analysis — Issue 9](../reports/claude-opus-analysis.md#issue-9-install_dependencies-uses-pip-instead-of-uv)
