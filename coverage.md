# Test Coverage Report

- **Date:** 2026-06-22 20:53:29
- **Branch:** `task/0036`
- **Status:** PASSED

### LCOV Aggregated

| File | Lines | Covered | % Coverage | Missing |
| :--- | ---: | ---: | ---: | :--- |
| fix_tests.py                             | 25 | 0 | 0.00% | 1, 3, 5, 26-27, 29-34, 36-37, 40-45, 47, 50-53, 55 |
| src/tdd_harness/__init__.py              | 0 | 0 | 0.00% |  |
| src/tdd_harness/adapters/__init__.py     | 2 | 2 | 100.00% |  |
| src/tdd_harness/adapters/base.py         | 23 | 18 | 78.26% | 23, 42, 61, 80, 93 |
| src/tdd_harness/adapters/lcov_adapter.py | 18 | 14 | 77.78% | 23, 33, 44-45 |
| src/tdd_harness/adapters/pytest_adapter.py | 42 | 36 | 85.71% | 36-37, 51, 66-68 |
| src/tdd_harness/adapters/ruff_adapter.py | 29 | 26 | 89.66% | 32, 53-54 |
| src/tdd_harness/cli.py                   | 109 | 104 | 95.41% | 116-117, 136, 165, 220 |
| src/tdd_harness/config.py                | 89 | 77 | 86.52% | 96, 118, 134, 142-149, 167 |
| src/tdd_harness/context.py               | 74 | 71 | 95.95% | 56, 146-147 |
| src/tdd_harness/controller.py            | 525 | 445 | 84.76% | 108, 127-130, 157-158, 187, 217, 249, 258-261, 264-268, 270-271, 278, 294, 303-306, 308-309, 333, 339, 348-349, 376, 381, 383, 386, 422, 427-428, 460-465, 476, 497-498, 509-510, 543-544, 560-561, 572-573, 617, 633-634, 644, 671, 673-679, 685-686, 712, 726, 746, 755, 777-778, 783, 791-792 |
| src/tdd_harness/coverage_parser.py       | 53 | 50 | 94.34% | 50, 53-54 |
| src/tdd_harness/exceptions.py            | 8 | 8 | 100.00% |  |
| src/tdd_harness/llm.py                   | 107 | 104 | 97.20% | 114-115, 177 |
| src/tdd_harness/mcp_client.py            | 72 | 66 | 91.67% | 38-39, 77, 105-107 |
| src/tdd_harness/models/__init__.py       | 2 | 2 | 100.00% |  |
| src/tdd_harness/models/tool.py           | 10 | 10 | 100.00% |  |
| src/tdd_harness/phase.py                 | 9 | 9 | 100.00% |  |
| src/tdd_harness/prompt.py                | 49 | 49 | 100.00% |  |
| src/tdd_harness/registry.py              | 150 | 149 | 99.33% | 128 |
| src/tdd_harness/runner.py                | 140 | 124 | 88.57% | 83, 85, 87, 105, 117-120, 252, 276-279, 283, 292, 303 |
| src/tdd_harness/security.py              | 43 | 43 | 100.00% |  |
| src/tdd_harness/sub_agents.py            | 43 | 43 | 100.00% |  |
| src/tdd_harness/task_loader.py           | 67 | 64 | 95.52% | 41, 86-87 |
| src/tdd_harness/tool_schemas.py          | 4 | 4 | 100.00% |  |
| src/tdd_harness/tracker.py               | 42 | 40 | 95.24% | 87, 107 |
| src/tdd_harness/utils.py                 | 36 | 35 | 97.22% | 26 |
| tests/conftest.py                        | 7 | 7 | 100.00% |  |
| tests/test_cli.py                        | 213 | 211 | 99.06% | 89-90 |
| tests/test_config.py                     | 40 | 40 | 100.00% |  |
| tests/test_context.py                    | 23 | 23 | 100.00% |  |
| tests/test_controller.py                 | 389 | 387 | 99.49% | 19, 575 |
| tests/test_coverage_parser.py            | 58 | 58 | 100.00% |  |
| tests/test_lcov_adapter.py               | 20 | 20 | 100.00% |  |
| tests/test_llm.py                        | 199 | 199 | 100.00% |  |
| tests/test_mcp_client.py                 | 122 | 122 | 100.00% |  |
| tests/test_prompt.py                     | 60 | 60 | 100.00% |  |
| tests/test_pytest_adapter.py             | 36 | 36 | 100.00% |  |
| tests/test_registry.py                   | 127 | 125 | 98.43% | 40, 90 |
| tests/test_ruff_adapter.py               | 31 | 31 | 100.00% |  |
| tests/test_runner.py                     | 83 | 82 | 98.80% | 75 |
| tests/test_security.py                   | 68 | 68 | 100.00% |  |
| tests/test_sub_agents.py                 | 68 | 68 | 100.00% |  |
| tests/test_task_loader.py                | 106 | 105 | 99.06% | 51 |
| tests/test_tracker.py                    | 58 | 58 | 100.00% |  |
| tests/test_utils.py                      | 55 | 55 | 100.00% |  |
| **LCOV Aggregated Language Counts** | 3534 | 3348 | 94.74% | |

