#!/usr/bin/env python3
"""
Unit Tests for arena.editorial.checkpoint

Tests the progress checkpointing system.
"""

import unittest
import tempfile
import shutil
import json
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from arena.editorial.checkpoint import CheckpointManager, CheckpointContext


class TestCheckpointBasics(unittest.TestCase):
    """Test basic checkpoint operations"""

    def setUp(self):
        """Create temporary checkpoint directory"""
        self.temp_dir = tempfile.mkdtemp(prefix="test_checkpoint_")
        self.manager = CheckpointManager(checkpoint_dir=self.temp_dir, enabled=True)

    def tearDown(self):
        """Clean up temporary directory"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_save_and_load_checkpoint(self):
        """Test basic save and load"""
        job_id = "test_job_123"
        stage = "test_stage"
        test_data = {"key": "value", "count": 42}

        # Save checkpoint
        success = self.manager.save_checkpoint(job_id, stage, test_data)
        self.assertTrue(success, "Save should succeed")

        # Load checkpoint
        loaded_data = self.manager.load_checkpoint(job_id, stage)
        self.assertIsNotNone(loaded_data, "Load should return data")
        self.assertEqual(loaded_data, test_data, "Loaded data should match saved data")

    def test_load_nonexistent_checkpoint(self):
        """Test loading a checkpoint that doesn't exist"""
        result = self.manager.load_checkpoint("nonexistent_job", "nonexistent_stage")
        self.assertIsNone(result, "Should return None for nonexistent checkpoint")

    def test_save_with_metadata(self):
        """Test saving checkpoint with metadata"""
        job_id = "metadata_test"
        stage = "stage1"
        data = {"test": "data"}
        metadata = {"cost": 0.05, "tokens": 1000}

        success = self.manager.save_checkpoint(job_id, stage, data, metadata=metadata)
        self.assertTrue(success)

        # Get checkpoint info to verify metadata
        info = self.manager.get_checkpoint_info(job_id, stage)
        self.assertIsNotNone(info)
        self.assertIn("timestamp", info)
        self.assertIn("file_size", info)

    def test_multiple_stages(self):
        """Test saving multiple stages for same job"""
        job_id = "multi_stage_job"

        data1 = {"stage": 1}
        data2 = {"stage": 2}
        data3 = {"stage": 3}

        self.manager.save_checkpoint(job_id, "stage1", data1)
        self.manager.save_checkpoint(job_id, "stage2", data2)
        self.manager.save_checkpoint(job_id, "stage3", data3)

        # List checkpoints
        checkpoints = self.manager.list_checkpoints(job_id)
        self.assertEqual(len(checkpoints), 3, "Should have 3 checkpoints")
        self.assertIn("stage1", checkpoints)
        self.assertIn("stage2", checkpoints)
        self.assertIn("stage3", checkpoints)

        # Load each stage
        self.assertEqual(self.manager.load_checkpoint(job_id, "stage1"), data1)
        self.assertEqual(self.manager.load_checkpoint(job_id, "stage2"), data2)
        self.assertEqual(self.manager.load_checkpoint(job_id, "stage3"), data3)


class TestJobIDGeneration(unittest.TestCase):
    """Test job ID generation"""

    def test_generate_job_id(self):
        """Test job ID generation from transcript"""
        transcript = {"text": "This is a test transcript"}
        job_id = CheckpointManager.generate_job_id(transcript)

        self.assertIsNotNone(job_id)
        self.assertIsInstance(job_id, str)
        self.assertEqual(len(job_id), 12, "Job ID should be 12 characters")

    def test_job_id_consistency(self):
        """Test that same transcript generates same job ID"""
        transcript = {"text": "Consistent transcript"}

        job_id1 = CheckpointManager.generate_job_id(transcript)
        job_id2 = CheckpointManager.generate_job_id(transcript)

        self.assertEqual(job_id1, job_id2, "Same transcript should generate same job ID")

    def test_job_id_uses_complete_transcript(self):
        shared_intro = "same intro " * 60
        transcript1 = {"text": shared_intro + "first ending", "duration": 10.0}
        transcript2 = {"text": shared_intro + "second ending", "duration": 10.0}

        self.assertNotEqual(
            CheckpointManager.generate_job_id(transcript1),
            CheckpointManager.generate_job_id(transcript2),
        )

    def test_different_transcripts_different_ids(self):
        """Test that different transcripts generate different job IDs"""
        transcript1 = {"text": "First transcript"}
        transcript2 = {"text": "Second transcript"}

        job_id1 = CheckpointManager.generate_job_id(transcript1)
        job_id2 = CheckpointManager.generate_job_id(transcript2)

        self.assertNotEqual(job_id1, job_id2, "Different transcripts should generate different job IDs")

    def test_empty_transcript(self):
        """Test job ID generation with empty transcript"""
        transcript = {"text": ""}
        job_id = CheckpointManager.generate_job_id(transcript)

        self.assertIsNotNone(job_id)
        self.assertEqual(len(job_id), 12)


