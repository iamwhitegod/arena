"""
Tests for ThoughtUnit data structure

Validates the foundational data model for editorial completeness.
"""

import pytest
from arena.editorial.thought_unit import (
    ThoughtUnit,
    RhetoricalType,
    DependencyLevel,
    IncompletePremiseError,
    IncompleteResolutionError,
    AmbiguousBoundaryError,
    UnresolvedReferenceError
)


class TestThoughtUnitCreation:
    """Test basic ThoughtUnit creation and properties"""

    def test_create_basic_thought_unit(self):
        """Test creating a basic ThoughtUnit"""
        unit = ThoughtUnit(
            premise_start=10.0,
            claim_peak=25.0,
            resolution_end=45.0,
            premise_text="This is the premise that sets up the thought.",
            claim_text="This is the core claim or insight.",
            resolution_text="This is the resolution that completes the thought.",
            rhetorical_type=RhetoricalType.ARGUMENT,
            dependency_level=DependencyLevel.STANDALONE
        )

        assert unit.premise_start == 10.0
        assert unit.claim_peak == 25.0
        assert unit.resolution_end == 45.0
        assert unit.duration == 35.0
        assert unit.rhetorical_type == RhetoricalType.ARGUMENT
        assert unit.dependency_level == DependencyLevel.STANDALONE

    def test_full_text_property(self):
        """Test that full_text combines all components"""
        unit = ThoughtUnit(
            premise_start=0.0,
            claim_peak=10.0,
            resolution_end=20.0,
            premise_text="Premise here.",
            claim_text="Claim here.",
            resolution_text="Resolution here.",
            rhetorical_type=RhetoricalType.ARGUMENT,
            dependency_level=DependencyLevel.STANDALONE
        )

        assert unit.full_text == "Premise here. Claim here. Resolution here."

    def test_duration_calculation(self):
        """Test duration is calculated correctly"""
        unit = ThoughtUnit(
            premise_start=100.0,
            claim_peak=150.0,
            resolution_end=220.0,
            premise_text="Setup",
            claim_text="Core",
            resolution_text="Conclusion",
            rhetorical_type=RhetoricalType.TEACHING,
            dependency_level=DependencyLevel.STANDALONE
        )

        assert unit.duration == 120.0


class TestCompletenessValidation:
    """Test completeness validation logic"""

    def test_complete_thought_unit(self):
        """Test that a complete thought unit passes validation"""
        unit = ThoughtUnit(
            premise_start=54.2,
            claim_peak=65.0,
            resolution_end=75.8,
            premise_text="I believe God can tell you who to marry, because many people say so.",
            claim_text="But what I've seen in the Bible is that there is not one place where God picked a wife for someone.",
            resolution_text="Not one place in scripture.",
            rhetorical_type=RhetoricalType.ARGUMENT,
            dependency_level=DependencyLevel.STANDALONE,
            has_unresolved_refs=False
        )

        assert unit.has_premise() == True
        assert unit.has_claim() == True
        assert unit.has_resolution() == True
        assert unit.is_complete() == True

    def test_missing_premise(self):
        """Test that missing premise fails validation"""
        unit = ThoughtUnit(
            premise_start=0.0,
            claim_peak=10.0,
            resolution_end=20.0,
            premise_text="",  # Empty premise
            claim_text="This is a claim without setup.",
            resolution_text="And this is the resolution.",
            rhetorical_type=RhetoricalType.ARGUMENT,
            dependency_level=DependencyLevel.STANDALONE
        )

        assert unit.has_premise() == False
        assert unit.is_complete() == False

    def test_missing_claim(self):
        """Test that missing claim fails validation"""
        unit = ThoughtUnit(
            premise_start=0.0,
            claim_peak=10.0,
            resolution_end=20.0,
            premise_text="This is a premise that sets up.",
            claim_text="",  # Empty claim
            resolution_text="But there's no core insight.",
            rhetorical_type=RhetoricalType.ARGUMENT,
            dependency_level=DependencyLevel.STANDALONE
        )

        assert unit.has_claim() == False
        assert unit.is_complete() == False

    def test_missing_resolution(self):
        """Test that missing resolution fails validation"""
        unit = ThoughtUnit(
            premise_start=0.0,
            claim_peak=10.0,
            resolution_end=20.0,
            premise_text="This is a premise that sets up.",
            claim_text="And this is the claim.",
            resolution_text="",  # Empty resolution
            rhetorical_type=RhetoricalType.ARGUMENT,
            dependency_level=DependencyLevel.STANDALONE
        )

        assert unit.has_resolution() == False
        assert unit.is_complete() == False

    def test_unresolved_references_fail(self):
        """Test that unresolved references cause incompleteness"""
        unit = ThoughtUnit(
            premise_start=0.0,
            claim_peak=10.0,
            resolution_end=20.0,
            premise_text="Setup is here with context.",
            claim_text="That's why this is important.",  # Unresolved "that"
            resolution_text="And that's the conclusion.",
            rhetorical_type=RhetoricalType.ARGUMENT,
            dependency_level=DependencyLevel.STANDALONE,
            has_unresolved_refs=True  # Flagged as having unresolved refs
        )

        assert unit.is_complete() == False

    def test_needs_context_fails_completeness(self):
        """Test that NEEDS_CONTEXT dependency fails completeness"""
        unit = ThoughtUnit(
            premise_start=0.0,
            claim_peak=10.0,
            resolution_end=20.0,
            premise_text="This continues from before.",
            claim_text="So the point is clear.",
            resolution_text="That's why it matters.",
            rhetorical_type=RhetoricalType.ARGUMENT,
            dependency_level=DependencyLevel.NEEDS_CONTEXT,  # Not standalone
            has_unresolved_refs=False
        )

        assert unit.is_complete() == False


