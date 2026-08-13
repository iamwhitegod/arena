"""
Thought Unit Data Structure

A ThoughtUnit represents a complete rhetorical unit with:
- Premise (where the thought begins)
- Claim (the core insight/peak)
- Resolution (where the thought completes)

This is the foundational abstraction for the editorial completeness system.
It replaces "moment detection" with "thought construction".
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
import json


PRODUCTION_COMPLETENESS_THRESHOLD = 0.85
PRODUCTION_COMPONENT_THRESHOLD = 8.0
UNRESOLVED_REFERENCE_SCORE_CAP = 0.4


class RhetoricalType(Enum):
    """Types of rhetorical structures in content"""
    STORY = "story"                    # Narrative with arc (setup → event → lesson)
    ARGUMENT = "argument"              # Thesis + reasoning (sermons, debates)
    EXAMPLE = "example"                # Illustration/case study
    TEACHING = "teaching"              # How-to/tutorial (tech talks, courses)
    QUESTION_ANSWER = "qa"             # Interview format (podcasts)
    COMPARISON = "comparison"          # Product reviews, vs discussions
    INSIGHT = "insight"                # Standalone wisdom/observation


class DependencyLevel(Enum):
    """How standalone is this thought?"""
    STANDALONE = "standalone"          # Fully self-contained, no prior context needed
    NEEDS_CONTEXT = "needs_context"    # Requires prior context to understand
    UNSALVAGEABLE = "unsalvageable"    # Too fragmented to fix


@dataclass
class ThoughtUnit:
    """
    A complete rhetorical unit - the atomic building block of clips.

    Represents premise → claim → resolution structure that forms
    a complete, standalone thought.

    Attributes:
        premise_start: Where setup/context begins (seconds)
        claim_peak: Where core insight appears (seconds)
        resolution_end: Where thought completes (seconds)
        premise_text: Setup sentences
        claim_text: Core statement/insight
        resolution_text: Supporting reasoning/conclusion
        rhetorical_type: Type of rhetorical structure
        dependency_level: How standalone this thought is
        completeness_score: Overall completeness (0.0-1.0)
        premise_clarity: How clear the premise is (0.0-10.0)
        claim_strength: How strong the claim is (0.0-10.0)
        resolution_closure: How satisfying the resolution is (0.0-10.0)
        has_unresolved_refs: Whether there are dangling references
        confidence: Detection confidence (0.0-1.0)
        seed_id: Original seed that generated this

    Example:
        >>> unit = ThoughtUnit(
        ...     premise_start=54.2,
        ...     claim_peak=65.0,
        ...     resolution_end=75.8,
        ...     premise_text="I believe God can tell you who to marry.",
        ...     claim_text="But what I've seen in the Bible is that there is not one place where God picked a wife for someone.",
        ...     resolution_text="Not one place.",
        ...     rhetorical_type=RhetoricalType.ARGUMENT,
        ...     dependency_level=DependencyLevel.STANDALONE
        ... )
        >>> unit.is_complete()
        True
        >>> unit.duration
        21.6
    """

    # Temporal boundaries
    premise_start: float      # Where setup/context begins (seconds)
    claim_peak: float         # Where core insight appears (seconds)
    resolution_end: float     # Where thought completes (seconds)

    # Text content
    premise_text: str         # Setup sentences
    claim_text: str           # Core statement/insight
    resolution_text: str      # Supporting reasoning/conclusion

    # Classification
    rhetorical_type: RhetoricalType
    dependency_level: DependencyLevel

    # Quality metrics
    completeness_score: float = 0.0       # 0.0-1.0 overall completeness
    premise_clarity: float = 0.0          # 0.0-10.0 how clear the premise is
    claim_strength: float = 0.0           # 0.0-10.0 how strong the claim is
    resolution_closure: float = 0.0       # 0.0-10.0 how satisfying the resolution is

    # Validation flags
    has_unresolved_refs: bool = False     # Dangling pronouns/references
    confidence: float = 0.0               # Detection confidence (0.0-1.0)

    # Metadata
    seed_id: str = ""                     # Original seed that generated this
    _detection_metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        """Total duration of thought unit in seconds"""
        # Transcript timestamps are decimal seconds. Normalizing the result keeps
        # serialized output stable despite binary floating-point representation.
        return round(self.resolution_end - self.premise_start, 3)

    @property
    def full_text(self) -> str:
        """Complete text of the thought unit"""
        return f"{self.premise_text} {self.claim_text} {self.resolution_text}".strip()

    def has_premise(self) -> bool:
        """
        Does this unit have a clear premise?

        A premise should be at least 20 characters to be meaningful.
        """
        return bool(self.premise_text and len(self.premise_text.strip()) > 20)

    def has_claim(self) -> bool:
        """
        Does this unit have a clear claim?

        A claim should be at least 10 characters to be meaningful.
        """
        return bool(self.claim_text and len(self.claim_text.strip()) > 10)

    def has_resolution(self) -> bool:
        """
        Does this unit have a clear resolution?

        A resolution may be a short emphatic sentence, but should still contain
        enough text to distinguish it from an empty or fragmentary boundary.
        """
        return bool(self.resolution_text and len(self.resolution_text.strip()) > 10)

    def is_complete(self) -> bool:
        """
        Validate rhetorical completeness

        A thought is complete if it has:
        1. Clear premise (setup/context)
        2. Clear claim (core insight)
        3. Clear resolution (closure)
        4. No unresolved references
        5. Standalone dependency level

        Returns:
            True if thought unit is complete, False otherwise
        """
        return (
            self.has_premise() and
            self.has_claim() and
            self.has_resolution() and
            not self.has_unresolved_refs and
            self.dependency_level == DependencyLevel.STANDALONE
        )

    def meets_production_standard(self) -> bool:
        """
        Does this meet production quality bar?

        Requirements for production quality:
        - Completeness score >= 0.85
        - All three components score >= 8.0/10
        - No unresolved references
        - Standalone dependency level

        Returns:
            True if meets production standard, False otherwise
        """
        return (
            self.completeness_score >= PRODUCTION_COMPLETENESS_THRESHOLD and
            self.premise_clarity >= PRODUCTION_COMPONENT_THRESHOLD and
            self.claim_strength >= PRODUCTION_COMPONENT_THRESHOLD and
            self.resolution_closure >= PRODUCTION_COMPONENT_THRESHOLD and
            not self.has_unresolved_refs and
            self.dependency_level == DependencyLevel.STANDALONE
        )

    def calculate_completeness_score(self) -> float:
        """
        Calculate overall completeness score from component scores.

        Formula: (premise_clarity + claim_strength + resolution_closure) / 30

        Units with unresolved references are capped at 0.4 because they are not
        safe to publish without surrounding context.

        Returns:
            Completeness score between 0.0 and 1.0
        """
        raw_score = (self.premise_clarity + self.claim_strength + self.resolution_closure) / 30

        if self.has_unresolved_refs:
            return min(raw_score, UNRESOLVED_REFERENCE_SCORE_CAP)

        return raw_score

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to dictionary

        Returns:
            Dictionary representation of ThoughtUnit
        """
        return {
            'premise_start': self.premise_start,
            'claim_peak': self.claim_peak,
            'resolution_end': self.resolution_end,
            'duration': self.duration,
            'premise_text': self.premise_text,
            'claim_text': self.claim_text,
            'resolution_text': self.resolution_text,
            'full_text': self.full_text,
            'rhetorical_type': self.rhetorical_type.value,
            'dependency_level': self.dependency_level.value,
            'completeness_score': self.completeness_score,
            'premise_clarity': self.premise_clarity,
            'claim_strength': self.claim_strength,
            'resolution_closure': self.resolution_closure,
            'is_complete': self.is_complete(),
            'meets_production_standard': self.meets_production_standard(),
            'has_unresolved_refs': self.has_unresolved_refs,
            'confidence': self.confidence,
            'seed_id': self.seed_id,
            '_metadata': self._detection_metadata
        }

    def to_json(self) -> str:
        """
        Serialize to JSON string

        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ThoughtUnit':
        """
        Deserialize from dictionary

        Args:
            data: Dictionary containing ThoughtUnit data

        Returns:
            ThoughtUnit instance
        """
        return cls(
            premise_start=data['premise_start'],
            claim_peak=data['claim_peak'],
            resolution_end=data['resolution_end'],
            premise_text=data['premise_text'],
            claim_text=data['claim_text'],
            resolution_text=data['resolution_text'],
            rhetorical_type=RhetoricalType(data['rhetorical_type']),
            dependency_level=DependencyLevel(data['dependency_level']),
            completeness_score=data.get('completeness_score', 0.0),
            premise_clarity=data.get('premise_clarity', 0.0),
            claim_strength=data.get('claim_strength', 0.0),
            resolution_closure=data.get('resolution_closure', 0.0),
            has_unresolved_refs=data.get('has_unresolved_refs', False),
            confidence=data.get('confidence', 0.0),
            seed_id=data.get('seed_id', ''),
            _detection_metadata=data.get('_metadata', {})
        )

    def __repr__(self) -> str:
        """String representation for debugging"""
        return (
            f"ThoughtUnit("
            f"duration={self.duration:.1f}s, "
            f"type={self.rhetorical_type.value}, "
            f"complete={self.is_complete()}, "
            f"score={self.completeness_score:.2f}"
            f")"
        )


class ThoughtUnitError(Exception):
    """Base exception for thought unit issues"""
    pass


class IncompletePremiseError(ThoughtUnitError):
    """Raised when premise cannot be found"""
    def __init__(self, claim_position: float, message: str):
        self.claim_position = claim_position
        super().__init__(message)


class IncompleteResolutionError(ThoughtUnitError):
    """Raised when resolution cannot be found"""
    def __init__(self, claim_position: float, message: str):
        self.claim_position = claim_position
        super().__init__(message)


class AmbiguousBoundaryError(ThoughtUnitError):
    """Raised when boundary detection is uncertain"""
    def __init__(self, candidates: List[float], message: str):
        self.candidates = candidates
        super().__init__(message)


class UnresolvedReferenceError(ThoughtUnitError):
    """Raised when thought contains unresolved references"""
    def __init__(self, references: List[str], message: str):
        self.references = references
        super().__init__(message)