class TestCheckpointManagement(unittest.TestCase):
    """Test checkpoint listing, clearing, and info"""

    def setUp(self):
        """Create temporary checkpoint directory"""
        self.temp_dir = tempfile.mkdtemp(prefix="test_checkpoint_")
        self.manager = CheckpointManager(checkpoint_dir=self.temp_dir, enabled=True)

    def tearDown(self):
        """Clean up temporary directory"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_list_checkpoints(self):
        """Test listing checkpoints for a job"""
        job_id = "list_test"

        # Initially empty
        checkpoints = self.manager.list_checkpoints(job_id)
        self.assertEqual(len(checkpoints), 0, "Should start with no checkpoints")

        # Add some checkpoints
        self.manager.save_checkpoint(job_id, "stage1", {"data": 1})
        self.manager.save_checkpoint(job_id, "stage2", {"data": 2})

        checkpoints = self.manager.list_checkpoints(job_id)
        self.assertEqual(len(checkpoints), 2)

    def test_clear_checkpoints(self):
        """Test clearing all checkpoints for a job"""
        job_id = "clear_test"

        # Create checkpoints
        self.manager.save_checkpoint(job_id, "stage1", {"data": 1})
        self.manager.save_checkpoint(job_id, "stage2", {"data": 2})
        self.manager.save_checkpoint(job_id, "stage3", {"data": 3})

        # Clear them
        removed = self.manager.clear_checkpoints(job_id)
        self.assertEqual(removed, 3, "Should remove 3 checkpoints")

        # Verify they're gone
        checkpoints = self.manager.list_checkpoints(job_id)
        self.assertEqual(len(checkpoints), 0, "Should have no checkpoints after clear")

    def test_clear_nonexistent_job(self):
        """Test clearing checkpoints for job that doesn't exist"""
        removed = self.manager.clear_checkpoints("nonexistent_job")
        self.assertEqual(removed, 0, "Should return 0 for nonexistent job")

    def test_get_checkpoint_info(self):
        """Test getting checkpoint metadata"""
        job_id = "info_test"
        stage = "test_stage"
        data = {"test": "data"}

        self.manager.save_checkpoint(job_id, stage, data)

        info = self.manager.get_checkpoint_info(job_id, stage)
        self.assertIsNotNone(info)
        self.assertIn("file_size", info)
        self.assertIn("timestamp", info)
        self.assertIn("job_id", info)
        self.assertIn("stage", info)
        self.assertGreater(info["file_size"], 0, "File size should be > 0")

    def test_get_info_nonexistent_checkpoint(self):
        """Test getting info for checkpoint that doesn't exist"""
        info = self.manager.get_checkpoint_info("nonexistent", "nonexistent")
        self.assertIsNone(info, "Should return None for nonexistent checkpoint")


class TestContextManager(unittest.TestCase):
    """Test CheckpointContext context manager"""

    def setUp(self):
        """Create temporary checkpoint directory"""
        self.temp_dir = tempfile.mkdtemp(prefix="test_checkpoint_")
        self.manager = CheckpointManager(checkpoint_dir=self.temp_dir, enabled=True)

    def tearDown(self):
        """Clean up temporary directory"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_context_manager_basic(self):
        """Test basic context manager usage"""
        job_id = "context_test"

        with CheckpointContext(self.manager, job_id) as ctx:
            ctx.save("stage1", {"data": 1})
            ctx.save("stage2", {"data": 2})

            # Load within context
            loaded = ctx.load("stage1")
            self.assertEqual(loaded, {"data": 1})

    def test_context_manager_auto_cleanup(self):
        """Test auto-cleanup on success"""
        job_id = "cleanup_test"

        with CheckpointContext(self.manager, job_id, auto_cleanup=True) as ctx:
            ctx.save("stage1", {"data": 1})
            ctx.save("stage2", {"data": 2})
            ctx.mark_success()  # Mark as successful

        # Checkpoints should be cleaned up
        checkpoints = self.manager.list_checkpoints(job_id)
        self.assertEqual(len(checkpoints), 0, "Checkpoints should be cleaned up on success")

    def test_context_manager_no_cleanup_on_failure(self):
        """Test checkpoints are kept on failure"""
        job_id = "failure_test"

        with CheckpointContext(self.manager, job_id, auto_cleanup=True) as ctx:
            ctx.save("stage1", {"data": 1})
            # Don't mark as success

        # Checkpoints should still exist
        checkpoints = self.manager.list_checkpoints(job_id)
        self.assertEqual(len(checkpoints), 1, "Checkpoints should be kept on failure")

    def test_context_manager_exception_handling(self):
        """Test context manager handles exceptions properly"""
        job_id = "exception_test"

        try:
            with CheckpointContext(self.manager, job_id, auto_cleanup=True) as ctx:
                ctx.save("stage1", {"data": 1})
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Checkpoints should still exist after exception
        checkpoints = self.manager.list_checkpoints(job_id)
        self.assertEqual(len(checkpoints), 1, "Checkpoints should be kept after exception")


class TestDisabledCheckpoints(unittest.TestCase):
    """Test checkpoint manager when disabled"""

    def setUp(self):
        """Create disabled checkpoint manager"""
        self.temp_dir = tempfile.mkdtemp(prefix="test_checkpoint_")
        self.manager = CheckpointManager(checkpoint_dir=self.temp_dir, enabled=False)

    def tearDown(self):
        """Clean up temporary directory"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_save_when_disabled(self):
        """Test that save returns False and doesn't create files when disabled"""
        job_id = "disabled_test"
        stage = "test_stage"
        data = {"test": "data"}

        success = self.manager.save_checkpoint(job_id, stage, data)
        self.assertFalse(success, "Save should return False when disabled")

        # No files should be created
        checkpoints = self.manager.list_checkpoints(job_id)
        self.assertEqual(len(checkpoints), 0, "No checkpoints should be created when disabled")

    def test_load_when_disabled(self):
        """Test that load returns None when disabled"""
        result = self.manager.load_checkpoint("any_job", "any_stage")
        self.assertIsNone(result, "Load should return None when disabled")


