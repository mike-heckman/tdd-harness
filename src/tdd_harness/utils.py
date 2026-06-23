"""
Utility functions for TDD Harness operations.
"""

import subprocess
from pathlib import Path


def install_dependencies(packages: list[str]) -> str:
    """
    Installs the missing dependencies into the virtual environment.
    """
    try:
        subprocess.check_call(["uv", "pip", "install", *packages])
        return f"Successfully installed: {', '.join(packages)}"
    except subprocess.CalledProcessError as e:
        return f"Failed to install dependencies: {e}"


def search_web(query: str) -> str:
    """
    Searches the web using duckduckgo-search.
    """
    try:
        from duckduckgo_search import DDGS  # type: ignore

        results = DDGS().text(query, max_results=5)
        if results:
            return "\n".join([f"- [{r['title']}]({r['href']})" for r in results])
        return "No results found."
    except ImportError:
        return "duckduckgo-search not installed"


def download_to_reference(url: str, library_name: str, filename: str) -> str:
    """
    Downloads a webpage, converts to markdown, and saves to docs/reference/{library_name}/{filename}.md.
    """
    try:
        import requests  # type: ignore
        from bs4 import BeautifulSoup  # type: ignore
        from markdownify import markdownify  # type: ignore

        resp = requests.get(url, timeout=10)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.content, "html.parser")
        md = markdownify(str(soup), heading_style="ATX")

        target_dir = Path("docs") / "reference" / library_name
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{filename}.md"
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(md)
        return f"Successfully saved to {target_path}"
    except ImportError:
        return "Missing requests, beautifulsoup4, or markdownify"
    except Exception as e:
        return f"Error downloading: {e}"
