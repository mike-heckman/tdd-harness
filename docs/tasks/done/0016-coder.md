---
id: '0016'
title: Zero-Config Multi-Language Adapter Discovery
success_criteria:
- Remove the `adapters` configuration block from `config.yaml` entirely to enforce Zero-Config architecture.
- Implement an Adapter Registry or auto-discovery mechanism in `runner.py` to natively locate all subclasses of `BaseAdapter`.
- Update the Orchestrator to support 'Targeted' execution (routing to specific adapters based on file extensions in the target string).
- Update the Orchestrator to support 'Global' execution (iterating through the `.languages` file active flags and running all matching adapters).
- Update the Orchestrator to support 'Defined' execution (parsing a target node ID like `file.py::test_case` to find the extension and route correctly).
- Global test executions must inherently trigger coverage production to generate `.lcov` artifacts natively, preventing duplicate suite runs.
dependencies:
  prod: []
  dev: []
---
# Unit of Work: Zero-Config Multi-Language Adapter Discovery

## Context
Following the Architect's redesign, the codebase is moving away from manual toolchain definition in `config.yaml` toward an auto-discovery mechanism. Adapters should intrinsically declare their `supported_extensions` and `language`. The orchestrator will dynamically route execution payloads (Targeted, Global, Defined) to the correct adapters at runtime based on the payload string and the active `.languages` file.
