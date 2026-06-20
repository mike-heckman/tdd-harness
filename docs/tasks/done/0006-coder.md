---
id: "0006"
title: "TDD Loop Controller and File Security Interceptors"
target_files:
  - "src/tdd_harness/controller.py"
  - "tests/test_controller.py"
success_criteria:
  - "Implement the specialized TDD Loop Controller state machine."
  - "Pre-flight Validation: Upon execution, invoke the `lint`, `test`, and `coverage` core tools. If any fail, automatically spawn an inner Red/Green fixup loop."
  - "Tool-Driven Orchestration: The controller provides the LLM with the unified tool registry schemas (from Task 0004) and handles LLM tool requests and dispatches them."
  - "File Access Security Wrappers: Implement basic Python security wrappers over file tools to enforce global constraints."
  - "Harness Lockdown: Block ALL writes targeting the `.tdd-harness/` configuration directory or the `src/tdd_harness/` module itself across all phases."
  - "Red Exit: Verify the test suite fails (using the core `run_test` tool)."
  - "Green Exit: Verify all tests pass."
  - "Blue Exit (Refactor): Verify all tests pass, and explicitly assert that the total number of unit tests has not decreased."
  - "Magenta Exit: Verify all tests pass, untested lines `<= max_uncovered_lines`, coverage `>= coverage_threshold`."
  - "Comprehensive integration tests mock the LLM and verify the boundary and transition logic."
---
# Unit of Work: TDD Loop Controller and File Security Interceptors

## Context
Implement the core Red-Green-Blue state machine that governs the TDD iterations. This component connects the CLI (Task 0005) to the LLM (Task 0003) and enforces strict directory-level security by intercepting the AI's file read/write operations.
