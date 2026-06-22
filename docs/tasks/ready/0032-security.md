---
id: "0032"
title: "Security Review: Phase Driver Loops & LLM Integration"
dependencies:
  prod: []
  dev: []
target_files:
  - "src/tdd_harness/controller.py"
  - "src/tdd_harness/llm.py"
  - "src/tdd_harness/mcp_client.py"
success_criteria:
  - "Audit all LLM prompt injection vectors: verify that user-controlled task file content and tool results cannot escape the system prompt boundaries."
  - "Audit the `_is_path_allowed` security interceptor for path traversal bypasses (e.g., symlinks, `../` sequences, absolute paths outside workspace)."
  - "Audit the `MCPClient` for credential leakage, ensuring API keys are not logged or included in error messages."
  - "Verify the `stage_implementation` and `stage_test_implementation` file revert logic is crash-safe (no partial writes, no orphaned backups)."
  - "Document findings in a security audit report at `docs/tasks/reports/0031-security-audit.md`."
---
# Unit of Work: Security Review: Phase Driver Loops & LLM Integration

## Context
With the introduction of real LLM driver loops (tasks 0025-0028) and MCP connectivity (0023), the attack surface expands significantly. The LLM now processes user-authored task files and returns tool calls that write files to disk. A security audit is required per Architect backlog policy to verify that the existing security boundaries (path restrictions, phase access rules, tool whitelisting) remain effective.
