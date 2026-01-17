#!/usr/bin/env python3
"""
Validate Refinement Plan Implementation

Checks that all architectural changes from REFINEMENT_PLAN.md are properly implemented:
- Problem 1: Layer 2/3 separation
- Problem 2: Hard stops
- Problem 3: Concrete scoring anchors
- Problem 4: Model parameter
- Refinement 1: Editorial contracts
- Refinement 2: Rejection reasons
- Refinement 3: Configurable scoring
- Refinement 4: No changes metric
"""

import sys
import re
from pathlib import Path
from enum import Enum

sys.path.insert(0, str(Path(__file__).parent))

# Import the modules to validate
from arena.editorial.layer2_boundary_analyzer import ThoughtBoundaryAnalyzer
from arena.editorial.layer3_context_refiner import StandaloneContextRefiner, RejectionReason
from arena.editorial.adapter import FourLayerAdapter


def check_layer2_changes():
    """Verify Layer 2 architectural changes"""
    print("\n[1/8] Checking Layer 2 Editorial Contract...")

    # Check docstring contains editorial contract
    docstring = ThoughtBoundaryAnalyzer.__doc__
    if "EDITORIAL CONTRACT" in docstring and "NARRATIVE STRUCTURE" in docstring:
        print("  ✓ Editorial contract documented")
    else:
        print("  ✗ Editorial contract missing")
        return False

    # Check model parameter exists
    import inspect
    sig = inspect.signature(ThoughtBoundaryAnalyzer.__init__)
    if 'model' in sig.parameters:
        print("  ✓ Model parameter added")
    else:
        print("  ✗ Model parameter missing")
        return False

    # Check prompt has hard constraints
    analyzer = ThoughtBoundaryAnalyzer(api_key="test", model="gpt-4o")
    prompt = analyzer._create_prompt(
        moment={'core_idea': 'test', 'why_interesting': 'test', 'content_type': 'test'},
        context_transcript="test",
        rough_start=0.0,
        rough_end=10.0
    )

    if "NEVER expand more than 30 seconds" in prompt:
        print("  ✓ Hard constraints (30s) in prompt")
    else:
        print("  ✗ Hard constraints missing")
        return False

    if "DO NOT WORRY ABOUT" in prompt and "Layer 3's job" in prompt:
        print("  ✓ Layer 3 separation documented in prompt")
    else:
        print("  ✗ Layer 3 separation missing from prompt")
        return False

    return True


def check_layer3_changes():
    """Verify Layer 3 architectural changes"""
    print("\n[2/8] Checking Layer 3 Editorial Contract...")

    # Check docstring contains editorial contract
    docstring = StandaloneContextRefiner.__doc__
    if "EDITORIAL CONTRACT" in docstring and "CONTEXTUAL INDEPENDENCE" in docstring:
        print("  ✓ Editorial contract documented")
    else:
        print("  ✗ Editorial contract missing")
        return False

    # Check rejection reason enum exists
    print("\n[3/8] Checking Rejection Reason Enum...")
    try:
        reasons = [r.value for r in RejectionReason]
        expected_reasons = [
            'missing_premise',
            'dangling_reference',
            'incomplete_resolution',
            'topic_drift',
            'duration_constraint',
            'structural_issue'
        ]

        if all(r in reasons for r in expected_reasons):
            print(f"  ✓ RejectionReason enum complete ({len(reasons)} reasons)")
        else:
            print("  ✗ RejectionReason enum incomplete")
            return False
    except Exception as e:
        print(f"  ✗ RejectionReason enum error: {e}")
        return False

    # Check metrics tracking
    print("\n[4/8] Checking 'No Changes Needed' Metric...")
    refiner = StandaloneContextRefiner(api_key="test")

    if 'no_changes_needed' in refiner.metrics:
        print("  ✓ no_changes_needed metric exists")
    else:
        print("  ✗ no_changes_needed metric missing")
        return False

    if 'boundary_quality_rate' in refiner.metrics:
        print("  ✓ boundary_quality_rate metric exists")
    else:
        print("  ✗ boundary_quality_rate metric missing")
        return False

    # Check validation method exists
    print("\n[5/8] Checking Hard Boundary Validation...")
    if hasattr(refiner, '_validate_refinement_bounds'):
        print("  ✓ _validate_refinement_bounds() method exists")

        # Test the validation logic
        valid = refiner._validate_refinement_bounds(100.0, 200.0, 95.0, 205.0)  # 5s and 5s adjustments = OK
        invalid = refiner._validate_refinement_bounds(100.0, 200.0, 80.0, 220.0)  # 20s adjustments = BAD

        if valid and not invalid:
            print("  ✓ Validation logic correct (15s limit enforced)")
        else:
            print("  ✗ Validation logic incorrect")
            return False
    else:
        print("  ✗ _validate_refinement_bounds() method missing")
        return False

    # Check concrete scoring anchors in prompt
    print("\n[6/8] Checking Concrete Scoring Anchors...")
    refiner_instance = StandaloneContextRefiner(api_key="test")
    prompt = refiner_instance._create_prompt(
        clip_text="test",
        start=0.0,
        end=10.0,
        thought={
            'moment_id': 'test',
            'thought_summary': 'test',
            'complete_thought': {
                'original_moment': {
                    'core_idea': 'test idea'
                }
            }
        }
    )

    if "0.9-1.0: PERFECT STANDALONE" in prompt and "Example:" in prompt:
        print("  ✓ Concrete scoring examples in prompt")
    else:
        print("  ✗ Concrete scoring examples missing")
        return False

    if "±15 seconds" in prompt or "±2 sentences" in prompt:
        print("  ✓ Hard constraints (15s) in prompt")
    else:
        print("  ✗ Hard constraints missing from prompt")
        return False

    return True


