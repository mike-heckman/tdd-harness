"""
Coverage parser module for processing lcov files.
"""

from pathlib import Path
from typing import Any


class LcovParser:
    """
    Parser for reading and aggregating lcov coverage files.
    """

    def __init__(self, project_root: Path):
        """
        Initialize LcovParser.

        Args:
            project_root: Project root directory.
        """
        self.project_root = project_root
        # Mapping of filename -> { 'lines': { line_num: hits } }
        self.file_stats: dict[str, dict[str, Any]] = {}

    def parse_directory(self, coverage_dir: Path) -> None:
        """
        Parses all .lcov files in a given directory and aggregates the stats.
        """
        if not coverage_dir or not coverage_dir.exists():
            return

        lcov_files = list(coverage_dir.glob("**/*.lcov"))
        for lcov_file in lcov_files:
            self.parse_file(lcov_file)

    def parse_file(self, lcov_file: Path) -> None:
        """
        Parses a single .lcov file.
        """
        try:
            with open(lcov_file) as f:
                current_file = None
                for line in f:
                    line = line.strip()
                    if line.startswith("SF:"):
                        raw_path = line[3:]
                        try:
                            abs_path = Path(raw_path).resolve()
                            if self.project_root.resolve() in abs_path.parents:
                                current_file = str(abs_path.relative_to(self.project_root.resolve()))
                            else:
                                current_file = raw_path
                        except ValueError:
                            current_file = raw_path

                        if current_file not in self.file_stats:
                            self.file_stats[current_file] = {"lines": {}}
                    elif line.startswith("DA:") and current_file:
                        parts = line[3:].split(",")
                        if len(parts) >= 2:
                            line_num = int(parts[0])
                            hits = int(parts[1])
                            if line_num not in self.file_stats[current_file]["lines"]:
                                self.file_stats[current_file]["lines"][line_num] = 0
                            self.file_stats[current_file]["lines"][line_num] += hits
        except Exception as e:
            print(f"Warning: Failed to parse {lcov_file}: {e}")

    def write_unified_lcov(self, output_path: Path) -> None:
        """
        Writes the aggregated file_stats to a unified standard .lcov file.
        """
        with open(output_path, "w") as f:
            for filename, stats in sorted(self.file_stats.items()):
                f.write(f"SF:{filename}\n")
                for line_num, hits in sorted(stats["lines"].items()):
                    f.write(f"DA:{line_num},{hits}\n")
                f.write("end_of_record\n")

    def get_missing_coverage(self) -> dict[str, list[int]]:
        """
        Returns a mapping of file_path to list of missing line numbers.
        """
        missing_coverage = {}
        for filename, stats in self.file_stats.items():
            missing = sorted([line_num for line_num, hits in stats["lines"].items() if hits == 0])
            if missing:
                missing_coverage[filename] = missing
        return missing_coverage
