# Task: 0002-coder - Subprocess Command Executor, Coverage Analyzer & Native Tools

## Context
Implement the execution runner component of the harness. The harness must run bash commands for lint, test, and coverage as specified by the configuration. Crucially, these core commands must be exposed natively as Tools in the Tool Registry so the LLM can invoke them directly. The project strictly mandates YAML for all configurations.

## Target Files
- `src/tdd_harness/runner.py`
- `src/tdd_harness/coverage.py`
- `src/tdd_harness/tools.py`
- `tests/test_runner.py`
- `tests/test_coverage.py`
- `tests/test_tools.py`

## Instructions
- Implement a class to run commands using Python's `subprocess` safely, capturing stdout/stderr and enforcing timeouts.
- **Refactor Coverage Analyzer (`src/tdd_harness/coverage.py`)**:
  - Migrate the core logic from `scripts/generate-unified-coverage.py` (or build fresh) to parse standard **LCOV** compatible output files explicitly written into the `./temp` directory by the language-specific coverage modules.
  - The module must aggregate these LCOV files and calculate total coverage and untested source lines.
  - It must read the `AgentMetrics` state from `.agent-metrics.yaml` and the guardrail limits from the core config (`minimum_coverage_percent`, `max_uncovered_lines`).
  - **Critical**: If the aggregated coverage fails the guardrails (e.g. coverage dropped, or untested lines exceed the max), the module must raise an `InsufficientCoverageException` containing a detailed summary of the problem.
  - On success, it writes the new metrics to `.agent-metrics.yaml`.
- **Expose Core Tools**:
  - In `src/tdd_harness/tools.py`, create standard OpenAI tool schema wrappers for `run_lint`, `run_test`, and `run_coverage`.
  - These wrappers invoke the Subprocess Runner. The `run_coverage` tool wrapper must specifically execute the bash coverage command (which writes to `./temp`), and then invoke the `coverage.py` analyzer within a `try/except` block to catch the `InsufficientCoverageException`.
  - The tools must return JSON-structured results back to the LLM (e.g. `{"status": "pass", "stdout": "..."}` or `{"status": "fail", "reason": "<exception_summary>"}`).
  - Automatically register these native tools into the unified Tool Registry (from Task 0004).

## Success Criteria
- Subprocess runner executes commands and handles timeouts gracefully.
- The refactored coverage module tracks state strictly in `.agent-metrics.yaml` and parses underlying test coverage outputs correctly.
- The `lint`, `test`, and `coverage` functions are successfully exported as schema-compliant tools for the LLM.
- Unit tests written for the runner, coverage parser, and tool wrappers.
