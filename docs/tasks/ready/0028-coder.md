---
id: "0028"
title: "Implement Red Phase LLM Driver Loop"
dependencies:
  prod: []
  dev: []
target_files:
  - "src/tdd_harness/controller.py"
success_criteria:
  - "Implement `run_red_phase(task_file: Path)` on `TDDLoopController` that orchestrates the Red (Test Generation) phase end-to-end."
  - "The method must use the `ContextBuilder` to assemble the LLM payload per `docs/phases/03-red-test-generation.md`: Task Context, Task Success Criteria, and the target Blue interfaces (stubs generated in Phase 02)."
  - "The method must invoke the LLM with the phase-specific system prompt and OpenAI tool schemas for: `search_symbols`, `get_symbol_source`, `ask_researcher`, `stage_test_implementation`, `success`, `abort`."
  - "The method must execute in a tool-call loop identical in structure to the Blue phase loop."
  - "The `check_red_exit()` validation must be invoked when the LLM calls `success`, confirming at least one test fails with `AssertionError` or `NotImplementedError`."
  - "If `stage_test_implementation` rejects a test (wrong error type, passes unexpectedly), the post-mortem summary must be injected into subsequent LLM prompts."
  - "Add unit tests in `tests/test_controller.py` covering the Red phase loop execution, expected-error enforcement, and post-mortem injection."
---
# Unit of Work: Implement Red Phase LLM Driver Loop

## Context
The CLI currently sets `controller.current_phase = Phase.RED` and immediately moves on. The Red phase is responsible for writing failing tests against the Blue interfaces. The LLM must be prompted with the stub interfaces and given access to `stage_test_implementation` to write tests. Tests must fail specifically due to `AssertionError` or `NotImplementedError` — not syntax errors or import errors.
