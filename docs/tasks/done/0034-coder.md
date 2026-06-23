---
id: "0034"
title: "Replace sys.exit() with dedicated exceptions in library code"
dependencies:
  prod: []
  dev: []
target_files:
  - "src/tdd_harness/controller.py"
  - "src/tdd_harness/mcp_client.py"
success_criteria:
  - "Define a `HarnessAbort` exception in a shared module (e.g., `models/` or a new `exceptions.py`)."
  - "Define an `MCPFatalError` exception in the same module."
  - "Replace `sys.exit(1)` in `controller.py:abort()` (L262) with `raise HarnessAbort(reason)`."
  - "Replace `sys.exit(1)` in `mcp_client.py:handle_failure()` (L52) with `raise MCPFatalError(error_msg)`."
  - "Update `cli.py:main()` and `cli.py:async_main()` to catch `HarnessAbort` and `MCPFatalError`, printing the message and calling `sys.exit(1)` at the CLI boundary only."
  - "Update all existing tests that use `pytest.raises(SystemExit)` to assert on the new exception types instead."
  - "All existing tests must continue to pass."
  - "No `sys.exit()` calls remain outside of `cli.py`."
---
# Unit of Work: Replace sys.exit() with dedicated exceptions in library code

## Context
The `controller.py:abort()` method and `mcp_client.py:handle_failure()` both call `sys.exit(1)` directly from library code. This makes the code untestable without mocking `sys.exit`, prevents clean embedding in other applications, and forces the test suite to use `pytest.raises(SystemExit)` as a workaround. Library code should raise exceptions; only the CLI entry point should call `sys.exit()`.

**Source:** [Claude Opus Analysis — Issue 6](../reports/claude-opus-analysis.md#issue-6-sysexit1-called-from-library-code)
