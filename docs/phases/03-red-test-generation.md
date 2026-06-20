# Phase 03: Red (Test Generation)

## Description
The LLM writes failing tests against the Blue interfaces. Tests must fail due to an assertion (`AssertionError` or `NotImplementedError`) and must explicitly declare a conceptual docstring.

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
2. Task `Success Criteria`
3. Target Blue Interfaces (Stubs)
