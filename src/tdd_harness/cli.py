"""
Command-line interface for tdd-harness.
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from .config import resolve_config_directory


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """
    Parse command-line arguments.

    Args:
        args: Optional list of arguments to parse.

    Returns:
        argparse.Namespace: The parsed arguments.
    """
    parser = argparse.ArgumentParser(description="TDD Harness CLI")
    parser.add_argument(
        "--project-dir",
        help="Project directory to use for configuration",
        default=None,
    )
    parser.add_argument(
        "--phase",
        choices=["green", "blue"],
        help="Set the initial phase for the harness",
        default=None,
    )

    known_args, _ = parser.parse_known_args(args)
    return known_args


def main():
    """
    Main entry point for the CLI.
    """
    load_dotenv()
    args = parse_args()

    # Resolve the config directory
    try:
        config_dir = resolve_config_directory(args.project_dir)
    except FileNotFoundError as e:
        print(f"Error: {e}\nPlease run 'tdd-harness init' to set up a new project.")
        sys.exit(1)

    # Check git status
    import subprocess

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"], cwd=Path.cwd(), capture_output=True, text=True, check=True
        )

        if result.stdout.strip():
            print("Error: Git repository is not clean. Please commit or stash changes.")
            sys.exit(1)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Warning: Could not check git status. Proceeding anyway.")

    # Print the configuration directory for debugging
    print(f"Using config directory: {config_dir}")

    # Continue with the harness logic
    print("TDD Harness initialized successfully.")
    import asyncio

    asyncio.run(async_main(config_dir))


async def async_main(config_dir: Path):
    """
    Async execution phase for CLI.
    """
    from .config import load_tdd_harness_config
    from .mcp_client import MCPClient
    from .registry import ToolRegistry

    _ = load_tdd_harness_config(config_dir)
    mcp_client = MCPClient(server_config={})
    registry = ToolRegistry(mcp_client=mcp_client)
    await registry.initialize()

    try:
        await registry.dispatch("index_repo", {})
        await registry.dispatch("doc_index_repo", {})
    except ValueError:
        pass


if __name__ == "__main__":
    main()
