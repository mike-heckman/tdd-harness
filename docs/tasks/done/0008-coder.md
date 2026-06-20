---
id: 0008
title: 5-Phase Controller & AST Context Injection
success_criteria:
- Implement programmatic tool-access checks (`ro` vs `rw`) per phase (Amber, Blue,
  Red, Green) to deny standard write tool calls to restricted directories.
- 'Create a `stage_test_implementation(filepath: str, code: str, test_name: str, test_concept: str)` native tool specifically for the Red Phase.'
- When called, the tool writes the `code` to the file, backing up the current file incrementally to `.tdd-harness/.cache/`. During the Red phase, validate that tests fail strictly with an `AssertionError` or `NotImplementedError` via the `TestAdapter` by running targeted tests on the file. Reject syntax/compilation errors and revert from cache.
- Instead of AST parsing, write the `test_concept` out to disk inside `<test_filename>-reasoning.yaml` mapped by the `test_name` and then the current execution's `session_id`.
- Trigger targeted MCP Server index updates (e.g., `index_folder` on the specifically
  modified directory) upon successful phase transitions to keep search context up-to-date
  efficiently.
- Call full repository indexers (`index_repo`, `doc_index_repo`) automatically during
  Harness startup.
dependencies:
  prod: []
  dev: []
---
# Unit of Work: 5-Phase Controller & AST Context Injection

## Context
Implementing the core state machine for the Amber, Blue, Red, and Green phases. See files in ./docs/phases/ for additional detail.
