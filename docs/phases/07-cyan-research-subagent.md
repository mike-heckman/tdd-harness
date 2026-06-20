# Phase 07: Cyan (Research Sub-Agent)

## Description
Unlike the sequential lifecycle phases, Cyan serves two distinct asynchronous roles:
1. **Documentation Provisioning (Triggered by Amber)**: When the Amber phase installs new dependencies, the Harness triggers Cyan to download and index the external library's documentation into the local (gitignored) `./docs/reference/{library_name}/` directory via `jDocMunch`.
2. **Research Sub-Routine (Triggered by Execution Phases)**: Dynamically invoked when a primary agent calls the `ask_researcher(query)` tool. The sub-agent searches the indexed documentation to answer the specific query, returning a concise summary to protect the primary token budget.

## Permissions
- `src/`: Read-Only (`ro`)
- `test/`: Read-Only (`ro`)
- `docs/reference/`: Read-Write (`rw`) *(Strictly required during Provisioning to create library directories and save fetched documentation)*

## Available Tools
- **Web Research Tools (Native)**: 
  - `search_web(query: str)`
  - `download_to_reference(url: str, library_name: str, filename: str)`
- All `jdocmunch` MCP Tools (e.g., `search_sections`, `get_section`, `get_toc`)
- All `jcodemunch` MCP Tools (e.g., `search_symbols`, `get_symbol_source`)

## Context Payload
*(Note: This payload is completely isolated from the primary agent's history)*
1. The explicit `query` string provided by the primary agent.
2. A System Prompt instructing it to return a concise, 3-4 sentence technical summary of its findings.