class TestProductionQuality:
    """Test production quality standards (90%+ bar)"""

    def test_meets_production_standard(self):
        """Test that high-quality thought unit meets production standard"""
        unit = ThoughtUnit(
            premise_start=0.0,
            claim_peak=10.0,
            resolution_end=20.0,
            premise_text="Clear premise",
            claim_text="Strong claim",
            resolution_text="Satisfying resolution",
            rhetorical_type=RhetoricalType.ARGUMENT,
            dependency_level=DependencyLevel.STANDALONE,
            completeness_score=0.90,
            premise_clarity=9.0,
            claim_strength=8.5,
            resolution_closure=8.0,
            has_unresolved_refs=False
        )

        assert unit.meets_production_standard() == True

    def test_low_completeness_fails_production(self):
        """Test that low completeness score fails production standard"""
        unit = ThoughtUnit(
            premise_start=0.0,
            claim_peak=10.0,
            resolution_end=20.0,
            premise_text="Premise",
            claim_text="Claim",
            resolution_text="Resolution",
            rhetorical_type=RhetoricalType.ARGUMENT,
            dependency_level=DependencyLevel.STANDALONE,
            completeness_score=0.75,  # Below 0.85
            premise_clarity=8.0,
            claim_strength=8.0,
            resolution_closure=8.0,
            has_unresolved_refs=False
        )

        assert unit.meets_production_standard() == False

    def test_low_component_score_fails_production(self):
        """Test that low component scores fail production standard"""
        unit = ThoughtUnit(
            premise_start=0.0,
            claim_peak=10.0,
            resolution_end=20.0,
            premise_text="Premise",
            claim_text="Claim",
            resolution_text="Resolution",
            rhetorical_type=RhetoricalType.ARGUMENT,
            dependency_level=DependencyLevel.STANDALONE,
            completeness_score=0.90,
            premise_clarity=7.0,  # Below 8.0
            claim_strength=8.5,
            resolution_closure=8.0,
            has_unresolved_refs=False
        )

        assert unit.meets_production_standard() == False

    def test_unresolved_refs_fail_production(self):
        """Test that unresolved refs fail production standard"""
        unit = ThoughtUnit(
            premise_start=0.0,
            claim_peak=10.0,
            resolution_end=20.0,
            premise_text="Premise",
            claim_text="Claim",
            resolution_text="Resolution",
            rhetorical_type=RhetoricalType.ARGUMENT,
            dependency_level=DependencyLevel.STANDALONE,
            completeness_score=0.90,
            premise_clarity=9.0,
            claim_strength=8.5,
            resolution_closure=8.0,
            has_unresolved_refs=True  # Has unresolved refs
        )

        assert unit.meets_production_standard() == False


