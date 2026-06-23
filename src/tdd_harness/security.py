"""
Security module for file and path validation within the TDD harness.
"""

from pathlib import Path

from .exceptions import SecurityError
from .phase import Phase


class SecurityInterceptor:
    """
    Manages security rules based on the current TDD phase and globally.
    """

    def __init__(self, initial_phase: Phase = Phase.AMBER):
        """
        Initialize with an initial phase.
        """
        self.current_phase = initial_phase

    def is_path_allowed(self, path: str, is_write: bool) -> bool:
        """
        Enforces global restrictions and phase-specific access rules.
        """
        target = Path(path).resolve()
        cwd = Path.cwd().resolve()

        try:
            rel_path = target.relative_to(cwd)
        except ValueError:
            return False  # Path is outside the workspace

        parts = rel_path.parts
        if not parts:
            return True

        # Global Lockdown
        if is_write and parts:
            p0 = parts[0].lower()
            if p0 in (".tdd-harness", ".git"):
                return False
            if len(parts) >= 2 and p0 == "src" and parts[1].lower() == "tdd_harness":
                return False

        # Phase-specific Write constraints
        if is_write and parts:
            p0 = parts[0].lower()
            if self.current_phase in (Phase.AMBER, Phase.BLUE, Phase.GREEN):
                # src/: rw, test/: ro
                if p0 == "tests":
                    return False
            elif self.current_phase in (Phase.RED, Phase.MAGENTA):
                # src/: ro, test/: rw
                if p0 == "src":
                    return False

        return True

    def read_file_safe(self, path: str) -> str:
        """
        Safely read a file, respecting phase access rules.
        """
        if not self.is_path_allowed(path, is_write=False):
            raise SecurityError(f"Read access to {path} denied.")
        with open(path, encoding="utf-8") as f:
            return f.read()

    def write_file_safe(self, path: str, content: str) -> str:
        """
        Safely write a file, respecting phase access rules.
        """
        if not self.is_path_allowed(path, is_write=True):
            raise SecurityError(f"Write access to {path} denied.")
        # Ensure parent dirs exist
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {path}"
