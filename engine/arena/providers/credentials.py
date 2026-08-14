"""
Provider credential resolution.

Credentials are resolved only during adapter construction and never
stored in RuntimeProfile, ModelBinding, logs, checkpoints, or artifacts.
"""

import os
from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class CredentialResolver(Protocol):
    """Protocol for resolving provider-specific credentials."""

    def get(self, provider: str, credential: str) -> Optional[str]:
        """Look up a credential for a given provider.

        Args:
            provider: Provider name (e.g., "openai", "anthropic").
            credential: Credential name (e.g., "api_key").

        Returns:
            The credential value, or None if not found.
        """
        ...


class EnvironmentCredentialResolver:
    """Resolves credentials from environment variables.

    Mapping:
        ("openai", "api_key")    -> OPENAI_API_KEY
        ("anthropic", "api_key") -> ANTHROPIC_API_KEY
        ("gemini", "api_key")    -> GEMINI_API_KEY

    General pattern: {PROVIDER}_{CREDENTIAL} in uppercase.
    """

    # Explicit overrides for non-obvious mappings
    _ENV_MAP: dict[tuple[str, str], str] = {
        ("openai", "api_key"): "OPENAI_API_KEY",
        ("anthropic", "api_key"): "ANTHROPIC_API_KEY",
        ("gemini", "api_key"): "GEMINI_API_KEY",
        ("google", "api_key"): "GOOGLE_API_KEY",
    }

    def get(self, provider: str, credential: str) -> Optional[str]:
        # Check explicit map first
        env_var = self._ENV_MAP.get((provider, credential))
        if env_var is None:
            # Fall back to convention: PROVIDER_CREDENTIAL
            env_var = f"{provider.upper()}_{credential.upper()}"

        return os.environ.get(env_var)