class TestCompletenessScoreCalculation:
    """Test completeness score calculation"""

    def test_calculate_perfect_score(self):
        """Test perfect score calculation"""
        unit = ThoughtUnit(
            premise_start=0.0,
            claim_peak=10.0,
            resolution_end=20.0,
            premise_text="Premise",
            claim_text="Claim",
            resolution_text="Resolution",
            rhetorical_type=RhetoricalType.ARGUMENT,
            dependency_level=DependencyLevel.STANDALONE,
            premise_clarity=10.0,
            claim_strength=10.0,
            resolution_closure=10.0,
            has_unresolved_refs=False
        )

        score = unit.calculate_completeness_score()
        assert score == 1.0  # (10 + 10 + 10) / 30 = 1.0

    def test_calculate_medium_score(self):
        """Test medium score calculation"""
        unit = ThoughtUnit(
            premise_start=0.0,
            claim_peak=10.0,
            resolution_end=20.0,
            premise_text="Premise",
            claim_text="Claim",
            resolution_text="Resolution",
            rhetorical_type=RhetoricalType.ARGUMENT,
            dependency_level=DependencyLevel.STANDALONE,
            premise_clarity=7.0,
            claim_strength=8.0,
            resolution_closure=6.0,
            has_unresolved_refs=False
        )

        score = unit.calculate_completeness_score()
        assert score == 0.7  # (7 + 8 + 6) / 30 = 0.7

    def test_unresolved_refs_cap_score(self):
        """Test that unresolved refs cap score at 0.4"""
        unit = ThoughtUnit(
            premise_start=0.0,
            claim_peak=10.0,
            resolution_end=20.0,
            premise_text="Premise",
            claim_text="Claim",
            resolution_text="Resolution",
            rhetorical_type=RhetoricalType.ARGUMENT,
            dependency_level=DependencyLevel.STANDALONE,
            premise_clarity=10.0,
            claim_strength=10.0,
            resolution_closure=10.0,
            has_unresolved_refs=True  # Has unresolved refs
        )

        score = unit.calculate_completeness_score()
        assert score == 0.4  # Capped at 0.4


class TestSerialization:
    """Test serialization and deserialization"""

    def test_to_dict(self):
        """Test serialization to dictionary"""
        unit = ThoughtUnit(
            premise_start=54.2,
            claim_peak=65.0,
            resolution_end=75.8,
            premise_text="Premise text",
            claim_text="Claim text",
            resolution_text="Resolution text",
            rhetorical_type=RhetoricalType.ARGUMENT,
            dependency_level=DependencyLevel.STANDALONE,
            completeness_score=0.85,
            seed_id="seed_001"
        )

        data = unit.to_dict()

        assert data['premise_start'] == 54.2
        assert data['claim_peak'] == 65.0
        assert data['resolution_end'] == 75.8
        assert data['duration'] == 21.6
        assert data['rhetorical_type'] == 'argument'
        assert data['dependency_level'] == 'standalone'
        assert data['completeness_score'] == 0.85
        assert data['seed_id'] == 'seed_001'

    def test_from_dict(self):
        """Test deserialization from dictionary"""
        data = {
            'premise_start': 54.2,
            'claim_peak': 65.0,
            'resolution_end': 75.8,
            'premise_text': 'Premise',
            'claim_text': 'Claim',
            'resolution_text': 'Resolution',
            'rhetorical_type': 'argument',
            'dependency_level': 'standalone',
            'completeness_score': 0.85,
            'seed_id': 'seed_001'
        }

        unit = ThoughtUnit.from_dict(data)

        assert unit.premise_start == 54.2
        assert unit.claim_peak == 65.0
        assert unit.resolution_end == 75.8
        assert unit.rhetorical_type == RhetoricalType.ARGUMENT
        assert unit.dependency_level == DependencyLevel.STANDALONE
        assert unit.completeness_score == 0.85
        assert unit.seed_id == 'seed_001'

    def test_roundtrip_serialization(self):
        """Test that to_dict/from_dict is lossless"""
        original = ThoughtUnit(
            premise_start=100.0,
            claim_peak=150.0,
            resolution_end=200.0,
            premise_text="Original premise",
            claim_text="Original claim",
            resolution_text="Original resolution",
            rhetorical_type=RhetoricalType.TEACHING,
            dependency_level=DependencyLevel.STANDALONE,
            completeness_score=0.90,
            premise_clarity=8.5,
            claim_strength=9.0,
            resolution_closure=8.0,
            has_unresolved_refs=False,
            confidence=0.95,
            seed_id="seed_123"
        )

        data = original.to_dict()
        restored = ThoughtUnit.from_dict(data)

        assert restored.premise_start == original.premise_start
        assert restored.claim_peak == original.claim_peak
        assert restored.resolution_end == original.resolution_end
        assert restored.premise_text == original.premise_text
        assert restored.claim_text == original.claim_text
        assert restored.resolution_text == original.resolution_text
        assert restored.rhetorical_type == original.rhetorical_type
        assert restored.dependency_level == original.dependency_level
        assert restored.completeness_score == original.completeness_score
        assert restored.seed_id == original.seed_id


