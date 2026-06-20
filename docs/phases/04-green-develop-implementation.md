# Phase 04: Green (Develop Implementation)

## Description
The LLM writes the production implementation code to satisfy the failing tests generated in the Red Phase. Employs dynamic code composition, rapid reverting, and post-mortem summarization on failure.

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
1. **Original Blue Stubs**
2. **Test Concepts** (from JSON state map)
3. ***Previous failure summaries*** (historical list, explicitly labeled to prevent repeating old mistakes)
4. **LATEST FAILED DRAFT** (The bad code it just submitted, if any)
5. **Post-Mortem Summary & Guidance** (The exact reason the Latest Draft failed, and actionable steps to fix it)
