---
id: "0020"
title: "Integrate TDD loop orchestration directly into CLI"
dependencies:
  prod: []
  dev: []
target_files:
  - "src/tdd_harness/cli.py"
success_criteria:
  - "Integrate TDDLoopController execution flow into the CLI async_main."
  - "Make the CLI the main entry point to drive the TDD phases (Amber -> Blue -> Red -> Green -> Magenta)."
  - "Verify that the loop controller uses the resolved project configuration directory."
  - "CLI must run the Amber pre-flight validation on startup and gracefully transition through phases based on task readiness."
---
# Unit of Work: Integrate TDD loop orchestration directly into CLI

## Context
We are ignoring `scripts/run.sh` and moving to the CLI as the main orchestration point. The CLI must initialize the `TDDLoopController` and execute the TDD loop phases instead of only running index repo.
