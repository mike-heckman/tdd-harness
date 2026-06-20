# Task: 0005-coder - CLI Entrypoint, Git Validation, and Anti-Thrashing Tracker

## Context
Integrate the config loader and basic validation logic into the primary entrypoint. This task establishes the CLI scaffolding, the pre-execution Git state validation, and the anti-thrashing sliding window tracker that protects the harness from infinite AI hallucination loops.

## Target Files
- `bin/tdd-harness.sh`
- `src/tdd_harness/cli.py`
- `src/tdd_harness/tracker.py`
- `tests/test_cli.py`
- `tests/test_tracker.py`

## Instructions
- Implement the CLI and Executable wrapper:
  - Create `bin/tdd-harness.sh` as the primary executable entrypoint that wraps the python execution environment.
  - In `cli.py`, parse a `--project-dir` argument and pass it to the Config Loader (Task 0001) to bootstrap the `.tdd-harness/` resolution logic.
  - Parse `--phase green` and `--phase blue` optional flags.
  - **Missing Config Fallback**: If the config loader fails to find a `.tdd-harness/` directory, immediately fail fast with an actionable error instructing the user to run `tdd-harness init`.
- **Git State Validation**:
  - Abort the execution immediately in `cli.py` if `git status --porcelain` is not clean.
- **Anti-Thrashing Mechanism** (`tracker.py`): 
  - Track hashes of LLM tool-calls and their success status.
  - Abort the loop and mark the active task as errored if:
    - X duplicate failed requests occur consecutively (`max_duplicate_failures`).
    - Y failed requests occur within a sliding window of Z requests.
  - Leave the workspace dirty upon a thrashing failure so the human reviewer can inspect the exact point of AI failure. No automatic rollback is performed.

## Success Criteria
- Harness can be executed universally via `bin/tdd-harness.sh`.
- CLI correctly passes the project directory down to the config loader.
- Harness aborts correctly if the Git tree is dirty before any AI logic begins.
- The anti-thrashing tracker accurately calculates failure thresholds and successfully exits the harness when triggered.
- Unit tests written for CLI parsing, git checks, and tracker math.
