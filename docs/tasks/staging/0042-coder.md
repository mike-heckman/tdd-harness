---
id: "0042"
title: "Add graceful shutdown for MCP connections"
dependencies:
  prod: []
  dev: []
target_files:
  - "src/tdd_harness/mcp_client.py"
  - "src/tdd_harness/cli.py"
  - "tests/test_mcp_client.py"
success_criteria:
  - "Implement `__aenter__` and `__aexit__` on `MCPClient` to support `async with` context manager usage."
  - "`__aexit__` must call `self.close()` to properly clean up `AsyncExitStack` resources."
  - "Update `cli.py:async_main()` to use `async with mcp_client:` or a `try/finally` block that guarantees `mcp_client.close()` is called on both normal exit and abort."
  - "Write a unit test verifying that `close()` is called when the context manager exits."
  - "Write a unit test verifying that `close()` is called even when an exception occurs within the context manager."
  - "All existing tests must continue to pass."
---
# Unit of Work: Add graceful shutdown for MCP connections

## Context
The `MCPClient` class has a `close()` method that calls `self.exit_stack.aclose()` and resets the session, but the CLI's `async_main()` never calls it. If the harness aborts (previously via `sys.exit(1)`, now via exception), the `AsyncExitStack` resources — including any open MCP server stdio connections — are leaked. Implementing the async context manager protocol ensures cleanup happens regardless of how execution terminates.

**Source:** [Claude Opus Analysis — Issue 12](../reports/claude-opus-analysis.md#issue-12-no-graceful-shutdown-for-mcp-connections)
