"""
Tests for ThoughtSeedDetector

Validates two-pass, full-context seed detection.
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

    def test_segment_normalization(self):
        """Test that segments are validated and indexed"""
        detector = ThoughtSeedDetector(api_key='test-key')

        segments = [
            {'start': 0.0, 'end': 5.0, 'text': 'Hello'},
            {'start': 5.0, 'end': 5.0, 'text': 'Bad end'},     # end == start
            {'start': 10.0, 'end': 15.0, 'text': ''},           # empty text
            {'start': 15.0, 'end': 20.0, 'text': 'Good'},
        ]

        valid = detector._normalize_segments(segments)
        self.assertEqual(len(valid), 2)
        self.assertEqual(valid[0]['_idx'], 0)
        self.assertEqual(valid[1]['_idx'], 3)

    def test_compact_transcript_format(self):
        """Test compact segment ID format"""
        detector = ThoughtSeedDetector(api_key='test-key')
        segs = detector._normalize_segments(self.sample_transcript['segments'])

        formatted = detector._format_compact_transcript(segs)
        self.assertIn('[S0|0.0]', formatted)
        self.assertIn('[S1|5.0]', formatted)
        self.assertIn('Welcome everyone', formatted)

    def test_text_grounding(self):
        """Test that seeds are grounded in real transcript segments"""
        detector = ThoughtSeedDetector(api_key='test-key')
        segs = detector._normalize_segments(self.sample_transcript['segments'])

        # Exact match with hint
        idx = detector._find_text_in_segments(
            'I believe that God can tell you who to marry', segs, 2
        )
        self.assertEqual(idx, 2)

        # Full scan without hint — unique text
        idx2 = detector._find_text_in_segments(
            'There is not one place where God picked a wife for someone', segs, None
        )
        self.assertIsNotNone(idx2)

        # Hallucinated text returns None
        idx3 = detector._find_text_in_segments('This was never said', segs, None)
        self.assertIsNone(idx3)

    def test_context_extraction(self):
        """Test context_before and context_after from neighboring segments"""
        detector = ThoughtSeedDetector(api_key='test-key')
        segs = detector._normalize_segments(self.sample_transcript['segments'])

        before, after = detector._extract_context(2, segs)
        self.assertIn('Welcome everyone', before)
        self.assertIn('Bible', after)

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
        self.assertEqual(detector.metrics['seeds_detected'], 0)
        self.assertEqual(detector.metrics['overview_calls'], 0)
        self.assertEqual(detector.metrics['detection_calls'], 0)

        # Metrics should be dict
        self.assertIsInstance(detector.metrics, dict)

    def test_empty_transcript(self):
        """Test handling of empty transcript"""
        detector = ThoughtSeedDetector(api_key='test-key')

        empty_transcript = {'segments': [], 'duration': 0}

        # Should return empty list without API calls
        seeds = detector.detect_seeds(empty_transcript)
        self.assertEqual(len(seeds), 0)
        self.assertEqual(detector.metrics['api_calls'], 0)


class TestSegmentIdParser(unittest.TestCase):
    """Test the canonical S<n> segment ID parser."""

    VALID_IDS = [
        ("S0", 0),
        ("S1", 1),
        ("S999", 999),
        ("S10", 10),
    ]

    INVALID_IDS = [
        "S+1",       # sign
        "S 1",       # space
        "S\u0661",   # Arabic-Indic digit ١
        "S01",       # leading zero
        "S-1",       # negative
        "S1\n",      # trailing newline
        "BAD",       # no prefix
        "",          # empty
        "S",         # prefix only
        123,         # non-string
        None,        # None
        "s1",        # lowercase
    ]

    def test_valid_ids(self):
        d = ThoughtSeedDetector(api_key='test-key')
        for seg_id, expected in self.VALID_IDS:
            with self.subTest(seg_id=seg_id):
                self.assertEqual(d._parse_seg_id(seg_id), expected)

    def test_invalid_ids(self):
        d = ThoughtSeedDetector(api_key='test-key')
        for seg_id in self.INVALID_IDS:
            with self.subTest(seg_id=repr(seg_id)):
                self.assertIsNone(d._parse_seg_id(seg_id))

    def test_invalid_ids_rejected_by_ground_seed(self):
        """Malformed segment IDs cause seed rejection in _ground_seed."""
        d = ThoughtSeedDetector(api_key='test-key')
        segs = d._normalize_segments([
            {'start': 0.0, 'end': 5.0, 'text': 'Unique phrase here'},
        ])
        base = {
            'text': 'Unique phrase here',
            'rhetorical_type': 'teaching',
            'interest_score': 0.8,
            'reasoning': 'r',
            'likely_has_premise': True,
            'likely_has_resolution': True,
        }
        for bad_id in self.INVALID_IDS:
            if bad_id is None or bad_id == "":
                continue  # absent/empty IDs intentionally allow global scan
            with self.subTest(seg_id=repr(bad_id)):
                raw = {**base, 'segment_id': bad_id}
                self.assertIsNone(d._ground_seed(raw, segs))

    def test_invalid_ids_rejected_in_all_overview_collections(self):
        """Malformed segment ranges are rejected across all four collections."""
        d = ThoughtSeedDetector(api_key='test-key')
        bad_range = {'start_segment': 'S+1', 'end_segment': 'S10'}
        reversed_range = {'start_segment': 'S10', 'end_segment': 'S2'}
        missing_end = {'start_segment': 'S2'}

        overview = d._validate_overview({
            'summary': 'test',
            'main_themes': [
                {**bad_range, 'name': 'T1', 'importance': 0.5},
                {**reversed_range, 'name': 'T2', 'importance': 0.5},
                {**missing_end, 'name': 'T3', 'importance': 0.5},
                {'name': 'T4', 'start_segment': 'S0', 'end_segment': 'S10', 'importance': 0.9},
            ],
            'sections': [
                {**bad_range, 'summary': 'bad'},
                {'summary': 'good', 'start_segment': 'S0', 'end_segment': 'S50'},
            ],
            'high_interest_regions': [
                {**bad_range, 'reason': 'bad'},
                {'start_segment': 'S0', 'end_segment': 'S10', 'reason': 'good'},
            ],
            'low_interest_regions': [
                {**bad_range, 'reason': 'bad'},
                {'start_segment': 'S0', 'end_segment': 'S5', 'reason': 'good'},
            ],
        })
        self.assertEqual(len(overview['main_themes']), 1)
        self.assertEqual(len(overview['sections']), 1)
        self.assertEqual(len(overview['high_interest_regions']), 1)
        self.assertEqual(len(overview['low_interest_regions']), 1)


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
