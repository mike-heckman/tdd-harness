---
id: "0036"
title: "Extract TDDLoopController into focused components"
dependencies:
  prod: []
  dev: []
target_files:
  - "src/tdd_harness/controller.py"
  - "src/tdd_harness/security.py"
  - "src/tdd_harness/task_loader.py"
  - "tests/test_controller.py"
success_criteria:
  - "Extract `_is_path_allowed()`, `read_file_safe()`, and `write_file_safe()` into a new `SecurityInterceptor` class in `src/tdd_harness/security.py`."
  - "Extract `_process_ready_tasks()` and `_validate_and_provision_task()` into a new `TaskLoader` class in `src/tdd_harness/task_loader.py`."
  - "Extract `install_dependencies()`, `search_web()`, and `download_to_reference()` out of the controller into an appropriate utility module."
  - "`TDDLoopController.__init__()` must accept the extracted components via constructor injection."
  - "`TDDLoopController` must remain under 600 lines after extraction."
  - "Write unit tests for the newly extracted `SecurityInterceptor` and `TaskLoader` classes."
  - "All 141+ existing tests must continue to pass without modification to their assertions (mock targets may be updated)."
  - "Test coverage must remain at or above 94%."
---
# Unit of Work: Extract TDDLoopController into focused components

## Context
The `TDDLoopController` class in `controller.py` is a ~1000-line monolith containing file security enforcement, phase validation logic, all 5 phase orchestration loops, backup/revert logic, post-mortem generation, task file parsing & provisioning, dependency installation, web search & download functionality, and sub-agent coordination. This violates the Single Responsibility Principle. Extracting cohesive groups of functionality into dedicated classes will improve maintainability, testability, and readability.

**Source:** [Claude Opus Analysis — Issue 1](../reports/claude-opus-analysis.md#issue-1-controllerpy-god-object-1002-lines)
