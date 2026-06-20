# Phase 02: Blue (Structural Blueprint)

## Description
Generates rigid interfaces, stubs, and abstract class definitions. Code must pass syntax linting (`ruff`) and the existing test suite (`pytest`) to prevent breaking changes.

## Permissions
- `src/`: Read-Write (`rw`)
- `test/`: Read-Only (`ro`)

## Available Tools
- `search_symbols` (MCP)
- `get_symbol_source` (MCP)
- `ask_researcher` (Native Sub-Agent)
- `stage_implementation` (Native)
- `success` (Native)
- `abort` (Native)

## Context Payload
1. Task `Context`
2. Task `Success Criteria`
3. Current file source (if modifying an existing file)
