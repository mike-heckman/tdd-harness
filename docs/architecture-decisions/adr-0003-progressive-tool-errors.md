# ADR 0003: Progressive Tool Errors & Help Delegation

## Status
Accepted

## Context
Providing full tool schemas and verbose error messages consumes massive amounts of the LLM context window. However, providing too little information leads to the LLM entering infinite failure loops when it misunderstands a tool's syntax.

## Decision
We will decouple tool descriptions and implement a progressive error escalation system:
1. **Condensed Schemas:** The primary tool schema exposed to the LLM will only contain a single-line description.
2. **Help Delegation:** A native `get_tool_help` tool will be added to the registry, providing the full, detailed syntax documentation for any registered tool.
3. **Progressive Errors:** The `AntiThrashingTracker` will track consecutive failures per tool. 
   - For native Python tools, `previous_failures` will be injected into the tool's execution parameters so the tool can return progressively verbose exceptions.
   - For external MCP tools, the `ToolRegistry` will act as a wrapper, programmatically appending progressive hints to the external error response.
4. **Decentralized Tool Configuration:** Tool configurations (including startup commands for MCP servers and their progressive error mapping rules) will be moved from the global config into `.tdd-harness/tools/*.yaml`. The error rules will allow mapping specific error strings/regexes to failure-count-based hints.
5. **Tracker Persistence:** A tool's failure count will persist across unrelated tool calls and only reset upon a successful execution of that specific tool.

## Consequences
- **Pros:** Massively reduces baseline token consumption. Guides the LLM specifically when it starts thrashing.
- **Cons:** Requires the LLM to spend an API turn calling `get_tool_help` if it forgets the syntax. Tightens the coupling between the tool dispatcher and the state tracker.
