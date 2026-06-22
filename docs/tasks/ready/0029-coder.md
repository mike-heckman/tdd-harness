---
id: "0029"
title: "Implement Green Phase LLM Driver Loop"
dependencies:
  prod: []
  dev: []
target_files:
  - "src/tdd_harness/controller.py"
success_criteria:
  - "Implement `run_green_phase(task_file: Path)` on `TDDLoopController` that orchestrates the Green (Develop Implementation) phase end-to-end."
  - "The method must use the `ContextBuilder` to assemble the LLM payload per `docs/phases/04-green-develop-implementation.md`: Original Blue Stubs, Test Concepts (from the `-reasoning.yaml` sidecar files), Previous failure summaries, Latest Failed Draft, and Post-Mortem Summary & Guidance."
  - "The method must invoke the LLM with the phase-specific system prompt and OpenAI tool schemas for: `search_symbols`, `get_symbol_source`, `ask_researcher`, `stage_implementation`, `success`, `abort`."
  - "The method must execute in a tool-call loop with post-mortem summarization and file revert on failure (leveraging the existing `stage_implementation` method)."
  - "The `check_green_exit()` validation must be invoked when the LLM calls `success`, confirming all tests pass."
  - "The `AntiThrashingTracker` must be checked after each tool dispatch. If `should_abort()` returns `True`, the loop must terminate with a dirty exit per SDD §5."
  - "Add unit tests in `tests/test_controller.py` covering the Green phase loop execution, post-mortem injection on failure, and anti-thrashing abort."
---
# Unit of Work: Implement Green Phase LLM Driver Loop

## Context
The CLI currently sets `controller.current_phase = Phase.GREEN` and immediately moves on. The Green phase is the core implementation phase where the LLM writes production code to satisfy failing tests. It must leverage the existing `stage_implementation` tool (which already handles lint/test/revert/post-mortem) and integrate the `AntiThrashingTracker` to prevent infinite failure loops per SDD §5.
