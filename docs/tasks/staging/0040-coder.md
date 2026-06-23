---
id: "0040"
title: "DRY up phase loop duplication in controller"
dependencies:
  prod: []
  dev: []
target_files:
  - "src/tdd_harness/controller.py"
  - "tests/test_controller.py"
success_criteria:
  - "Extract the shared loop structure from `run_blue_phase`, `run_red_phase`, `run_green_phase`, and `run_magenta_loop` into a reusable template method (e.g., `_run_phase_loop(phase, context_assembler_fn)`)."
  - "The template method must handle: setting `current_phase`, resetting tracker, entering the `while loop_active` loop, calling `llm_client.chat()`, checking `_phase_successful`, and checking `tracker.should_abort()`."
  - "Each phase method must supply only its unique behavior via a context assembler callback or strategy object (e.g., task parsing, test concept loading for Green, per-file coverage for Magenta)."
  - "The duplicated context assembly pattern (parse frontmatter → clear ContextBuilder → add phase prompt + task context + file sources) must be consolidated."
  - "The duplicated post-mortem injection pattern must be consolidated."
  - "All existing tests must continue to pass."
  - "Test coverage must remain at or above 94%."
---
# Unit of Work: DRY up phase loop duplication in controller

## Context
The four phase runner methods (`run_blue_phase`, `run_red_phase`, `run_green_phase`, `run_magenta_loop`) share an almost identical structure: set phase → parse task file → clear ContextBuilder → add phase prompt + task context + file sources → get tools → reset tracker → enter while loop → call LLM → check success → check abort. The Green and Magenta phases add slight variations (test concepts, per-file coverage), but the core loop structure is copy-pasted across ~340 lines. This DRY violation compounds maintenance cost — any bug fix or behavioral change must be applied to all four methods.

**Source:** [Claude Opus Analysis — Issue 7](../reports/claude-opus-analysis.md#issue-7-phase-loop-duplication)
