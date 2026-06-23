---
id: "0041"
title: "Add read_file to phase-gated tool schemas"
dependencies:
  prod: []
  dev: []
target_files:
  - "src/tdd_harness/tool_schemas.py"
success_criteria:
  - "Add a `read_file` entry to the `AVAILABLE_TOOLS` list in `tool_schemas.py` with `valid_phases` set to `['blue', 'red', 'green', 'magenta']`."
  - "The schema must match the signature registered by `controller.register_python_tool(self.read_file_safe, name='read_file')` — a single required `path` parameter of type `string`."
  - "Verify that `get_tools_for_phase()` returns `read_file` for all four active phases."
  - "Write a unit test asserting `read_file` is present in the schemas returned by `get_tools_for_phase()` for each phase."
  - "All existing tests must continue to pass."
---
# Unit of Work: Add read_file to phase-gated tool schemas

## Context
The `AVAILABLE_TOOLS` list in `tool_schemas.py` includes `stage_implementation`, `stage_test_implementation`, `success`, `abort`, `search_symbols`, `get_symbol_source`, and `ask_researcher` — but does not include `read_file`. While `read_file` is registered at runtime via `controller.register_python_tool()`, it is not exposed in the phase-gated schema list passed to `get_tools_for_phase()`. This means the LLM may not "see" the `read_file` tool depending on how tools are assembled for the chat call.

**Source:** [Claude Opus Analysis — Issue 11](../reports/claude-opus-analysis.md#issue-11-missing-read_file-tool-in-phase-schemas)
