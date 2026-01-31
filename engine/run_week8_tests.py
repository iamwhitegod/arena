#!/usr/bin/env python3
"""
Week 8: Comprehensive Test Runner

Runs all Week 8 unit and integration tests and provides summary.
"""

import unittest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Discover and run tests
def run_tests():
    """Run all Week 8 tests"""
    print("=" * 80)
    print("WEEK 8: COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print()

    # Create test loader
    loader = unittest.TestLoader()

    # Discover tests in tests/unit and tests/integration
    unit_tests = loader.discover('tests/unit', pattern='test_*.py')
    integration_tests = loader.discover('tests/integration', pattern='test_*.py')

    # Create test suite
    suite = unittest.TestSuite()
    suite.addTests(unit_tests)
    suite.addTests(integration_tests)

    # Run tests with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print()
    print(f"Tests Run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print()

    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED!")
        print()
        print("Week 8 Test Coverage:")
        print("  • Retry Module:        16 unit tests")
        print("  • Checkpoint Module:   24 unit tests")
        print("  • Parallel Processing:  9 integration tests")
        print("  • Total:               49 tests")
        print()
        print("Coverage Areas:")
        print("  ✓ API retry logic (exponential backoff, smart retry)")
        print("  ✓ Checkpoint save/load/clear operations")
        print("  ✓ Context manager auto-cleanup")
        print("  ✓ Thread-safe metrics tracking")
        print("  ✓ Parallel batch processing")
        print("  ✓ Error handling and edge cases")
        print()
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print()
        print("Please review failures above and fix issues.")
        print()
        return 1


if __name__ == '__main__':
    sys.exit(run_tests())
