---
id: '0010'
title: Tool Registry & Tracker Updates for Progressive Errors
success_criteria:
- Add `detailed_description` (and optional `syntax_examples`) to the `ToolEntry` class.
- Update `get_openai_schemas()` in `registry.py` to only expose the short `description`
  field.
- 'Register a new native tool `get_tool_help(tool_name: str)` in the `ToolRegistry`
  that returns the `detailed_description` and schema of the requested tool.'
- Update `AntiThrashingTracker` (`tracker.py`) to track `consecutive_tool_failures`
  per tool name. The counter must only reset when the specific tool succeeds.
- Update `ToolRegistry.dispatch()` to fetch `previous_failures` from the tracker.
- In `dispatch()`, inject `previous_failures` into the `**arguments` payload for Python
  tools.
- Refactor the Config Loader (`src/tdd_harness/config.py`) to parse tool definitions
  from `.tdd-harness/tools/*.yaml` files. Each YAML file supports a `config` block
  (MCP command/env, `restart_policy` default="exit") and a `tools` block mapping tool
  names to progressive errors.
- Update `mcp_client.py` to implement a Docker-like restart policy (`exit`, `always`,
  `on-failure`) for MCP servers. If the policy is `exit`, the harness must gracefully
  crash and exit on MCP failure.
- 'In `dispatch()`, wrap MCP tool calls: if an MCP tool fails, scan its configured
  `errors` array using fast substring matching (or regex if explicitly configured).
  If matched, append the progressive hint based on the `previous_failures` count.
  If no match is found, append nothing.'
- For Native Python tools, pass their extracted config block into them during initialization
  so they can handle their own progressive logic natively.
dependencies:
  prod:
  - pyyaml
  dev: []
---
# Unit of Work: Tool Registry & Tracker Updates for Progressive Errors

## Context
Implement condensed tool schemas, a native `get_tool_help` tool, and the failure-tracking injection loop to reduce token consumption and guide the LLM when it fails.
