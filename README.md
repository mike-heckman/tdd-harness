# 🧪 tdd-harness

**An autonomous AI harness that enforces strict Test-Driven Development.**

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Coverage: 94%](https://img.shields.io/badge/coverage-94%25-brightgreen.svg)](coverage.md)
[![Tests: 141](https://img.shields.io/badge/tests-141%20passing-brightgreen.svg)](scripts/test.sh)

---

## The Problem

AI coding agents are powerful but undisciplined. Left to their own devices, they:

- **Cheat tests** — editing failing tests instead of fixing the implementation.
- **Thrash in loops** — retrying the same broken approach indefinitely, burning tokens.
- **Bloat context** — dumping raw tracebacks into the conversation until the window overflows.
- **Skip coverage** — declaring success with untested edge cases.

`tdd-harness` solves this by wrapping any OpenAI-compatible LLM in a **deterministic state machine** that programmatically enforces the TDD lifecycle — not by asking the model to follow rules, but by _physically denying_ it the tools to break them.

---

## How It Works

The harness orchestrates five strict phases, each with **programmatically enforced file access boundaries**:

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  AMBER   │────▶│   BLUE   │────▶│   RED    │────▶│  GREEN   │────▶│ MAGENTA  │
│ Baseline │     │ Blueprint│     │  Tests   │     │   Impl   │     │ Coverage │
│ Check    │     │  Stubs   │     │  (fail)  │     │  (pass)  │     │ Guardrail│
└──────────┘     └──────────┘     └──────────┘     └──────────┘     └──────────┘
  src: rw          src: rw          src: RO          src: rw          src: RO
  test: ro         test: ro         test: RW         test: ro         test: RW
```

| Phase | Purpose | Write Access | Exit Criteria |
|:------|:--------|:-------------|:--------------|
| **Amber** | Pre-flight validation | `src/` | All tests pass, linter clean |
| **Blue** | Structural blueprint — interfaces & stubs | `src/` | Tests pass, count ≥ baseline |
| **Red** | Write failing tests against the stubs | `tests/` | Suite fails with `AssertionError` or `NotImplementedError` |
| **Green** | Implement code to satisfy the tests | `src/` | All tests pass |
| **Magenta** | Coverage guardrail — file-by-file enforcement | `tests/` | Coverage ≥ threshold, uncovered lines ≤ max |

The LLM **cannot** write test files during Green, and **cannot** modify source during Red. These aren't guidelines — they're hard-coded tool denials at the registry layer.

---

## Key Design Decisions

### 1. Deterministic Orchestration over Agentic Loops

The harness rejects the popular "ReAct loop" pattern where an LLM autonomously sequences JSON tool calls. Instead, **the harness itself is the state machine** — Python manages phase transitions, file I/O, subprocess execution, and MCP server communication. The LLM is invoked only as a **stateless NLP node** for semantic transformations: extracting search queries, generating code, summarizing failures.

### 2. Staging Buffers & Atomic Revert

The LLM never writes files directly. It calls `stage_implementation()` or `stage_test_implementation()`, which:
1. Creates a backup of the original file.
2. Writes the proposed changes.
3. Runs lint + targeted tests.
4. **Reverts immediately on failure** — the working tree stays clean.
5. On failure, generates a **post-mortem summary** via a secondary LLM call and injects the concise guidance into subsequent prompts instead of the raw traceback.

### 3. Post-Mortem Summarization (Context Conservation)

When tests fail, raw tracebacks are **not** injected into the persistent chat history. Instead:
- A secondary LLM call distills the root cause into a concise summary.
- The failed code is reverted and the raw error is discarded from context.
- Only the summary survives, preserving the context window for productive work.
- Results are cached by `sha256(filepath:error)` to avoid duplicate LLM calls.

### 4. Anti-Thrashing Guardrails

The `AntiThrashingTracker` monitors tool calls via a sliding window:
- Hashes each `(tool_name, arguments)` pair using deterministic JSON serialization.
- Aborts if **N duplicate failures** repeat, or **M failures occur within a window of Z** calls.
- Exposes `previous_failures` counts to tools, enabling [Progressive Error Escalation](docs/architecture-decisions/adr-0003-progressive-tool-errors.md) — tools return increasingly verbose hints as the failure count rises.

### 5. Pluggable Toolchain Adapters

Language-specific operations are decoupled via abstract adapter interfaces:

```
Adapter (ABC)
├── TestAdapter   → PytestAdapter (.py)
├── LintAdapter   → RuffAdapter (.py)
└── CoverageAdapter → LcovAdapter (.py)
```

Adapters are **auto-discovered** at runtime via `pkgutil` — drop a new adapter module into `src/tdd_harness/adapters/` and it registers itself. No configuration changes needed.

### 6. Unified Tool Registry (MCP + Python)

The `ToolRegistry` provides a single dispatch surface for both:
- **MCP tools** — loaded dynamically from external MCP servers via stdio transport.
- **Python tools** — local functions registered with automatic schema introspection.

All tools emit OpenAI-compatible function schemas, keeping the LLM integration provider-agnostic.

### 7. Sub-Agent Architecture

Specialized sub-agents isolate distinct LLM concerns:

| Sub-Agent | Role |
|:----------|:-----|
| `ReviewSubAgent` | Gates phase exits — reviews diffs against the task spec, can REJECT |
| `PostMortemSubAgent` | Distills failure tracebacks into concise root-cause summaries |
| `ResearchSubAgent` | Investigates queries using MCP tools + web search |

Each sub-agent has its own configurable prompt and operates statelessly against the shared `LLMClient`.

---

## Quick Start

### Prerequisites

- Python ≥ 3.12
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/mike-heckman/tdd-harness.git
cd tdd-harness

# Install dependencies via uv
uv sync
```

### Initialize a Project

```bash
uv run tdd-harness init
```

This creates a `.tdd-harness/` directory with:
- `config.yaml` — LLM endpoint, context limits, coverage thresholds, anti-thrashing settings
- `prompts/` — System message and compression prompt templates

### Configure

Edit `.tdd-harness/config.yaml`:

```yaml
llm:
  provider: openai
  base_url: http://localhost:8000/v1   # Any OpenAI-compatible endpoint
  model: your-model-name
  api_key: your-api-key               # Or set via .env / environment
  context_size: 8192
  minimum_available_context: 2048
  keep_turns: 1

harness:
  coverage_threshold: 80.0
  max_uncovered_lines: 50
  anti_thrashing:
    max_duplicate_failures: 3
    max_window_failures: 4
    window_size: 5
```

### Run the Harness

```bash
bin/tdd-harness.sh
```

Or with a specific starting phase:

```bash
bin/tdd-harness.sh --phase green
```

The harness will:
1. Validate the baseline (Amber)
2. Pick the first task from `docs/tasks/ready/`
3. Execute Blue → Red → Green → Magenta phases
4. Move the completed task to `docs/tasks/done/`

---

## Project Structure

```
tdd-harness/
├── bin/
│   └── tdd-harness.sh          # Primary executable entrypoint
├── src/tdd_harness/
│   ├── adapters/               # Pluggable toolchain adapters (auto-discovered)
│   │   ├── base.py             # ABC interfaces: TestAdapter, LintAdapter, CoverageAdapter
│   │   ├── pytest_adapter.py   # Pytest + report-log parsing
│   │   ├── ruff_adapter.py     # Ruff linter with JSON output
│   │   └── lcov_adapter.py     # LCOV coverage aggregation
│   ├── models/
│   │   └── tool.py             # Pydantic models: ToolCall, ToolCallResponse
│   ├── cli.py                  # Argument parsing & async orchestration entry
│   ├── config.py               # YAML config loader with 3-tier resolution fallback
│   ├── context.py              # Context / ContextBuilder — singleton context stack manager
│   ├── controller.py           # TDDLoopController — the core state machine (~1000 LOC)
│   ├── coverage_parser.py      # LCOV file parser and aggregator
│   ├── llm.py                  # LLMClient — chat, compression, tool-call loop
│   ├── mcp_client.py           # MCP stdio transport client with restart policies
│   ├── prompt.py               # Prompt class with SHA256 hash + token cache
│   ├── registry.py             # Unified ToolRegistry (MCP + Python tools)
│   ├── runner.py               # AdapterRegistry & orchestration functions
│   ├── sub_agents.py           # Review, PostMortem, and Research sub-agents
│   ├── tool_schemas.py         # Phase-gated OpenAI function schema registry
│   └── tracker.py              # AntiThrashingTracker — sliding window abort logic
├── tests/                      # 141 tests, 94% coverage
├── scripts/                    # Standardized lifecycle scripts (test, lint, clean)
├── docs/
│   ├── software-design-document.md
│   ├── architecture-decisions/  # ADRs (multi-phase TDD, progressive errors)
│   ├── phases/                  # Detailed phase specifications (Amber–Cyan)
│   └── tools.md                 # Tool registry documentation
└── .tdd-harness/                # Project-level harness configuration
```

---

## Task File Format

Tasks are Markdown files with YAML frontmatter placed in `docs/tasks/ready/`:

```markdown
---
id: "0042"
title: "Implement Widget Processor"
success_criteria:
  - "All unit tests pass"
  - "Coverage exceeds 80%"
target_files:
  - src/widget/processor.py
dependencies:
  prod:
    - pydantic
  dev:
    - pytest
---

## Context

Describe the implementation requirements here...
```

---

## Development

### Run Tests

```bash
./scripts/test.sh
```

### Run Linter

```bash
./scripts/lint.sh
```

### View Coverage

```bash
cat coverage.md
```

---

## Architecture Decisions

| ADR | Decision |
|:----|:---------|
| [ADR-0002](docs/architecture-decisions/adr-0002-multi-phase-tdd.md) | Multi-phase TDD pipeline with programmatic file access boundaries |
| [ADR-0003](docs/architecture-decisions/adr-0003-progressive-tool-errors.md) | Progressive tool error escalation & condensed schemas |

---

## License

[MIT](LICENSE) © 2026 Mike Heckman
