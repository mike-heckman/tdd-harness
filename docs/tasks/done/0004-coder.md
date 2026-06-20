# Task: 0004-coder - MCP Client & Tool Registry

## Context
Create the unified tool registry system. This component must act as a Model Context Protocol (MCP) client, loading external MCP servers as well as dynamically importing configured Python extensions. The central registry serves all tools to the LLM.

## Target Files
- `src/tdd_harness/registry.py`
- `src/tdd_harness/mcp_client.py`
- `tests/test_registry.py`

## Instructions
- **CRITICAL**: Do not write a custom MCP client from scratch. You MUST use the official `mcp` Python SDK (Model Context Protocol package) to handle the JSON-RPC stdio transport.
- Implement an MCP Client utilizing the official `mcp` SDK to connect to standard stdio-based MCP servers defined in the `mcp_servers` configuration block.
- Implement a Python extension loader that dynamically imports local modules, exposing decorated `@tool` functions.
- Centralize all loaded tools (MCP tools and Python extensions) into a unified registry.
- Generate standard OpenAI-compatible tool schemas from the unified registry so the LLM adapter can expose them.
- Implement an execution dispatcher that routes incoming tool calls back to the correct MCP server or Python function.

## Success Criteria
- Registry successfully initializes MCP connections and parses available tools.
- Local Python functions are seamlessly wrapped into the unified registry.
- Tool schemas match the OpenAI tool specification.
- Execution dispatcher accurately calls MCP tools or local functions with correct arguments and captures responses.
- Unit tests written in `tests/test_registry.py`.
