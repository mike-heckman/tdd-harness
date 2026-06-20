# Harness Tools Registry

This document outlines the specialized native tools built into the TDD Harness to facilitate autonomous execution, token conservation, and state transitions.

## Native Harness Tools

### 1. Execution & Code Composition
These tools are the primary levers for modifying the workspace. They encapsulate the "Dynamic Code Composition" loop, automatically triggering background linting and testing.

- **`stage_implementation(filepath: str, code: str)`**
  Writes implementation logic to the `src/` directory. Automatically calls `run_lint(filepath)` and `run_test(filepath)` under the hood. If tests pass, the change is committed. If tests fail, it reverts the file using `.orig` backups, discards tracebacks, and returns a concise "Post-Mortem Summary".
- **`stage_test_implementation(filepath: str, code: str)`**
  Writes test logic to the `test/` directory. Operates using the exact same Post-Mortem revert loop (via `run_lint` and `run_test`) as `stage_implementation`. During the Red phase, it guarantees that new tests fail before advancing.

### 2. Validation & Quality Gates
These tools are standard OpenAI schema wrappers that invoke the Subprocess Runner. They execute configured bash commands and return structured JSON results (e.g., `{"status": "pass", "stdout": "..."}`) directly to the LLM.

- **`run_lint(filepath: str = None)`**
  Executes the configured linting command (e.g., `ruff`) and returns the structured output. Can be run globally or targeted at specific files.
- **`run_test(filepath: str = None, language: str = None)`**
  Executes the configured testing suite. Returns structured test results including failure classes. Supports three distinct execution models:
  1. **"Everything"** (`filepath=None, language=None`): Runs the full suite across all active languages. *Only this model triggers coverage generation.*
  2. **Language-specific** (`language="python"`): Runs only the test suite for the requested language.
  3. **Test-specific** (`filepath="tests/test_foo.py"`): Runs only a specific test file to optimize execution time during tight loops.
- **`run_coverage()`**
  Executes the bash coverage command, aggregates `lcov` output files in `./temp`, and calculates metrics based on `.agent-metrics.yaml`. Raises an `InsufficientCoverageException` if limits are violated.

### 3. State Transitions
The Harness is inherently stateless regarding the agent's multi-step intentions. Phase transitions are not automatic; they must be explicitly triggered by the agent using these tools.

- **`success(message: str)`**
  Signals that the agent believes it has fully satisfied the constraints of the current phase. The `message` (e.g., implementation notes or caveats) is automatically written to a report file at `./docs/tasks/reports/<task_id>.md` for external review. The Harness performs a holistic evaluation (e.g., all tests pass, coverage targets met). In execution phases, this triggers the **Violet Review Gate**. If the Reviewer approves, the state machine advances.
- **`abort(reason: str)`**
  An explicit escape hatch. If the agent is trapped in a failure loop, lacks required third-party dependencies, or fundamentally cannot satisfy the Definition of Done, it calls this tool to pause the loop. The `reason` is written to `./docs/tasks/reports/<task_id>.md`, escalating the roadblock to the human developer or Architect.

### 4. Context Management & Sub-Agents
Tools designed to protect the primary agent's context window from token exhaustion.

- **`ask_researcher(search_keywords: str)`**
  Triggers the **Cyan Orchestration Pipeline**. Instead of exposing dozens of complex search tools directly to the execution agent, the primary agent provides exact search keywords (e.g. `"Stripe charge API JSON payload"` - DO NOT use conversational questions). The Harness automatically orchestrates local and web searches, returning a synthesized summary.
- **`get_tool_help(tool_name: str)`**
  Returns the extended JSON schema, detailed description, and syntax examples for a specific tool. This allows the baseline prompt to remain extremely minimal, only loading complex schemas when the agent explicitly requests them.

### 5. Cyan Web Research & Provisioning Tools
These tools are exclusively granted to the Cyan Sub-Agent. They allow Cyan to fetch external documentation and strictly cache it locally for semantic search, preventing the agent's context window from being flooded by raw HTML.

- **`search_web(query: str)`**
  Executes a headless web search (e.g., via `duckduckgo-search`) and returns a list of URLs and text snippets.
- **`download_to_reference(url: str, library_name: str, filename: str)`**
  Downloads the target URL, uses `beautifulsoup4` and `markdownify` to strip away navigation/HTML bloat, converts the core article to Markdown, and securely writes it to `./docs/reference/{library_name}/{filename}.md`. If called during ad-hoc research without a specific pip package, the domain name should be used as the `library_name`.

---

## MCP Plugin Suites

The harness heavily leverages external MCP servers for read-only static analysis and documentation retrieval. These suites are primarily exposed to the **Blue Phase** (Architecture Blueprinting) and the **Cyan Phase** (Research Sub-Agent).

- **`jDocMunch`**
  A comprehensive suite of documentation tools. Used for indexing, table-of-contents navigation, and deep-dive retrieval of Markdown, API specs, and project requirements.
- **`jCodeMunch`**
  A specialized codebase analysis suite. Used for repository indexing, file-tree mapping, and precise symbol/AST lookups across the workspace.
