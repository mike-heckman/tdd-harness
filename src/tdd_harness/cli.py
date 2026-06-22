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
        "command",
        nargs="?",
        help="Command to run (e.g. init)",
        default=None,
    )
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


def init_project(project_dir: str | None) -> None:
    """
    Initialize a new tdd-harness project.

    Args:
        project_dir: Optional project directory to initialize.
    """
    base_dir = Path(project_dir).resolve() if project_dir else Path.cwd()
    config_dir = base_dir / ".tdd-harness"

    if config_dir.exists():
        print(f"Directory {config_dir} already exists. Initialization aborted.")
        return

    prompts_dir = config_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    config_yaml = """llm:
  provider: openai
  base_url: http://localhost:8000/v1
  context_size: 8192
  minimum_available_context: 2048
  keep_turns: 1

harness:
  coverage_threshold: 80.0
  max_uncovered_lines: 50
  anti_thrashing:
    max_duplicate_failures: 3
    max_window_failures: 4
    window_size: 5

mcp_servers: []
extensions: []
"""
    (config_dir / "config.yaml").write_text(config_yaml)

    system_message_yaml = """prompt: |
  You are an AI developer...
"""
    (prompts_dir / "system_message.yaml").write_text(system_message_yaml)

    compression_prompt_yaml = """prompt: |
  Summarize the following chat history concisely, retaining all critical technical decisions and failures.
"""
    (prompts_dir / "compression_prompt.yaml").write_text(compression_prompt_yaml)

    print(f"Initialized tdd-harness in {config_dir}")


def main():
    """
    Main entry point for the CLI.
    """
    load_dotenv()
    args = parse_args()

    if args.command == "init":
        init_project(args.project_dir)
        sys.exit(0)

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