class TestAtomicWrites(unittest.TestCase):
    """Test atomic file write behavior"""

    def setUp(self):
        """Create temporary checkpoint directory"""
        self.temp_dir = tempfile.mkdtemp(prefix="test_checkpoint_")
        self.manager = CheckpointManager(checkpoint_dir=self.temp_dir, enabled=True)

    def tearDown(self):
        """Clean up temporary directory"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_overwrite_checkpoint(self):
        """Test that saving to same stage overwrites previous data"""
        job_id = "overwrite_test"
        stage = "test_stage"

        # Save first version
        data1 = {"version": 1}
        self.manager.save_checkpoint(job_id, stage, data1)

        # Save second version
        data2 = {"version": 2}
        self.manager.save_checkpoint(job_id, stage, data2)

        # Load should return second version
        loaded = self.manager.load_checkpoint(job_id, stage)
        self.assertEqual(loaded, data2, "Should load most recent version")

    def test_concurrent_save_safety(self):
        """Test that saves are atomic (no corruption)"""
        job_id = "concurrent_test"
        stage = "test_stage"

        # Rapidly save multiple versions
        for i in range(10):
            data = {"iteration": i, "data": "x" * 1000}
            self.manager.save_checkpoint(job_id, stage, data)

        # Final load should succeed and return valid JSON
        loaded = self.manager.load_checkpoint(job_id, stage)
        self.assertIsNotNone(loaded)
        self.assertIn("iteration", loaded)


class TestComplexData(unittest.TestCase):
    """Test checkpointing with complex data structures"""

    def setUp(self):
        """Create temporary checkpoint directory"""
        self.temp_dir = tempfile.mkdtemp(prefix="test_checkpoint_")
        self.manager = CheckpointManager(checkpoint_dir=self.temp_dir, enabled=True)

    def tearDown(self):
        """Clean up temporary directory"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_nested_data(self):
        """Test saving/loading nested dictionaries"""
        job_id = "nested_test"
        stage = "test_stage"

        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": 42
                    }
                }
            }
        }

        self.manager.save_checkpoint(job_id, stage, data)
        loaded = self.manager.load_checkpoint(job_id, stage)

        self.assertEqual(loaded, data)

    def test_list_data(self):
        """Test saving/loading lists"""
        job_id = "list_test"
        stage = "test_stage"

        data = [
            {"id": 1, "name": "first"},
            {"id": 2, "name": "second"},
            {"id": 3, "name": "third"}
        ]

        self.manager.save_checkpoint(job_id, stage, data)
        loaded = self.manager.load_checkpoint(job_id, stage)

        self.assertEqual(loaded, data)

    def test_mixed_types(self):
        """Test saving/loading mixed data types"""
        job_id = "mixed_test"
        stage = "test_stage"

        data = {
            "string": "test",
            "integer": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "list": [1, 2, 3],
            "dict": {"key": "value"}
        }

        self.manager.save_checkpoint(job_id, stage, data)
        loaded = self.manager.load_checkpoint(job_id, stage)

        self.assertEqual(loaded, data)


if __name__ == '__main__':
    # Run tests with verbosity
    unittest.main(verbosity=2)
