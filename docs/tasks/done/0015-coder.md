---
id: '0015'
title: Dependency & Documentation Provisioning (Amber Phase)
success_criteria:
- Implement strict schema validation in the **Amber Phase** based on `docs/interfaces/task-schema.md`
  (requiring YAML frontmatter and specific Markdown headers).
- If validation fails, move the task file to `./docs/tasks/error/` and generate a
  `<task_name>.error.log` alongside it. The original task file must not be modified.
- If validation passes, Amber must parse the `dependencies` block from the YAML frontmatter
  and trigger a native harness tool to install/update the missing libraries in the
  virtual environment.
- After installation, Amber must trigger the **Cyan Sub-Agent** via the `ask_researcher` tool.
- The Cyan Sub-Agent must use its `search_web` and `download_to_reference` tools to fetch the external reference documentation for the library
  and store it securely in the `./docs/reference/{library_name}/` directory.
- '`jDocMunch` must be triggered to index `./docs/reference/` so it is immediately
  searchable by the execution agents.'
dependencies:
  prod:
  - pyyaml
  - duckduckgo-search
  - requests
  - beautifulsoup4
  - markdownify
  dev: []
---
# Unit of Work: Dependency & Documentation Provisioning (Amber Phase)

## Context
The primary execution agents (Red, Green) should not be responsible for environment management. The Architect declares dependencies in the Task file, and the Amber phase must provision the environment and the documentation index before the execution phases begin.
