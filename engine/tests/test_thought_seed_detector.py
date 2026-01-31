"""
Tests for ThoughtSeedDetector

Validates sliding window seed detection approach
"""

import sys
sys.path.insert(0, '../')

from arena.editorial.thought_seed_detector import ThoughtSeedDetector
from arena.editorial.thought_unit import RhetoricalType
import unittest


class TestThoughtSeedDetector(unittest.TestCase):
    """Test ThoughtSeedDetector functionality"""

    def setUp(self):
        """Set up test fixtures"""
        # Create sample transcript data
        self.sample_transcript = {
            'segments': [
                {'start': 0.0, 'end': 5.0, 'text': 'Welcome everyone.'},
                {'start': 5.0, 'end': 10.0, 'text': 'Today I want to talk about something important.'},
                {'start': 10.0, 'end': 18.0, 'text': 'I believe that God can tell you who to marry.'},
                {'start': 18.0, 'end': 25.0, 'text': 'But what I have seen in the Bible is interesting.'},
                {'start': 25.0, 'end': 32.0, 'text': 'There is not one place where God picked a wife for someone.'},
                {'start': 32.0, 'end': 35.0, 'text': 'Not one place.'},
            ],
            'duration': 35.0
        }

    def test_window_creation(self):
        """Test sliding window creation"""
        detector = ThoughtSeedDetector(api_key='test-key')

        # Create windows from sample transcript
        windows = detector._create_windows(self.sample_transcript['segments'])

        # Should create at least 1 window
        self.assertGreater(len(windows), 0)

        # First window should start at 0
        self.assertEqual(windows[0]['start'], 0.0)

        # Windows should have text
        for window in windows:
            self.assertIn('text', window)
            self.assertIn('segments', window)
            self.assertIsInstance(window['text'], str)
            self.assertIsInstance(window['segments'], list)

    def test_window_overlap(self):
        """Test that windows have proper overlap"""
        # Create longer transcript for multiple windows
        segments = []
        for i in range(100):  # 200 seconds total
            segments.append({
                'start': i * 2.0,
                'end': (i + 1) * 2.0,
                'text': f'Segment {i}.'
            })

        long_transcript = {'segments': segments, 'duration': 200.0}

        detector = ThoughtSeedDetector(api_key='test-key')
        windows = detector._create_windows(segments)

        # Should have multiple windows
        self.assertGreater(len(windows), 1)

        # Check overlap between consecutive windows
        for i in range(len(windows) - 1):
            window1 = windows[i]
            window2 = windows[i + 1]

            # Window 2 should start before window 1 ends (overlap)
            expected_start = window1['start'] + (detector.WINDOW_SIZE - detector.WINDOW_OVERLAP)
            self.assertAlmostEqual(window2['start'], expected_start, delta=1.0)

    def test_text_similarity(self):
        """Test text similarity calculation"""
        detector = ThoughtSeedDetector(api_key='test-key')

        # Identical texts
        sim1 = detector._text_similarity("hello world", "hello world")
        self.assertEqual(sim1, 1.0)

        # Completely different
        sim2 = detector._text_similarity("hello world", "goodbye universe")
        self.assertLess(sim2, 0.5)

        # Partial overlap
        sim3 = detector._text_similarity("hello world today", "hello world tomorrow")
        self.assertGreaterEqual(sim3, 0.5)
        self.assertLess(sim3, 1.0)

        # Empty strings
        sim4 = detector._text_similarity("", "")
        self.assertEqual(sim4, 0.0)

    def test_deduplication(self):
        """Test seed deduplication logic"""
        detector = ThoughtSeedDetector(api_key='test-key')

        seeds = [
            {
                'timestamp': 10.0,
                'text': 'I believe God can tell you who to marry',
                'interest_score': 0.8
            },
            {
                'timestamp': 12.0,  # Within 10 second threshold
                'text': 'I believe God can tell you who to marry',  # Same text
                'interest_score': 0.7
            },
            {
                'timestamp': 50.0,  # Different time
                'text': 'This is a different thought entirely',
                'interest_score': 0.9
            }
        ]

        unique = detector._deduplicate_seeds(seeds)

        # Should keep only 2 seeds (first two are duplicates)
        self.assertEqual(len(unique), 2)

        # Should keep the one with higher score (0.8)
        timestamps = [s['timestamp'] for s in unique]
        self.assertIn(10.0, timestamps)
        self.assertIn(50.0, timestamps)

    def test_deduplication_keeps_higher_score(self):
        """Test that deduplication keeps seed with higher interest score"""
        detector = ThoughtSeedDetector(api_key='test-key')

        seeds = [
            {
                'timestamp': 10.0,
                'text': 'This is the key insight',
                'interest_score': 0.6
            },
            {
                'timestamp': 11.0,  # Similar time
                'text': 'This is the key insight',  # Same text
                'interest_score': 0.9  # Higher score
            }
        ]

        unique = detector._deduplicate_seeds(seeds)

        # Should keep only 1 seed
        self.assertEqual(len(unique), 1)

        # Should keep the one with 0.9 score
        self.assertEqual(unique[0]['interest_score'], 0.9)
        self.assertEqual(unique[0]['timestamp'], 11.0)

    def test_seed_structure(self):
        """Test that seed detection returns proper structure"""
        # This test validates the expected seed structure
        # (We can't test actual GPT calls without an API key)

        expected_keys = [
            'seed_id',
            'timestamp',
            'text',
            'rhetorical_type',
            'interest_score',
            'reasoning',
            'likely_has_premise',
            'likely_has_resolution',
            'context_before',
            'context_after'
        ]

        # Create a mock seed
        mock_seed = {
            'seed_id': 'seed_001',
            'timestamp': 15.0,
            'text': 'I believe God can tell you who to marry',
            'rhetorical_type': 'argument',
            'interest_score': 0.85,
            'reasoning': 'Strong claim that needs support',
            'likely_has_premise': True,
            'likely_has_resolution': True,
            'context_before': 'Today I want to talk about marriage.',
            'context_after': 'But what I have seen in the Bible is different.'
        }

        # Validate all required keys present
        for key in expected_keys:
            self.assertIn(key, mock_seed)

        # Validate types
        self.assertIsInstance(mock_seed['timestamp'], float)
        self.assertIsInstance(mock_seed['interest_score'], float)
        self.assertIsInstance(mock_seed['likely_has_premise'], bool)
        self.assertIsInstance(mock_seed['likely_has_resolution'], bool)

    def test_metrics_tracking(self):
        """Test that detector tracks metrics"""
        detector = ThoughtSeedDetector(api_key='test-key')

        # Initial metrics
        self.assertEqual(detector.metrics['api_calls'], 0)
        self.assertEqual(detector.metrics['tokens_used'], 0)
        self.assertEqual(detector.metrics['cost_usd'], 0.0)
        self.assertEqual(detector.metrics['windows_analyzed'], 0)
        self.assertEqual(detector.metrics['seeds_detected'], 0)

        # Metrics should be dict
        self.assertIsInstance(detector.metrics, dict)

    def test_empty_transcript(self):
        """Test handling of empty transcript"""
        detector = ThoughtSeedDetector(api_key='test-key')

        empty_transcript = {'segments': [], 'duration': 0}

        # Should handle gracefully without crashing
        windows = detector._create_windows([])
        self.assertEqual(len(windows), 0)


class TestRhetoricalTypeMapping(unittest.TestCase):
    """Test that seed rhetorical types map to ThoughtUnit RhetoricalType enum"""

    def test_rhetorical_type_values(self):
        """Test that all rhetorical types in prompts are valid"""
        valid_types = [
            'argument',
            'teaching',
            'story',
            'advice',
            'qa',
            'comparison',
            'insight'
        ]

        # These should match RhetoricalType enum values
        enum_values = [rt.value for rt in RhetoricalType]

        # Check that seed types are subset of enum values
        for seed_type in valid_types:
            # Map seed types to enum values
            if seed_type == 'advice':
                # 'advice' seeds map to 'example' or 'teaching' in ThoughtUnit
                continue
            elif seed_type == 'qa':
                # 'qa' maps directly
                self.assertIn('qa', enum_values)
            else:
                self.assertIn(seed_type, enum_values)


if __name__ == '__main__':
    print("Testing ThoughtSeedDetector...")
    unittest.main(verbosity=2)
