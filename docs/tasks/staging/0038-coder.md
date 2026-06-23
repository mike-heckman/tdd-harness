---
id: "0038"
title: "Standardize import style to relative imports"
dependencies:
  prod: []
  dev: []
target_files:
  - "src/tdd_harness/llm.py"
  - "src/tdd_harness/sub_agents.py"
  - "src/tdd_harness/tracker.py"
  - "src/tdd_harness/adapters/base.py"
  - "src/tdd_harness/adapters/pytest_adapter.py"
  - "src/tdd_harness/adapters/ruff_adapter.py"
  - "src/tdd_harness/adapters/lcov_adapter.py"
success_criteria:
  - "Convert all `from src.tdd_harness.X import Y` absolute imports within the `tdd_harness` package to `from .X import Y` relative imports."
  - "Adapter modules in `src/tdd_harness/adapters/` must use `from ..models.tool import ...` style relative imports."
  - "No absolute `from src.tdd_harness` imports remain in any module under `src/tdd_harness/`."
  - "All existing tests must continue to pass."
  - "Ruff linting must pass cleanly."
---
# Unit of Work: Standardize import style to relative imports

## Context
The project mixes absolute `from src.tdd_harness.X` imports (in `llm.py`, `sub_agents.py`, `tracker.py`, and adapter modules) with relative `from .X` imports (in `controller.py`, `cli.py`, `config.py`). This works due to the `hatch` build configuration but makes the package fragile to restructuring and violates PEP 8's recommendation for consistency within a package.

**Source:** [Claude Opus Analysis — Issue 8](../reports/claude-opus-analysis.md#issue-8-mixed-import-styles-from-srctdd_harness-vs-relative)
