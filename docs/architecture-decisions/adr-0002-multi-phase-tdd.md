# ADR 0002: Multi-Phase TDD Pipeline & Guardrails

## Status
Accepted

## Context
The standard Red/Green/Refactor TDD cycle is insufficient for autonomous LLM agents because it lacks deterministic state boundaries. Agents often try to bypass failing tests by editing them after the fact ("lazy agent" problem) or lose track of why a test was written. We need a strict execution sandbox that programmatically denies write/edit tool access to specific paths based on the current execution phase, ensuring the agent follows SOLID engineering principles.

## Decision
We will transition from a 3-phase cycle to a strict **5-Phase TDD Pipeline**:

1. **Amber (Baseline Check)**: `src/: rw, test/: ro`. Validates `pytest == 0` and `ruff == 0`. Ensures the environment is clean before starting.
2. **Blue (Structural Blueprint)**: `src/: rw, test/: ro`. Generates rigid interfaces/stubs. Code must pass `ruff` (no syntax errors). Stubs return valid types.
3. **Red (Test)**: `src/: ro, test/: rw`. The LLM writes failing tests against the Blue interfaces. 
   - **Constraint**: Must fail due to an assertion (`AssertionError` or `NotImplementedError`). Syntax/import errors result in a rejected turn.
   - **Structured Test Tool**: Instead of writing raw files, the LLM must use a `stage_test_implementation(test_file, test_name, concept_description, test_code)` tool. This strictly enforces the presence of the concept description at the schema level and allows the harness to persist the description to internal state mapping.
4. **Green (Develop)**: `src/: rw, test/: ro`. Implements the code to satisfy the tests. 
   - **Context Injection**: The harness reads the internal state mapping for any failing tests and explicitly injects those "Test Concepts" into the prompt. This eliminates the need for brittle, language-specific AST parsing.
5. **Magenta (Coverage Guardrail)**: `src/: ro, test/: rw`. 
   - Uses `lcov` to capture branch/line coverage.
   - Loops file-by-file for any file missing coverage, injecting specific line numbers to target missing paths.
   - *Future Enhancement Stub*: If the LLM repeatedly fails to increase coverage, the harness currently halts and alerts the human. Future logic will handle this more dynamically.

### Toolchain Adapters & Configuration
To support multiple languages and precise file-level execution, the TDD Controller will use separate `TestAdapter`, `LintAdapter`, and `CoverageAdapter` interfaces. Raw stdout is no longer parsed by the core loop.
- The adapter configuration will be defined in `.tdd-harness/config.yaml`:
  ```yaml
  adapters:
    test: pytest
    lint: ruff
    coverage: lcov
  ```
- **Execution Scoping**: Both the `TestAdapter` and `LintAdapter` interfaces will support taking an optional `file_path` to execute against a single file rather than the entire workspace to save time in tight loops.

## Consequences
- **Pros:** Programmatically prevents the LLM from cheating tests without requiring slow OS-level disk operations. Context tokens are vastly reduced in the Green phase by passing only the AST test concepts.
- **Cons:** Increases total LLM API calls per feature. Requires maintaining language-specific `TestAdapter` plugins to parse structured test outputs (e.g., `pytest-reportlog`).
