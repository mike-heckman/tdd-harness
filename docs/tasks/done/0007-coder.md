---
id: '0007'
title: Toolchain Adapters Interface & Config Dictionary
success_criteria:
- 'Rename `tdd-harness.yaml` to `config.yaml` and update the schema to support an
  `adapters` configuration block (e.g., `test: pytest`, `lint: ruff`, `coverage: lcov`).'
- Create `TestAdapter`, `LintAdapter`, and `CoverageAdapter` base classes defining
  uniform interfaces.
- The `TestAdapter` must support running a single file or the entire test suite.
- The `LintAdapter` must support running against a single file or the entire codebase.
- Implement `PytestAdapter` that uses `pytest --report-log` to parse specific exception
  types (e.g., `AssertionError` vs `SyntaxError`).
- Implement `RuffAdapter` for Python linting.
- Implement `LcovAdapter` (using `generate-unified-coverage.py`) for coverage parsing.
dependencies:
  prod: []
  dev:
  - pytest
  - ruff
---
# Unit of Work: Toolchain Adapters Interface & Config Dictionary

## Context
We are migrating to a 5-Phase TDD Pipeline that requires language-agnostic testing, linting, and coverage execution.
This task focuses on creating separate adapter interfaces for tests, linting, and coverage to support both global and file-specific execution.
