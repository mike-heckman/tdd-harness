---
id: "0030"
title: "Complete Magenta Phase LLM Coverage Loop"
dependencies:
  prod: []
  dev: []
target_files:
  - "src/tdd_harness/controller.py"
success_criteria:
  - "Replace the commented-out stub in `run_magenta_loop()` (lines 715-721) with a real LLM invocation that prompts the model to write additional tests covering the missing lines."
  - "The LLM must be given the file source code, specific uncovered line numbers, and access to `stage_test_implementation`, `search_symbols`, `get_symbol_source`, `ask_researcher`, `success`, and `abort` tools."
  - "The LLM invocation must use a tool-call loop identical in structure to the other phase loops."
  - "The `check_magenta_exit()` method must be invoked using the actual coverage percentage and uncovered line count parsed from the `LcovParser` output after each LLM attempt."
  - "Replace the `TODO: dynamic handling` comment on line 738 with proper error reporting that writes to `docs/tasks/reports/` before aborting."
  - "The `AntiThrashingTracker` must be integrated to prevent infinite loops if the LLM cannot increase coverage."
  - "Add unit tests in `tests/test_controller.py` covering the Magenta loop LLM invocation, coverage re-check, and abort on max attempts."
---
# Unit of Work: Complete Magenta Phase LLM Coverage Loop

## Context
The `run_magenta_loop()` method has the correct outer structure (parse coverage, iterate files, retry loop) but the inner LLM invocation is commented out with `# In a real implementation this sends the context to the LLM agent`. The method also has a `TODO: dynamic handling` where it aborts. This task completes the loop by invoking the LLM to write tests that cover the missing lines identified by `LcovParser`.
