---
id: "0043"
title: "Replace global mutable config cache with ConfigResolver class"
dependencies:
  prod: []
  dev: []
target_files:
  - "src/tdd_harness/config.py"
  - "tests/test_config.py"
success_criteria:
  - "Create a `ConfigResolver` class that encapsulates the directory resolution logic currently in `build_cache_tdd_directories()` and `resolve_config_directory()`."
  - "The `ConfigResolver` must hold its cache as an instance attribute, not a module-level global."
  - "Remove the module-level `CACHE_TDD_DIRECTORIES` global list."
  - "Remove the `force` parameter (it is unused in the codebase)."
  - "Update all call sites that use `resolve_config_directory()` or `build_cache_tdd_directories()` to use the new `ConfigResolver` instance."
  - "Write unit tests verifying that two separate `ConfigResolver` instances do not share state."
  - "All existing tests must continue to pass without manual cache clearing."
---
# Unit of Work: Replace global mutable config cache with ConfigResolver class

## Context
`CACHE_TDD_DIRECTORIES` in `config.py` is a module-level mutable global list that persists across function calls. The `force` parameter for cache busting exists but is not used anywhere in the codebase. Tests need to manually clear this state or risk inheriting stale directory lists from prior test cases. Encapsulating this into an instance-scoped class eliminates the cross-test contamination risk.

**Source:** [Claude Opus Analysis — Issue 3](../reports/claude-opus-analysis.md#issue-3-global-mutable-cache-in-config-module)
