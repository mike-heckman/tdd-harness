# 🔬 tdd-harness — Deep Codebase Review Report

**Date:** 2026-06-22  
**Branch:** `performance/0033`  
**Reviewer:** Architect Persona (Deep Review)  
**Scope:** Full codebase analysis — 17 Python modules, 16 test files, 10 scripts, 7 phase docs, 2 ADRs

---

## Executive Summary

The `tdd-harness` codebase demonstrates **exceptional architectural discipline** for a project of this maturity. It implements a genuinely novel approach to constraining AI agents: rather than asking an LLM to follow TDD rules via prompting, the harness physically denies tool access based on phase state — a fundamentally stronger guarantee. The codebase has 94% test coverage across 141 tests, follows PEP 8, and the design document is remarkably well-maintained relative to the implementation.

That said, several structural issues warrant attention before the system reaches production readiness.

---

## 🏆 Exceptional Design Decisions

### 1. Phase-Gated File Access — The Core Innovation

> [!IMPORTANT]
> This is the project's most original contribution to the AI tooling space.

The [_is_path_allowed()](file:///home/mike/Projects/mike-heckman/tdd-harness/src/tdd_harness/controller.py#L113-L149) method in the controller doesn't rely on prompting to prevent test manipulation — it **denies the `write_file` tool at the registry layer** based on the current `Phase` enum. During `Phase.RED`, the LLM literally cannot write to `src/`. During `Phase.GREEN`, it cannot write to `tests/`. This is a hardware-style interlock, not a software suggestion.

### 2. Staging Buffers with Atomic Revert

The [stage_implementation()](file:///home/mike/Projects/mike-heckman/tdd-harness/src/tdd_harness/controller.py#L280-L338) and [stage_test_implementation()](file:///home/mike/Projects/mike-heckman/tdd-harness/src/tdd_harness/controller.py#L340-L417) methods implement a transactional write pattern: backup → write → lint → test → revert-on-failure. This keeps the working tree clean during LLM failure loops and is a genuinely smart solution to the "dirty workspace" problem that plagues agent systems.

### 3. Post-Mortem Summarization (Context Conservation)

Instead of dumping raw tracebacks into the LLM context (which rapidly exhausts the window), the harness makes a **secondary LLM call** via [PostMortemSubAgent](file:///home/mike/Projects/mike-heckman/tdd-harness/src/tdd_harness/sub_agents.py#L56-L85) to distill the error into a concise root-cause summary. The raw error is discarded, the file is reverted, and only the summary survives in context. Results are cached by `sha256(filepath:error)` to prevent duplicate API calls — a thoughtful optimization.

### 4. Anti-Thrashing with Progressive Error Escalation

The [AntiThrashingTracker](file:///home/mike/Projects/mike-heckman/tdd-harness/src/tdd_harness/tracker.py#L12-L118) uses a sliding window to detect both duplicate failures and burst failures. What elevates this beyond a simple counter is [ADR-0003](file:///home/mike/Projects/mike-heckman/tdd-harness/docs/architecture-decisions/adr-0003-progressive-tool-errors.md): the `previous_failures` count is injected into tool parameters, allowing tools to return *progressively verbose* hints. This guides the LLM out of failure loops without wasting tokens upfront on verbose documentation.

### 5. Auto-Discovered Pluggable Adapters

The [AdapterRegistry.discover()](file:///home/mike/Projects/mike-heckman/tdd-harness/src/tdd_harness/runner.py#L28-L62) method uses `pkgutil.iter_modules()` + `__subclasses__()` to automatically find and register all `Adapter` subclasses at runtime. Adding a new language adapter requires zero configuration — just drop a new module into `src/tdd_harness/adapters/` and it registers itself. Clean, extensible, and follows the Open/Closed Principle.

### 6. Context Deadlock Prevention

The [chat()](file:///home/mike/Projects/mike-heckman/tdd-harness/src/tdd_harness/llm.py#L127-L211) method performs an upfront check: if `system_tokens + incoming_tokens` already exceed the usable context window, it raises `RuntimeError("Context Exhausted")` instead of entering an infinite compression loop. This is a subtle but critical safeguard.

### 7. Prompt Hash-Based Cache Invalidation

The [Prompt](file:///home/mike/Projects/mike-heckman/tdd-harness/src/tdd_harness/prompt.py#L18-L146) class computes a SHA256 hash of the prompt text and compares it against a cached hash in `.prompt-cache.yaml`. If the prompt changes, all token count caches for that prompt are invalidated automatically. This supports read-only configuration mounts (e.g., container deployments) while keeping mutable state in a separate file.

---

## ⚠️ Potential Issues

### Issue 1: `controller.py` God Object (1002 lines)

**Severity:** 🔴 High  
**Location:** [controller.py](file:///home/mike/Projects/mike-heckman/tdd-harness/src/tdd_harness/controller.py)

The `TDDLoopController` class is a ~1000-line monolith containing:
- File security enforcement
- Phase validation logic
- All 5 phase orchestration loops
- Backup/revert logic
- Post-mortem generation
- Task file parsing & provisioning
- Dependency installation
- Web search & download functionality
- Sub-agent coordination

This violates SRP despite the class docstring explicitly claiming adherence to it. The phase loops (`run_blue_phase`, `run_red_phase`, `run_green_phase`, `run_magenta_loop`) share massive structural duplication (context assembly, tool-call loop, post-mortem injection, abort checking).

**Recommendation:** Extract each phase into a dedicated `PhaseRunner` class. Extract file security into a `SecurityInterceptor`. Extract task parsing into a `TaskLoader`.

---

### Issue 2: Singleton Anti-Patterns

**Severity:** 🟡 Medium  
**Locations:**
- [HarnessContext](file:///home/mike/Projects/mike-heckman/tdd-harness/src/tdd_harness/config.py#L43-L83) — singleton via `__new__`
- [ContextBuilder](file:///home/mike/Projects/mike-heckman/tdd-harness/src/tdd_harness/context.py#L75-L149) — singleton via `__new__`

Both use the `__new__`-override singleton pattern, which creates **global mutable state** that bleeds across test runs. The `conftest.py` has a fixture to reset `ContextBuilder._instance = None` between tests, but any missed teardown will cause subtle cross-test contamination. `HarnessContext` injects a `"test-"` prefix when `pytest` is in `sys.modules` (line 58) — a runtime behavior conditional on the test runner is a code smell.

**Recommendation:** Replace singletons with dependency injection. Pass `ContextBuilder` and `HarnessContext` as constructor parameters to `TDDLoopController` and `LLMClient`.

---

### Issue 3: Global Mutable Cache in Config Module

**Severity:** 🟡 Medium  
**Location:** [config.py L85-L118](file:///home/mike/Projects/mike-heckman/tdd-harness/src/tdd_harness/config.py#L85-L118)

`CACHE_TDD_DIRECTORIES` is a **module-level mutable global list** that persists across function calls. The `force` parameter for cache busting exists but is not used anywhere in the codebase. Tests need to manually clear this state or risk inheriting stale directory lists from prior test cases.

**Recommendation:** Convert `build_cache_tdd_directories` into a method on a `ConfigResolver` class that can be properly instantiated and scoped.

---

### Issue 4: Incorrect - resolved

---

### Issue 5: `object` Type Annotations as Escape Hatches

**Severity:** 🟡 Medium  
**Location:** Multiple files, especially:
- [llm.py L18-L19](file:///home/mike/Projects/mike-heckman/tdd-harness/src/tdd_harness/llm.py#L18-L20) — `config_loader: object, prompt: object`
- [registry.py L89](file:///home/mike/Projects/mike-heckman/tdd-harness/src/tdd_harness/registry.py#L89) — `tracker: object | None`
- [llm.py L83-L84](file:///home/mike/Projects/mike-heckman/tdd-harness/src/tdd_harness/llm.py#L83-L84) — `msg: object, registry: object | None`

The codebase frequently uses `object` as a type annotation with `# type: ignore` comments to avoid circular imports or complex typing. While the `# Reason:` comments explain the rationale, this undermines Pyright's ability to catch interface mismatches at static analysis time.

**Recommendation:** Define lightweight `Protocol` classes (like the existing [MCPClientProtocol](file:///home/mike/Projects/mike-heckman/tdd-harness/src/tdd_harness/registry.py#L36-L52)) for `ConfigLoader`, `PromptLike`, and `TrackerProtocol`.

---

### Issue 6: `sys.exit(1)` Called from Library Code

**Severity:** 🟡 Medium  
**Locations:**
- [controller.py L262](file:///home/mike/Projects/mike-heckman/tdd-harness/src/tdd_harness/controller.py#L262) — `abort()` calls `sys.exit(1)`
- [mcp_client.py L52](file:///home/mike/Projects/mike-heckman/tdd-harness/src/tdd_harness/mcp_client.py#L52) — `handle_failure()` calls `sys.exit(1)`

Calling `sys.exit()` from library code (not the CLI layer) makes the code untestable without mocking `sys.exit` and prevents clean embedding in other applications. The test suite uses `pytest.raises(SystemExit)` to work around this.

**Recommendation:** Raise dedicated exceptions (`HarnessAbort`, `MCPFatalError`) and let the CLI layer handle the exit.

---

### Issue 7: Phase Loop Duplication

**Severity:** 🟡 Medium  
**Location:** [controller.py](file:///home/mike/Projects/mike-heckman/tdd-harness/src/tdd_harness/controller.py) — lines 663–1002

The four phase runner methods (`run_blue_phase`, `run_red_phase`, `run_green_phase`, `run_magenta_loop`) share an almost identical structure:

1. Set `current_phase`
2. Parse task file frontmatter
3. Clear `ContextBuilder`, add phase prompt + task context + file sources
4. Get tools for phase
5. Reset tracker
6. Enter `while loop_active` → call `llm_client.chat()` → check `_phase_successful` → check `tracker.should_abort()`

The Green and Magenta phases add slight variations (test concepts, per-file coverage), but the core loop structure is copy-pasted. This is a DRY violation that will compound maintenance cost.

**Recommendation:** Extract a `_run_phase_loop(phase, context_assembler_fn)` template method.

---

### Issue 8: Mixed Import Styles (`from src.tdd_harness` vs relative)

**Severity:** 🟢 Low  
**Locations:**
- [llm.py](file:///home/mike/Projects/mike-heckman/tdd-harness/src/tdd_harness/llm.py#L9-L10): `from src.tdd_harness.config import ...`
- [sub_agents.py](file:///home/mike/Projects/mike-heckman/tdd-harness/src/tdd_harness/sub_agents.py#L5-L8): `from src.tdd_harness.context import ...`
- [adapters/base.py](file:///home/mike/Projects/mike-heckman/tdd-harness/src/tdd_harness/adapters/base.py#L7): `from src.tdd_harness.models.tool import ...`
- [controller.py](file:///home/mike/Projects/mike-heckman/tdd-harness/src/tdd_harness/controller.py#L19-L29): `from .config import ...` (relative)

The project mixes absolute `from src.tdd_harness.X` imports with relative `from .X` imports within the same package. This works because of the `hatch` build configuration, but it makes the package fragile to restructuring and violates PEP 8's recommendation for consistency.

**Recommendation:** Standardize on relative imports within the `tdd_harness` package.

---

### Issue 9: `install_dependencies` Uses `pip` Instead of `uv`

**Severity:** 🟡 Medium  
**Location:** [controller.py L449-L457](file:///home/mike/Projects/mike-heckman/tdd-harness/src/tdd_harness/controller.py#L449-L457)

```python
subprocess.check_call([sys.executable, "-m", "pip", "install", *packages])
```

The project mandates `uv` as the package manager (per `.agent-context.md`), yet the `install_dependencies` tool uses `pip`. This could install packages outside the `uv`-managed virtual environment, causing dependency drift.

**Recommendation:** Replace with `subprocess.check_call(["uv", "add", *packages])` or `["uv", "pip", "install", *packages]`.

---

### Issue 10: `_ConfigLoaderWrapper` Ad-Hoc Class in CLI

**Severity:** 🟢 Low  
**Location:** [cli.py L155-L160](file:///home/mike/Projects/mike-heckman/tdd-harness/src/tdd_harness/cli.py#L155-L160)

An inline class `_ConfigLoaderWrapper` is defined inside `async_main()` solely to satisfy the `LLMClient` constructor's expected interface. This is a symptom of Issue 5 (loose typing) — `LLMClient` accepts `config_loader: object` and calls `.get_config()` on it dynamically.

**Recommendation:** Define a `ConfigLoaderProtocol` and have `TddHarnessConfig` implement it directly, or simplify `LLMClient` to accept the config object directly.

---

### Issue 11: Missing `read_file` Tool in Phase Schemas

**Severity:** 🟢 Low  
**Location:** [tool_schemas.py](file:///home/mike/Projects/mike-heckman/tdd-harness/src/tdd_harness/tool_schemas.py)

The `AVAILABLE_TOOLS` list includes `stage_implementation`, `stage_test_implementation`, `success`, `abort`, `search_symbols`, `get_symbol_source`, and `ask_researcher` — but does **not** include `read_file` or `write_file`. These are registered via `controller.register_python_tool()` but not exposed in the phase-gated schema list, meaning the LLM may not "see" them depending on how tools are assembled for the chat call.

**Recommendation:** Add `read_file` to the `AVAILABLE_TOOLS` registry with appropriate phase gating.

---

### Issue 12: No Graceful Shutdown for MCP Connections

**Severity:** 🟢 Low  
**Location:** [mcp_client.py](file:///home/mike/Projects/mike-heckman/tdd-harness/src/tdd_harness/mcp_client.py)

The `MCPClient` has a `close()` method but the CLI's `async_main()` never calls it. If the harness aborts (via `sys.exit(1)` in `abort()`), the `AsyncExitStack` resources are leaked.

**Recommendation:** Wrap `async_main` in `async with mcp_client:` or use `try/finally`.

---

## 📊 Metrics Summary

| Metric | Value | Assessment |
|:-------|:------|:-----------|
| Test Coverage | 94.00% | ✅ Excellent |
| Test Count | 141 | ✅ Strong |
| Source Modules | 17 | Reasonable |
| Lines of Code (src) | ~3,300 | Moderate complexity |
| ADRs | 2 | ✅ Good practice |
| Phase Documentation | 7 detailed specs | ✅ Exceptional |
| Linting | `ruff` clean | ✅ |
| Type Checking | `pyright` (basic mode) | ⚠️ Many `# type: ignore` |

---

## 🎯 Prioritized Improvement Roadmap

| Priority | Issue | Effort | Impact |
|:---------|:------|:-------|:-------|
| 🟡 P1 | Replace `sys.exit()` with exceptions (Issue 6) | 1 hr | Testability & embedding |
| 🟡 P1 | Fix `pip` → `uv` in `install_dependencies` (Issue 9) | 10 min | Toolchain consistency |
| 🟡 P1 | Extract controller phases into separate runners (Issue 1) | 4 hr | Maintainability |
| 🟡 P2 | Replace singletons with DI (Issue 2) | 2 hr | Testability |
| 🟡 P2 | Standardize import style (Issue 8) | 30 min | Consistency |
| 🟡 P2 | Define Protocol classes for loose types (Issue 5) | 1 hr | Type safety |
| 🟢 P3 | DRY up phase loops (Issue 7) | 2 hr | Maintainability |
| 🟢 P3 | Add `read_file` to tool schemas (Issue 11) | 15 min | Completeness |
| 🟢 P3 | Graceful MCP shutdown (Issue 12) | 30 min | Resource cleanup |
| 🟢 P3 | Remove global config cache (Issue 3) | 30 min | Test isolation |
| 🟢 P3 | Inline class cleanup (Issue 10) | 15 min | Code clarity |

---

## Verdict

This is a **well-engineered, thoughtfully designed system** with a genuinely novel core concept (phase-gated file access for AI agents). The documentation quality — especially the phase specs and ADRs — is notably above average. The 94% test coverage with 141 tests demonstrates strong engineering discipline.

The primary risks are the controller monolith, singleton state management, and the `AssertionError` typo which could silently break the Red phase's core guarantee. Address the P0 issue immediately; the P1/P2 items should be resolved before wider adoption.
