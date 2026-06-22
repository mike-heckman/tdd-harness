"""
Command-line interface for tdd-harness.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

from .config import load_tdd_harness_config, resolve_config_directory
from .controller import Phase, TDDLoopController
from .mcp_client import MCPClient
from .registry import ToolRegistry


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

    asyncio.run(async_main(config_dir))


async def async_main(config_dir: Path):
    """
    Async execution phase for CLI.
    """
    config = load_tdd_harness_config(config_dir)
    mcp_client = MCPClient(server_config={})
    registry = ToolRegistry(mcp_client=mcp_client)
    await registry.initialize()

    controller = TDDLoopController(config, registry)

    print("Running Amber pre-flight validation...")
    if not controller.pre_flight_validation():
        print("Error: Amber pre-flight validation failed. Please fix issues before proceeding.")
        sys.exit(1)

    print("Amber phase complete. System is ready.")

    try:
        await registry.dispatch("index_repo", {})
        await registry.dispatch("doc_index_repo", {})
    except ValueError:
        pass

    print("Transitioning to Blue phase (Structural Blueprint)...")
    controller.current_phase = Phase.BLUE

    print("Transitioning to Red phase (Test Generation)...")
    controller.current_phase = Phase.RED

    print("Transitioning to Green phase (Implementation)...")
    controller.current_phase = Phase.GREEN

    print("Transitioning to Magenta phase (Coverage Guardrail)...")
    await controller.run_magenta_loop()

    print("TDD Loop execution complete.")


if __name__ == "__main__":
    main()
