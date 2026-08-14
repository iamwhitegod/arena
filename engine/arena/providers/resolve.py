"""
Single entry point for resolving CLI arguments into an InferenceBundle.

Called once per pipeline run at the Python composition root.
"""

from typing import Optional

from .credentials import CredentialResolver, EnvironmentCredentialResolver
from .profile import Capability, RuntimeProfile
from .registry import InferenceBundle, ProviderRegistry


def resolve_inference(
    *,
    required: set[Capability],
    provider: Optional[str] = None,
    chat_provider: Optional[str] = None,
    chat_model: Optional[str] = None,
    overview_chat_provider: Optional[str] = None,
    overview_chat_model: Optional[str] = None,
    embedding_provider: Optional[str] = None,
    embedding_model: Optional[str] = None,
    transcription_provider: Optional[str] = None,
    transcription_model: Optional[str] = None,
    credentials: Optional[CredentialResolver] = None,
    registry: Optional[ProviderRegistry] = None,
) -> InferenceBundle:
    """CLI args -> RuntimeProfile -> InferenceBundle.

    This is the single function all Python entry points call.
    It builds only the requested capabilities.

    Args:
        required: Which capabilities this command needs.
        provider: Shorthand — sets all capabilities to this provider.
        *_provider/*_model: Per-capability overrides.
        credentials: Credential resolver (defaults to env vars).
        registry: Provider registry (defaults to production factories).

    Returns:
        InferenceBundle with only the requested models constructed.
    """
    profile = RuntimeProfile.from_args(
        provider=provider,
        chat_provider=chat_provider,
        chat_model=chat_model,
        overview_chat_provider=overview_chat_provider,
        overview_chat_model=overview_chat_model,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
        transcription_provider=transcription_provider,
        transcription_model=transcription_model,
    )

    creds = credentials or EnvironmentCredentialResolver()
    reg = registry or ProviderRegistry()

    return reg.build_required(profile, required, creds)
