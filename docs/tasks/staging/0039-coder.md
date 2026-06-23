---
id: "0039"
title: "Define Protocol classes for loose object type annotations"
dependencies:
  prod: []
  dev: []
target_files:
  - "src/tdd_harness/protocols.py"
  - "src/tdd_harness/llm.py"
  - "src/tdd_harness/registry.py"
  - "src/tdd_harness/cli.py"
success_criteria:
  - "Create a new `src/tdd_harness/protocols.py` module containing `Protocol` class definitions."
  - "Define `ConfigLoaderProtocol` with a `get_config() -> TddHarnessConfig` method signature."
  - "Define `TrackerProtocol` with `record_tool_call()`, `should_abort()`, `get_previous_failures()`, and `reset()` method signatures."
  - "Replace `config_loader: object` in `LLMClient.__init__()` with `config_loader: ConfigLoaderProtocol`."
  - "Replace `tracker: object | None` in `ToolRegistry.__init__()` with `tracker: TrackerProtocol | None`."
  - "Replace `msg: object` and `registry: object | None` in `LLMClient._handle_tool_calls()` with properly typed parameters."
  - "Remove the `_ConfigLoaderWrapper` ad-hoc class from `cli.py` by either having `TddHarnessConfig` conform to `ConfigLoaderProtocol` or simplifying `LLMClient` to accept the config directly."
  - "Remove all `# type: ignore` comments that were working around these loose types."
  - "Pyright must pass without new errors on the modified files."
  - "All existing tests must continue to pass."
---
# Unit of Work: Define Protocol classes for loose object type annotations

## Context
The codebase frequently uses `object` as a type annotation (e.g., `config_loader: object`, `tracker: object | None`, `msg: object`) with `# type: ignore` comments to avoid circular imports or complex typing. While `# Reason:` comments explain the rationale, this undermines Pyright's ability to catch interface mismatches. The project already has a good example of this pattern done right — `MCPClientProtocol` in `registry.py` — which should be extended to cover the remaining loose types. Additionally, the `_ConfigLoaderWrapper` ad-hoc class in `cli.py` exists solely to satisfy the dynamically-called `.get_config()` interface, and should be eliminated as part of this work.

**Source:** [Claude Opus Analysis — Issue 5](../reports/claude-opus-analysis.md#issue-5-object-type-annotations-as-escape-hatches) and [Issue 10](../reports/claude-opus-analysis.md#issue-10-_configloaderwrapper-ad-hoc-class-in-cli)
