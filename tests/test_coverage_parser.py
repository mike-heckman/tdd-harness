import pytest

from src.tdd_harness.coverage_parser import LcovParser


@pytest.fixture
def parser(tmp_path):
    return LcovParser(project_root=tmp_path)


def test_parse_directory_empty(parser, tmp_path):
    parser.parse_directory(tmp_path)
    assert parser.file_stats == {}


def test_parse_directory_not_exists(parser, tmp_path):
    parser.parse_directory(tmp_path / "nonexistent")
    assert parser.file_stats == {}


def test_parse_file_success(parser, tmp_path):
    lcov_file = tmp_path / "coverage.lcov"
    lcov_file.write_text("SF:src/main.py\nDA:1,1\nDA:2,0\nDA:3,2\nend_of_record\n")

    # Needs a real file structure to test relative_to correctly
    (tmp_path / "src").mkdir()
    (tmp_path / "src/main.py").touch()

    parser.parse_file(lcov_file)
    assert "src/main.py" in parser.file_stats
    assert parser.file_stats["src/main.py"]["lines"] == {1: 1, 2: 0, 3: 2}


def test_parse_directory_success(parser, tmp_path):
    cov_dir = tmp_path / "cov"
    cov_dir.mkdir()
    lcov_file = cov_dir / "coverage.lcov"
    lcov_file.write_text("SF:src/main.py\nDA:1,1\nend_of_record\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src/main.py").touch()

    parser.parse_directory(cov_dir)
    assert "src/main.py" in parser.file_stats
    assert parser.file_stats["src/main.py"]["lines"] == {1: 1}


def test_parse_file_not_in_project_root(parser, tmp_path):
    lcov_file = tmp_path / "coverage.lcov"
    # file outside project root
    lcov_file.write_text("SF:/outside/main.py\nDA:1,1\nend_of_record\n")

    parser.parse_file(lcov_file)
    assert "/outside/main.py" in parser.file_stats


def test_parse_file_value_error(parser, tmp_path):
    # This simulates a path issue
    lcov_file = tmp_path / "coverage.lcov"
    lcov_file.write_text(
        "SF:\n"  # Empty SF to trigger potential error/fallback
        "DA:1,1\n"
        "end_of_record\n"
    )
    parser.parse_file(lcov_file)
    assert "" in parser.file_stats


def test_parse_file_exception(parser, tmp_path, capsys):
    # test warning message print when exception occurs
    lcov_file = tmp_path / "coverage.lcov"
    # Create a directory where it expects a file to raise IsADirectoryError
    lcov_file.mkdir()

    parser.parse_file(lcov_file)

    captured = capsys.readouterr()
    assert "Warning: Failed to parse" in captured.out


def test_write_unified_lcov(parser, tmp_path):
    parser.file_stats = {"src/main.py": {"lines": {1: 1, 2: 0}}}
    output_path = tmp_path / "unified.lcov"
    parser.write_unified_lcov(output_path)

    content = output_path.read_text()
    assert "SF:src/main.py\n" in content
    assert "DA:1,1\n" in content
    assert "DA:2,0\n" in content
    assert "end_of_record\n" in content


def test_get_missing_coverage(parser):
    parser.file_stats = {"src/main.py": {"lines": {1: 1, 2: 0, 3: 0}}, "src/other.py": {"lines": {1: 1, 2: 1}}}
    missing = parser.get_missing_coverage()
    assert missing == {"src/main.py": [2, 3]}
