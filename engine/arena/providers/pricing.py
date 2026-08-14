"""
Centralized pricing table for cloud inference providers.

Replaces hardcoded pricing scattered across editorial modules.
Values are estimates verified against each provider's official pricing.
Unknown provider/model combinations return None, never zero.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class PricingEntry:
    provider: str
    model: str
    effective_from: date
    input_per_million: Optional[Decimal] = None
    output_per_million: Optional[Decimal] = None
    audio_per_minute: Optional[Decimal] = None


# Keyed by (provider, model) for O(1) lookup.
PRICING: dict[tuple[str, str], PricingEntry] = {
    ("openai", "gpt-4o"): PricingEntry(
        provider="openai",
        model="gpt-4o",
        effective_from=date(2024, 5, 13),
        input_per_million=Decimal("2.50"),
        output_per_million=Decimal("10.00"),
    ),
    ("openai", "gpt-4o-mini"): PricingEntry(
        provider="openai",
        model="gpt-4o-mini",
        effective_from=date(2024, 7, 18),
        input_per_million=Decimal("0.150"),
        output_per_million=Decimal("0.600"),
    ),
    ("openai", "text-embedding-3-small"): PricingEntry(
        provider="openai",
        model="text-embedding-3-small",
        effective_from=date(2024, 1, 25),
        input_per_million=Decimal("0.020"),
    ),
    ("openai", "whisper-1"): PricingEntry(
        provider="openai",
        model="whisper-1",
        effective_from=date(2023, 3, 1),
        audio_per_minute=Decimal("0.006"),
    ),
}


def calculate_chat_cost(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> Optional[Decimal]:
    """Calculate cost for a chat completion. Returns None if pricing unknown."""
    entry = PRICING.get((provider, model))
    if entry is None or entry.input_per_million is None:
        return None

    input_cost = (Decimal(input_tokens) / Decimal("1000000")) * entry.input_per_million
    output_cost = Decimal("0")
    if entry.output_per_million is not None:
        output_cost = (Decimal(output_tokens) / Decimal("1000000")) * entry.output_per_million

    return input_cost + output_cost


def calculate_embedding_cost(
    provider: str,
    model: str,
    total_tokens: int,
) -> Optional[Decimal]:
    """Calculate cost for an embedding call. Returns None if pricing unknown."""
    entry = PRICING.get((provider, model))
    if entry is None or entry.input_per_million is None:
        return None

    return (Decimal(total_tokens) / Decimal("1000000")) * entry.input_per_million


def calculate_speech_cost(
    provider: str,
    model: str,
    audio_seconds: float,
) -> Optional[Decimal]:
    """Calculate cost for speech transcription. Returns None if pricing unknown."""
    entry = PRICING.get((provider, model))
    if entry is None or entry.audio_per_minute is None:
        return None

    minutes = Decimal(str(audio_seconds)) / Decimal("60")
    return minutes * entry.audio_per_minute
