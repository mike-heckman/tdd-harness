# Test Coverage Report

- **Date:** 2026-06-22 17:04:11
- **Branch:** `performance/0033`
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
| src/tdd_harness/cli.py                   | 104 | 99 | 95.19% | 115-116, 135, 160, 215 |
| src/tdd_harness/config.py                | 89 | 77 | 86.52% | 96, 118, 134, 142-149, 167 |
| src/tdd_harness/context.py               | 74 | 71 | 95.95% | 56, 146-147 |
| src/tdd_harness/controller.py            | 648 | 526 | 81.17% | 186-189, 216-217, 246, 276, 308, 317-320, 323-327, 329-330, 337, 353, 362-365, 367-368, 392, 398, 407-408, 435, 440, 442, 445, 466-469, 479-480, 482-483, 485-486, 488-493, 496-497, 506, 520, 529, 533-534, 537, 541, 544, 547, 553-555, 558, 560-566, 568-572, 606, 611-612, 644-649, 660, 681-682, 693-694, 727-728, 744-745, 756-757, 801, 817-818, 828, 855, 857-863, 869-870, 896, 910, 930, 939, 961-962, 967, 975-976 |
| src/tdd_harness/coverage_parser.py       | 53 | 50 | 94.34% | 50, 53-54 |
| src/tdd_harness/llm.py                   | 107 | 104 | 97.20% | 116-117, 180 |
| src/tdd_harness/mcp_client.py            | 71 | 65 | 91.55% | 36-37, 75, 103-105 |
| src/tdd_harness/models/__init__.py       | 2 | 2 | 100.00% |  |
| src/tdd_harness/models/tool.py           | 10 | 10 | 100.00% |  |
| src/tdd_harness/prompt.py                | 49 | 49 | 100.00% |  |
| src/tdd_harness/registry.py              | 150 | 149 | 99.33% | 128 |
| src/tdd_harness/runner.py                | 140 | 124 | 88.57% | 83, 85, 87, 105, 117-120, 252, 276-279, 283, 292, 303 |
| src/tdd_harness/sub_agents.py            | 43 | 43 | 100.00% |  |
| src/tdd_harness/tool_schemas.py          | 4 | 4 | 100.00% |  |
| src/tdd_harness/tracker.py               | 42 | 40 | 95.24% | 87, 107 |
| tests/conftest.py                        | 7 | 7 | 100.00% |  |
| tests/test_cli.py                        | 181 | 179 | 98.90% | 89-90 |
| tests/test_config.py                     | 40 | 40 | 100.00% |  |
| tests/test_context.py                    | 23 | 23 | 100.00% |  |
| tests/test_controller.py                 | 501 | 498 | 99.40% | 17, 449, 774 |
| tests/test_coverage_parser.py            | 58 | 58 | 100.00% |  |
| tests/test_lcov_adapter.py               | 20 | 20 | 100.00% |  |
| tests/test_llm.py                        | 199 | 199 | 100.00% |  |
| tests/test_mcp_client.py                 | 123 | 123 | 100.00% |  |
| tests/test_prompt.py                     | 60 | 60 | 100.00% |  |
| tests/test_pytest_adapter.py             | 36 | 36 | 100.00% |  |
| tests/test_registry.py                   | 127 | 125 | 98.43% | 40, 90 |
| tests/test_ruff_adapter.py               | 31 | 31 | 100.00% |  |
| tests/test_runner.py                     | 83 | 82 | 98.80% | 75 |
| tests/test_sub_agents.py                 | 68 | 68 | 100.00% |  |
| tests/test_tracker.py                    | 58 | 58 | 100.00% |  |
| **LCOV Aggregated Language Counts** | 3315 | 3116 | 94.00% | |

