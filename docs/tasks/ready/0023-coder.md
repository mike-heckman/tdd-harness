---
id: "0023"
title: "Implement MCP Client with Real Server Connectivity"
dependencies:
  prod:
    - mcp
  dev: []
target_files:
  - "src/tdd_harness/mcp_client.py"
success_criteria:
  - "Replace the stub `connect()` method in `MCPClient` with a real implementation that establishes a connection to the configured MCP server using the `mcp` library's `ClientSession`."
  - "Replace the stub `get_tools()` method to query the connected server session for available tools and return them as a list of tool definition dictionaries."
  - "Replace the stub `call_tool()` method to dispatch tool calls to the connected server session and return the result."
  - "The `handle_failure()` method must correctly implement the `restart_policy` behavior: `exit` terminates the process, `on-failure` attempts reconnection once, and `always` retries indefinitely."
  - "If no MCP server config is provided (empty dict), all methods must return gracefully without attempting connection (preserving backward compatibility with existing tests)."
  - "Add unit tests in `tests/test_mcp_client.py` covering the connection lifecycle, error handling, and restart policy branching."
---
# Unit of Work: Implement MCP Client with Real Server Connectivity

## Context
The `MCPClient` class currently contains only stubs that return empty results. It imports `ClientSession` from `mcp` but never uses it. The `ToolRegistry` depends on `MCPClient.get_tools()` to discover MCP tools during initialization and `MCPClient.call_tool()` to dispatch tool calls. Without a real implementation, no MCP tools (jCodeMunch, jDocMunch) can be used at runtime.