class TestRhetoricalTypes:
    """Test different rhetorical types"""

    def test_all_rhetorical_types(self):
        """Test that all rhetorical types can be used"""
        types = [
            RhetoricalType.STORY,
            RhetoricalType.ARGUMENT,
            RhetoricalType.EXAMPLE,
            RhetoricalType.TEACHING,
            RhetoricalType.QUESTION_ANSWER,
            RhetoricalType.COMPARISON,
            RhetoricalType.INSIGHT
        ]

        for rtype in types:
            unit = ThoughtUnit(
                premise_start=0.0,
                claim_peak=10.0,
                resolution_end=20.0,
                premise_text="Premise for " + rtype.value,
                claim_text="Claim for " + rtype.value,
                resolution_text="Resolution for " + rtype.value,
                rhetorical_type=rtype,
                dependency_level=DependencyLevel.STANDALONE
            )

            assert unit.rhetorical_type == rtype


class TestExceptions:
    """Test custom exceptions"""

    def test_incomplete_premise_error(self):
        """Test IncompletePremiseError"""
        with pytest.raises(IncompletePremiseError) as exc_info:
            raise IncompletePremiseError(
                claim_position=65.0,
                message="Could not find premise for claim at 65.0s"
            )

        assert exc_info.value.claim_position == 65.0

    def test_incomplete_resolution_error(self):
        """Test IncompleteResolutionError"""
        with pytest.raises(IncompleteResolutionError) as exc_info:
            raise IncompleteResolutionError(
                claim_position=65.0,
                message="Could not find resolution for claim at 65.0s"
            )

        assert exc_info.value.claim_position == 65.0

    def test_ambiguous_boundary_error(self):
        """Test AmbiguousBoundaryError"""
        candidates = [10.5, 12.3, 15.7]
        with pytest.raises(AmbiguousBoundaryError) as exc_info:
            raise AmbiguousBoundaryError(
                candidates=candidates,
                message="Multiple possible boundaries found"
            )

        assert exc_info.value.candidates == candidates

    def test_unresolved_reference_error(self):
        """Test UnresolvedReferenceError"""
        refs = ["that", "this", "it"]
        with pytest.raises(UnresolvedReferenceError) as exc_info:
            raise UnresolvedReferenceError(
                references=refs,
                message="Found unresolved references"
            )

        assert exc_info.value.references == refs


class TestUserClipExamples:
    """Test using actual user clip examples from test_007"""

    def test_user_clip_02_standalone(self):
        """Test Clip 2 from test_007 - perfect standalone"""
        unit = ThoughtUnit(
            premise_start=54.2,
            claim_peak=65.0,
            resolution_end=75.8,
            premise_text="I believe, I personally believe that God can tell you who to marry. The reason why I believe it is because a lot of people said so.",
            claim_text="But what I've seen in the Bible is that there is not one place where God picked a wife for someone.",
            resolution_text="Not one place.",
            rhetorical_type=RhetoricalType.ARGUMENT,
            dependency_level=DependencyLevel.STANDALONE,
            has_unresolved_refs=False
        )

        assert unit.duration == 21.6
        assert unit.is_complete() == True
        assert unit.dependency_level == DependencyLevel.STANDALONE

    def test_user_clip_03_long_complete(self):
        """Test Clip 3 from test_007 - long complete thought (139s)"""
        unit = ThoughtUnit(
            premise_start=78.3,
            claim_peak=150.0,  # Approximate middle
            resolution_end=217.6,
            premise_text="God does not describe how to pick a wife. He prescribes how to pick a wife.",
            claim_text="[Biblical examples: Deuteronomy, Moses, Boaz, Jacob, David...]",
            resolution_text="I'm saying that the Bible describes how people picked. The Bible doesn't show that God picked for somebody.",
            rhetorical_type=RhetoricalType.ARGUMENT,
            dependency_level=DependencyLevel.STANDALONE,
            has_unresolved_refs=False
        )

        assert unit.duration == 139.3
        assert unit.is_complete() == True
        # This proves variable length works - 139s is acceptable

    def test_user_clip_01_incomplete_but_interesting(self):
        """Test Clip 1 from test_007 - lacks completeness but engaging"""
        unit = ThoughtUnit(
            premise_start=18.0,
            claim_peak=28.0,
            resolution_end=38.7,
            premise_text="",  # Missing premise
            claim_text="The anxiety of being single is nothing compared to the regret of being in the wrong marriage.",
            resolution_text="Many single people want to get married. Many married people want to be single.",
            rhetorical_type=RhetoricalType.INSIGHT,
            dependency_level=DependencyLevel.STANDALONE,
            has_unresolved_refs=False
        )

        assert unit.duration == 20.7
        assert unit.has_premise() == False  # Missing premise
        assert unit.is_complete() == False  # Not complete
        # But user kept it anyway - proves tolerance for high-interest clips
