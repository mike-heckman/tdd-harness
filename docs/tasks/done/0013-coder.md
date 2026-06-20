---
id: '0013'
title: Research Sub-Agent (`ask_researcher`)
success_criteria:
- 'Create a new native tool `ask_researcher(query: str)`.'
- When invoked, the tool must instantiate a secondary, stateless LLM client (the Sub-Agent).
- The Sub-Agent must be initialized with a system prompt and access to the full suite
  of `jdocmunch` and `jcodemunch` MCP tools.
- The Sub-Agent must be prompted to use its tools to find the answer to the `query`,
  and then return a concise, 3-4 sentence technical summary of the findings.
- The `ask_researcher` tool must return *only* this concise summary back to the primary
  agent, keeping the primary agent's context clean.
dependencies:
  prod: []
  dev: []
---
# Unit of Work: Research Sub-Agent (`ask_researcher`)

## Context
To prevent token exhaustion and tool schema bloat in the primary execution phases (Red, Green, Magenta), the primary agent is not given direct access to the `jdocmunch` or `jcodemunch` tools. Instead, it must rely on a dedicated Research Sub-Agent to perform deep dives into documentation and large codebases.