def check_adapter_changes():
    """Verify FourLayerAdapter changes"""
    print("\n[7/8] Checking Configurable Scoring Weights...")

    # Check constructor signature
    import inspect
    sig = inspect.signature(FourLayerAdapter.__init__)

    if 'score_weights' in sig.parameters:
        print("  ✓ score_weights parameter added")
    else:
        print("  ✗ score_weights parameter missing")
        return False

    # Check default weights exist
    adapter = FourLayerAdapter(api_key="test", model="gpt-4o")

    if hasattr(adapter, 'score_weights'):
        print(f"  ✓ score_weights attribute exists: {adapter.score_weights}")

        if 'interest' in adapter.score_weights and 'standalone' in adapter.score_weights:
            print("  ✓ Default weights configured (interest + standalone)")
        else:
            print("  ✗ Default weights incomplete")
            return False
    else:
        print("  ✗ score_weights attribute missing")
        return False

    return True


def check_cli_integration():
    """Verify CLI integration"""
    print("\n[8/8] Checking CLI Integration...")

    # Read arena_process.py to check for --editorial-model flag
    arena_process_path = Path(__file__).parent / "arena_process.py"

    if not arena_process_path.exists():
        print("  ✗ arena_process.py not found")
        return False

    content = arena_process_path.read_text()

    if "--editorial-model" in content:
        print("  ✓ --editorial-model CLI flag added")
    else:
        print("  ✗ --editorial-model CLI flag missing")
        return False

    if "editorial_model" in content and "FourLayerAdapter" in content:
        print("  ✓ editorial_model parameter passed to FourLayerAdapter")
    else:
        print("  ✗ editorial_model parameter integration incomplete")
        return False

    return True


def main():
    """Run all validation checks"""
    print("=" * 70)
    print("🔍 VALIDATING REFINEMENT PLAN IMPLEMENTATION")
    print("=" * 70)

    checks = [
        ("Layer 2 Changes", check_layer2_changes),
        ("Layer 3 Changes", check_layer3_changes),
        ("FourLayerAdapter Changes", check_adapter_changes),
        ("CLI Integration", check_cli_integration),
    ]

    results = []

    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n  ⚠️  Exception during {name}: {e}")
            results.append((name, False))

    # Print summary
    print("\n" + "=" * 70)
    print("📊 VALIDATION SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {name}")

    print("\n" + "=" * 70)

    if passed == total:
        print(f"✅ ALL CHECKS PASSED ({passed}/{total})")
        print("\n🎉 Refinement Plan Implementation Complete!")
        print("\nNext steps:")
        print("  1. Test on real video: python3 arena_process.py video.mp4 --use-4layer")
        print("  2. Export layers: Add --export-editorial-layers to see intermediate results")
        print("  3. Test gpt-4o-mini: Add --editorial-model gpt-4o-mini for cost savings")
        return 0
    else:
        print(f"❌ {total - passed} CHECK(S) FAILED ({passed}/{total} passed)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
