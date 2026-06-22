---
id: "0027"
title: "Implement Blue Phase LLM Driver Loop"
dependencies:
  prod: []
  dev: []
target_files:
  - "src/tdd_harness/controller.py"
success_criteria:
  - "Implement `run_blue_phase(task_file: Path)` on `TDDLoopController` that orchestrates the Blue (Structural Blueprint) phase end-to-end."
  - "The method must use the `ContextBuilder` to assemble the LLM payload per `docs/phases/02-blue-structural-blueprint.md`: Task Context, Task Success Criteria, and current file source (if modifying an existing file)."
  - "The method must invoke the LLM via `AsyncOpenAI` (or the refactored `LLMClient` if 0024 is complete) with the phase-specific system prompt, the assembled context payload, and OpenAI tool schemas for: `search_symbols`, `get_symbol_source`, `ask_researcher`, `stage_implementation`, `success`, `abort`."
  - "The method must execute in a tool-call loop: processing LLM tool calls, dispatching them via `registry.dispatch()`, and feeding results back until the LLM calls `success` or `abort`, or the `AntiThrashingTracker` triggers an abort."
  - "The `check_blue_exit()` method must be fully implemented: parse the test count from `PytestAdapter`'s reportlog output and verify the count has not decreased compared to the initial count captured at phase entry."
  - "Past failure summaries must be injected into subsequent LLM prompts if `stage_implementation` returns a post-mortem."
  - "Add unit tests in `tests/test_controller.py` covering the Blue phase loop execution, tool dispatch, and exit validation."
---
# Unit of Work: Implement Blue Phase LLM Driver Loop

## Context
The CLI currently sets `controller.current_phase = Phase.BLUE` and immediately moves on. There is no LLM invocation. The Blue phase is responsible for generating rigid interfaces, stubs, and abstract class definitions. The LLM needs to be prompted with the task context and given access to `stage_implementation` to write code, then `success` to signal completion. The `check_blue_exit` method also has a stub `pass` where it should verify test counts have not decreased.
