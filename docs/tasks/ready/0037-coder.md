---
id: "0037"
title: "Replace singletons with dependency injection"
dependencies:
  prod: []
  dev: []
target_files:
  - "src/tdd_harness/config.py"
  - "src/tdd_harness/context.py"
  - "src/tdd_harness/controller.py"
  - "src/tdd_harness/llm.py"
  - "src/tdd_harness/cli.py"
  - "tests/conftest.py"
success_criteria:
  - "Remove the `__new__` singleton override from `HarnessContext` in `config.py`. Convert it to a regular class that is instantiated once and passed via constructor."
  - "Remove the `__new__` singleton override from `ContextBuilder` in `context.py`. Convert it to a regular class that is instantiated once and passed via constructor."
  - "Update `TDDLoopController.__init__()` to accept `HarnessContext` and `ContextBuilder` as constructor parameters."
  - "Update `LLMClient` to accept `ContextBuilder` as a constructor parameter instead of instantiating a new singleton internally."
  - "Update `cli.py:async_main()` to instantiate `HarnessContext` and `ContextBuilder` and inject them into the controller and LLM client."
  - "Remove the `HarnessContext._instance` reset logic from `conftest.py` (it should no longer be needed)."
  - "Remove the `pytest`-detection conditional (`if 'pytest' in sys.modules`) from `HarnessContext.__new__`."
  - "All existing tests must continue to pass."
---
# Unit of Work: Replace singletons with dependency injection

## Context
Both `HarnessContext` and `ContextBuilder` use the `__new__`-override singleton pattern, creating global mutable state that bleeds across test runs. The `conftest.py` fixture manually resets `ContextBuilder._instance = None` between tests, and `HarnessContext` injects a `"test-"` prefix when `pytest` is in `sys.modules` — a runtime behavior conditional on the test runner. Replacing singletons with constructor injection eliminates cross-test contamination risks and removes the test-runner-aware code smell.

**Source:** [Claude Opus Analysis — Issue 2](../reports/claude-opus-analysis.md#issue-2-singleton-anti-patterns)
