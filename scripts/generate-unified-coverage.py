#!/usr/bin/env python3
"""
Script to generate unified coverage report and check metrics.
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
from argparse import Namespace
from pathlib import Path
from typing import Final


class AgentMetrics:
    """Class tracking codebase health metrics and history."""

    METRICS_FILE: Final[str] = ".agent-metrics.json"
    MINIMUM_COVERAGE_PCT: Final[str] = "minimum_coverage_percent"
    MAX_UNCOVERED_LINES: Final[str] = "max_uncovered_lines"
    LAST_KNOWN_COVERAGE_PCT: Final[str] = "last_known_coverage_percent"

    def __init__(self, project_dir: Path, filename: str = METRICS_FILE):
        """
        Initialize AgentMetrics.

        Args:
            project_dir: Project root directory.
            filename: Metrics file name.
        """
        self._dirty = True
        self._filename = project_dir / filename
        metrics = self.default_metrics_object()
        try:
            with open(self._filename) as fp:
                data = json.load(fp)
            for key in metrics.keys():
                if key in data:
                    metrics[key] = data[key]
        except Exception:
            pass

        self._metrics = metrics

    def save(self, force: bool = False) -> bool:
        """
        Save the metrics to disk.

        Args:
            force: If True, force save even if not dirty.

        Returns:
            True if saved successfully.
        """
        if not self._dirty and not force:
            return False
        try:
            with open(self._filename, "w") as fp:
                json.dump(self._metrics, fp, indent=4, separators=(",", ": "), sort_keys=True)
        except Exception:
            return False
        self._dirty = False
        return True

    def default_metrics_object(self) -> dict[str, int | float]:
        """
        Return the default set of tracking metrics.

        Returns:
            Dict containing metric defaults.
        """
        return {self.LAST_KNOWN_COVERAGE_PCT: 0, self.MINIMUM_COVERAGE_PCT: 80.0, self.MAX_UNCOVERED_LINES: 50}

    @property
    def minimum_coverage_pct(self) -> float:
        """Get the minimum acceptable coverage percentage."""
        return self._metrics[self.MINIMUM_COVERAGE_PCT]

    @property
    def max_uncovered_lines(self) -> int:
        """Get the maximum acceptable uncovered lines count."""
        return self._metrics[self.MAX_UNCOVERED_LINES]

    @property
    def last_known_coverage_pct(self) -> float:
        """Get the last historically recorded coverage percentage."""
        return self._metrics[self.LAST_KNOWN_COVERAGE_PCT]

    def set_last_known_coverage_pct(self, coverage: float) -> None:
        """
        Update the last known coverage percentage and save.

        Args:
            coverage: The new coverage percentage.
        """
        self._metrics[self.LAST_KNOWN_COVERAGE_PCT] = coverage
        self._dirty = True
        self.save()


FILELIST_HEADER = "| File | Lines | Covered | % Coverage | Missing |\n| :--- | ---: | ---: | ---: | :--- |\n"


def format_missing_lines(missing_lines: list) -> str:
    """Formats a list of missing line numbers into ranges."""
    if not missing_lines:
        return ""
    ranges = []
    start = missing_lines[0]
    end = missing_lines[0]
    for line in missing_lines[1:]:
        if line == end + 1:
            end = line
        else:
            ranges.append(str(start) if start == end else f"{start}-{end}")
            start = line
            end = line
    ranges.append(str(start) if start == end else f"{start}-{end}")
    return ", ".join(ranges)


def get_git_branch(project_root: Path) -> str:
    """
    Get the current git branch name.

    Args:
        project_root: The project directory.

    Returns:
        The current branch name or 'unknown'.
    """
    try:
        current_branch = (
            subprocess.check_output(
                ["git", "symbolic-ref", "HEAD", "--short"], stderr=subprocess.DEVNULL, cwd=project_root
            )
            .decode("utf-8")
            .strip()
        )
    except Exception:
        current_branch = "unknown"
    return current_branch


def report_summary(language: str, output: str, stmts: int, covered: int) -> tuple[str, int, int]:
    """
    Format the summary portion of the coverage report.

    Args:
        language: The target language.
        output: String buffer of output rows.
        stmts: Total number of lines.
        covered: Total covered lines.

    Returns:
        A tuple of (formatted_report, stmts, covered).
    """
    if stmts == 0:
        return "", 0, 0

    report = f"### {language}\n\n{FILELIST_HEADER}{output}"
    pct = (covered / stmts) * 100
    report += f"| **{language} Language Counts** | {stmts} | {covered} | {pct:.2f}% | |\n"

    return report, stmts, covered


def generate_lcov_coverage(coverage_dir: Path, project_root: Path) -> tuple[str, int, int]:
    """
    Process LCOV Coverage output from the given coverage directory.
    """
    language = "LCOV Aggregated"
    output = ""
    total_stmts = 0
    total_covered = 0

    if not coverage_dir or not coverage_dir.exists():
        return report_summary(language, output, total_stmts, total_covered)

    lcov_files = list(coverage_dir.glob("**/*.lcov"))
    if not lcov_files:
        return report_summary(language, output, total_stmts, total_covered)

    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from src.tdd_harness.coverage_parser import LcovParser

    parser = LcovParser(project_root)
    parser.parse_directory(coverage_dir)

    # Save unified standard lcov
    parser.write_unified_lcov(project_root / "coverage.lcov")

    for filename, stats in sorted(parser.file_stats.items()):
        f_stmts = len(stats["lines"])
        f_covered = sum(1 for hits in stats["lines"].values() if hits > 0)
        f_pct = (f_covered / f_stmts * 100) if f_stmts > 0 else 0.0

        missing = sorted([line_num for line_num, hits in stats["lines"].items() if hits == 0])
        missing_str = format_missing_lines(missing)

        total_stmts += f_stmts
        total_covered += f_covered
        output += f"| {filename:<40s} | {f_stmts} | {f_covered} | {f_pct:.2f}% | {missing_str} |\n"

    return report_summary(language, output, total_stmts, total_covered)


def parse_arguments() -> Namespace:
    """
    Parse command line execution arguments.

    Returns:
        Argparse populated Namespace object.
    """
    parser = argparse.ArgumentParser(description="Generate unified coverage report")
    parser.add_argument("--project-root", default=os.environ.get("PROJECT_ROOT", "."), help="Project root directory")
    parser.add_argument("--coverage-dir", default=None, help="Directory containing .lcov files to aggregate")
    return parser.parse_args()


def main() -> int:
    """
    Execute coverage metrics generation and analysis.

    Returns:
        Exit code 0 on success, 1 on failure.
    """
    args = parse_arguments()

    project_root = Path(args.project_root)
    coverage_dir = Path(args.coverage_dir) if args.coverage_dir else None

    current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_branch = get_git_branch(project_root)

    metrics = AgentMetrics(project_root)
    passed = True

    output_lcov, stmts, covered = generate_lcov_coverage(coverage_dir, project_root)
    uncovered = max(0, stmts - covered)

    if uncovered > metrics.max_uncovered_lines:
        output_lcov += f"**ERROR** Code has {uncovered} untested lines (max allowed: {metrics.max_uncovered_lines})!\n"
        passed = False
    elif stmts > metrics.max_uncovered_lines:
        coverage_pct = (covered / stmts) * 100
        if coverage_pct < metrics.minimum_coverage_pct:
            output_lcov += (
                f"**ERROR** Code coverage is {coverage_pct:.2f}% (minimum required: {metrics.minimum_coverage_pct}%)!\n"
            )
            passed = False
        metrics.set_last_known_coverage_pct(coverage_pct)

    status = "PASSED" if passed else "FAILED"

    final_report = "# Test Coverage Report\n\n"
    final_report += f"- **Date:** {current_date}\n"
    final_report += f"- **Branch:** `{current_branch}`\n"
    final_report += f"- **Status:** {status}\n\n"

    if output_lcov:
        final_report += output_lcov
    else:
        final_report += "**No accumulated coverage found.**\n"

    # Print to stdout
    print(final_report)

    # Save to coverage.md
    with open(project_root / "coverage.md", "w") as f:
        f.write(final_report)

    metrics.save()

    if not passed:
        print(
            f"\n**ACTION REQUIRED:** Please review the files with missing coverage and add test cases to reduce the total uncovered lines below {metrics.max_uncovered_lines} and ensure overall coverage is above {metrics.minimum_coverage_pct}%."
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
