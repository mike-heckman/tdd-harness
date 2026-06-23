import subprocess
from unittest.mock import MagicMock, patch

from src.tdd_harness.utils import download_to_reference, install_dependencies, search_web


@patch("subprocess.check_call")
def test_install_dependencies(mock_call):
    res = install_dependencies(["testpkg"])
    mock_call.assert_called_once_with(["uv", "pip", "install", "testpkg"])
    assert "Successfully installed" in res


@patch("subprocess.check_call")
def test_install_dependencies_fail(mock_call):
    mock_call.side_effect = subprocess.CalledProcessError(1, "cmd")
    res = install_dependencies(["testpkg"])
    mock_call.assert_called_once_with(["uv", "pip", "install", "testpkg"])
    assert "Failed to install dependencies" in res


def test_search_web_no_module():
    import sys

    with patch.dict(sys.modules, {"duckduckgo_search": None}):
        res = search_web("query")
        assert "duckduckgo-search not installed" in res


def test_download_to_reference_no_module():
    import sys

    with patch.dict(sys.modules, {"requests": None}):
        res = download_to_reference("url", "lib", "file")
        assert "Missing requests" in res


def test_search_web_success():
    import sys

    mock_ddgs = MagicMock()
    mock_ddgs.return_value.text.return_value = [{"title": "T", "href": "http"}]
    mock_ddgs_module = MagicMock()
    mock_ddgs_module.DDGS = mock_ddgs
    with patch.dict(sys.modules, {"duckduckgo_search": mock_ddgs_module}):
        res = search_web("query")
        assert "http" in res


def test_download_to_reference_success(tmp_path):
    import sys

    mock_req = MagicMock()
    mock_req.get.return_value.content = b"<html></html>"
    mock_bs4 = MagicMock()
    mock_md = MagicMock()
    mock_md.markdownify.return_value = "md"
    with patch.dict(sys.modules, {"requests": mock_req, "bs4": mock_bs4, "markdownify": mock_md}):
        with patch("src.tdd_harness.utils.Path") as mock_path:
            mock_dir = MagicMock()
            mock_path.return_value.__truediv__.return_value.__truediv__.return_value = mock_dir
            mock_dir.__truediv__.return_value = tmp_path / "file.md"
            res = download_to_reference("url", "lib", "file")
            assert "Successfully saved" in res


def test_download_to_reference_error():
    import sys

    mock_req = MagicMock()
    mock_req.get.side_effect = Exception("oops")
    with patch.dict(sys.modules, {"requests": mock_req, "bs4": MagicMock(), "markdownify": MagicMock()}):
        res = download_to_reference("url", "lib", "file")
        assert "Error downloading" in res
