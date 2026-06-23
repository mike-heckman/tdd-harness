# Test Coverage Report

- **Date:** 2026-06-22 20:24:45
- **Branch:** `task/0034`
- **Status:** PASSED

### LCOV Aggregated

| File | Lines | Covered | % Coverage | Missing |
| :--- | ---: | ---: | ---: | :--- |
| src/tdd_harness/__init__.py              | 0 | 0 | 0.00% |  |
| src/tdd_harness/adapters/__init__.py     | 2 | 2 | 100.00% |  |
| src/tdd_harness/adapters/base.py         | 23 | 18 | 78.26% | 23, 42, 61, 80, 93 |
| src/tdd_harness/adapters/lcov_adapter.py | 18 | 14 | 77.78% | 23, 33, 44-45 |
| src/tdd_harness/adapters/pytest_adapter.py | 42 | 36 | 85.71% | 36-37, 51, 66-68 |
| src/tdd_harness/adapters/ruff_adapter.py | 29 | 26 | 89.66% | 32, 53-54 |
| src/tdd_harness/cli.py                   | 109 | 104 | 95.41% | 116-117, 136, 165, 220 |
| src/tdd_harness/config.py                | 89 | 77 | 86.52% | 96, 118, 134, 142-149, 167 |
| src/tdd_harness/context.py               | 74 | 71 | 95.95% | 56, 146-147 |
| src/tdd_harness/controller.py            | 649 | 527 | 81.20% | 187-190, 217-218, 247, 277, 309, 318-321, 324-328, 330-331, 338, 354, 363-366, 368-369, 393, 399, 408-409, 436, 441, 443, 446, 467-470, 480-481, 483-484, 486-487, 489-494, 497-498, 507, 521, 530, 534-535, 538, 542, 545, 548, 554-556, 559, 561-567, 569-573, 607, 612-613, 645-650, 661, 682-683, 694-695, 728-729, 745-746, 757-758, 802, 818-819, 829, 856, 858-864, 870-871, 897, 911, 931, 940, 962-963, 968, 976-977 |
| src/tdd_harness/coverage_parser.py       | 53 | 50 | 94.34% | 50, 53-54 |
| src/tdd_harness/exceptions.py            | 4 | 4 | 100.00% |  |
| src/tdd_harness/llm.py                   | 107 | 104 | 97.20% | 114-115, 177 |
| src/tdd_harness/mcp_client.py            | 72 | 66 | 91.67% | 38-39, 77, 105-107 |
| src/tdd_harness/models/__init__.py       | 2 | 2 | 100.00% |  |
| src/tdd_harness/models/tool.py           | 10 | 10 | 100.00% |  |
| src/tdd_harness/prompt.py                | 49 | 49 | 100.00% |  |
| src/tdd_harness/registry.py              | 150 | 149 | 99.33% | 128 |
| src/tdd_harness/runner.py                | 140 | 124 | 88.57% | 83, 85, 87, 105, 117-120, 252, 276-279, 283, 292, 303 |
| src/tdd_harness/sub_agents.py            | 43 | 43 | 100.00% |  |
| src/tdd_harness/tool_schemas.py          | 4 | 4 | 100.00% |  |
| src/tdd_harness/tracker.py               | 42 | 40 | 95.24% | 87, 107 |
| tests/conftest.py                        | 7 | 7 | 100.00% |  |
| tests/test_cli.py                        | 213 | 211 | 99.06% | 89-90 |
| tests/test_config.py                     | 40 | 40 | 100.00% |  |
| tests/test_context.py                    | 23 | 23 | 100.00% |  |
| tests/test_controller.py                 | 502 | 499 | 99.40% | 18, 450, 775 |
| tests/test_coverage_parser.py            | 58 | 58 | 100.00% |  |
| tests/test_lcov_adapter.py               | 20 | 20 | 100.00% |  |
| tests/test_llm.py                        | 199 | 199 | 100.00% |  |
| tests/test_mcp_client.py                 | 122 | 122 | 100.00% |  |
| tests/test_prompt.py                     | 60 | 60 | 100.00% |  |
| tests/test_pytest_adapter.py             | 36 | 36 | 100.00% |  |
| tests/test_registry.py                   | 127 | 125 | 98.43% | 40, 90 |
| tests/test_ruff_adapter.py               | 31 | 31 | 100.00% |  |
| tests/test_runner.py                     | 83 | 82 | 98.80% | 75 |
| tests/test_sub_agents.py                 | 68 | 68 | 100.00% |  |
| tests/test_tracker.py                    | 58 | 58 | 100.00% |  |
| **LCOV Aggregated Language Counts** | 3358 | 3159 | 94.07% | |

