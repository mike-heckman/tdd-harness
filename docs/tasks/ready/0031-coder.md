---
id: "0031"
title: "Wire CLI End-to-End: Phase Orchestration with Task File Routing"
dependencies:
  prod: []
  dev: []
target_files:
  - "src/tdd_harness/cli.py"
success_criteria:
  - "Replace the log-only phase transitions in `async_main()` (lines 166-176) with actual invocations of the controller's phase driver methods: `run_blue_phase()`, `run_red_phase()`, `run_green_phase()`, and `run_magenta_loop()`."
  - "The CLI must parse the active task file from `docs/tasks/ready/` (asciibetically first) and pass it to each phase driver."
  - "After successful completion of all phases (including Violet review via `success()`), the task file must be atomically moved from `docs/tasks/ready/` to `docs/tasks/done/`."
  - "If any phase aborts, the task file must remain in `docs/tasks/ready/` and the abort report must be written to `docs/tasks/reports/`."
  - "The `--phase` CLI argument must be honored: if `--phase blue` is passed, execution starts at Blue; if `--phase green` is passed, execution starts at Green (skipping Blue and Red)."
  - "The CLI must instantiate the `LLMClient` (from task 0024) and `Prompt` (from task 0022) and pass them to the controller, replacing the raw `AsyncOpenAI` instantiation currently scattered throughout `controller.py`."
  - "Add or update unit tests in `tests/test_cli.py` covering end-to-end phase sequencing, task file routing, and the `--phase` argument."
---
# Unit of Work: Wire CLI End-to-End: Phase Orchestration with Task File Routing

## Context
The `async_main()` function in `cli.py` currently only logs phase transitions (`print("Transitioning to Blue phase...")`) and sets `controller.current_phase` without invoking any LLM driver loops. The only phase with any real execution is Magenta (via `run_magenta_loop()`), and even that contains stubs. This task wires the full execution pipeline: Amber → Blue → Red → Green → Magenta → Violet, routing the active task file through each phase.
