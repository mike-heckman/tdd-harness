# Phase 01: Amber (Baseline Check)

## Description
Provisions the environment and validates the baseline. 
1. **Schema Validation**: The Harness parses the Task file against the official `task-schema.md`. If validation fails, the file is moved to `./docs/tasks/error/` and a sidecar `.error.log` is generated with the exact validation failures, preserving the original file perfectly.
2. **Provisioning**: The Harness reads the validated YAML frontmatter for required external libraries (`dependencies: prod|dev`) and uses an internal language tool to install/update them. It then delegates to Cyan to download and index the external documentation into `./docs/reference/{library_name}/`.
3. **Validation**: Ensures `pytest` and `ruff` pass with zero errors to prevent the agent from thrashing on pre-existing issues.

## Permissions
- `src/`: Read-Write (`rw`)
- `test/`: Read-Only (`ro`)

## Available Tools
- `search_symbols` (MCP)
- `get_symbol_source` (MCP)
- `stage_implementation` (Native)
- `success` (Native)
- `abort` (Native)

## Context Payload
*(Note: The LLM is only invoked if the baseline check fails. If it passes, this phase is skipped.)*
1. **Linter Tracebacks** (if `ruff` fails)
2. **Failing Test Tracebacks** (if `pytest` fails)
3. ***Previous failure summaries*** (historical list, explicitly labeled)
4. **LATEST FAILED DRAFT** (The bad code it just submitted, if any)
5. **Post-Mortem Summary & Guidance** (Actionable steps to fix the Latest Draft)
