"""
Prompt manager for loading prompts, validating hashes, and caching token counts.
"""

import hashlib
import logging
from pathlib import Path
from typing import Any

import yaml

from .config import load_prompt_config
from .context import Context, ContextType

logger = logging.getLogger(__name__)


class Prompt:
    """
    Manages loading of a prompt configuration, checking its hash against a cache.

    It also manages token counts for different models.
    """

    def __init__(self, prompt_name: str, project_dir: str | Path | None = None) -> None:
        """
        Initialize the Prompt class.

        Args:
            prompt_name: The name of the prompt to load.
            project_dir: The project root directory where the cache should live.
        """
        self.prompt_name = prompt_name
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.prompt_config = load_prompt_config(prompt_name, project_dir=self.project_dir)

        self.prompt_text = self.prompt_config.prompt
        self.prompt_hash = self._compute_hash(self.prompt_text)

        self.cache_file = self.project_dir / ".prompt-cache.yaml"
        self._cache_data = self._load_cache()

        self._validate_cache()

    def _compute_hash(self, text: str) -> str:
        """
        Compute the SHA256 hash of the given text.

        Args:
            text: The text to hash.

        Returns:
            The SHA256 hash string.
        """
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _load_cache(self) -> dict[str, Any]:  # Reason: yaml.safe_load returns arbitrary nested dictionaries
        """
        Load the cache from the `.prompt-cache.yaml` file.

        Returns:
            A dictionary containing the parsed cache data.
        """
        if self.cache_file.exists():
            with open(self.cache_file) as f:
                return yaml.safe_load(f) or {}
        return {}

    def _save_cache(self) -> None:
        """
        Save the current cache state back to the cache file.
        """
        with open(self.cache_file, "w") as f:
            yaml.safe_dump(self._cache_data, f)

    def _validate_cache(self) -> None:
        """
        Validate the cached prompt hash.

        If the hash has changed or is missing, update the cache and clear out old
        token counts.
        """
        if "prompt_caches" not in self._cache_data:
            self._cache_data["prompt_caches"] = {}

        if self.prompt_name not in self._cache_data["prompt_caches"]:
            self._cache_data["prompt_caches"][self.prompt_name] = {
                "prompt_hash": self.prompt_hash,
                "token_counts": {},
            }
            self._save_cache()
            return

        cached_prompt = self._cache_data["prompt_caches"][self.prompt_name]
        if cached_prompt.get("prompt_hash") != self.prompt_hash:
            logger.info("Prompt '%s' hash changed, invalidating token cache.", self.prompt_name)
            cached_prompt["prompt_hash"] = self.prompt_hash
            cached_prompt["token_counts"] = {}
            self._save_cache()

    def token_size(self, model: str) -> int | None:
        """
        Get the cached token count for a specific model.

        Args:
            model: The name of the model.

        Returns:
            The cached token count, or None if not available.
        """
        return self._cache_data["prompt_caches"][self.prompt_name]["token_counts"].get(model)

    def update_token_size(self, model: str, count: int) -> None:
        """
        Update the token count for a specific model and save the cache.

        Args:
            model: The name of the model.
            count: The token count to store.
        """
        self._cache_data["prompt_caches"][self.prompt_name]["token_counts"][model] = count
        self._save_cache()

    def get_system_message(self, model: str | None = None) -> Context:
        """
        Get a Context object representing this prompt as a system message.

        Args:
            model: Optional model name to look up the exact cached token count.

        Returns:
            A Context object initialized with the prompt text and metadata.
        """
        token_count = self.token_size(model) if model else None

        return Context(
            text=self.prompt_text,
            context_type=ContextType.SYSTEM,
            token_count=token_count,
            is_count_estimated=(token_count is None),
            metadata={
                "prompt_name": self.prompt_name,
                "prompt_hash": self.prompt_hash,
            },
        )
