# Phase 05: Magenta (Coverage Guardrail)

## Description
A guardrail phase that verifies line and branch coverage via tools like `lcov`. The LLM writes additional tests to cover any untested execution paths identified in the new or modified code.

## Permissions
- `src/`: Read-Only (`ro`)
- `test/`: Read-Write (`rw`)

## Available Tools
- `search_symbols` (MCP)
- `get_symbol_source` (MCP)
- `ask_researcher` (Native Sub-Agent)
- `stage_test_implementation` (Native)
- `success` (Native)
- `abort` (Native)

## Context Payload
1. Task `Context`
2. Coverage Gaps (Specific unexecuted line numbers)
