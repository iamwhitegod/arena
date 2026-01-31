"""
Progress Checkpointing for Resumable Editorial Processing

Allows resuming from failure without re-processing completed work.
Critical for long videos (2+ hours) where API costs are significant.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime


class CheckpointManager:
    """
    Manages progress checkpoints for resumable editorial processing.

    Each checkpoint saves the output of a processing stage, allowing
    the system to resume from that point if processing fails.

    Checkpoints are identified by a job_id (hash of transcript) and
    stage name.
    """

    def __init__(self, checkpoint_dir: str = ".checkpoint", enabled: bool = True):
        """
        Initialize checkpoint manager.

        Args:
            checkpoint_dir: Directory to store checkpoints (default: .checkpoint)
            enabled: Enable checkpointing (default: True)
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.enabled = enabled

        if self.enabled:
            self.checkpoint_dir.mkdir(exist_ok=True)

    @staticmethod
    def generate_job_id(transcript_data: Dict) -> str:
        """
        Generate unique job ID from transcript.

        Uses hash of first 500 characters of transcript text to create
        a stable identifier for this video.

        Args:
            transcript_data: Transcript dict with 'text' field

        Returns:
            12-character hex job ID

        Example:
            >>> job_id = CheckpointManager.generate_job_id(transcript_data)
            >>> print(job_id)  # e.g., "a3f9c8e2b1d4"
        """
        text_sample = str(transcript_data.get('text', ''))[:500]
        hash_obj = hashlib.md5(text_sample.encode())
        return hash_obj.hexdigest()[:12]

    def save_checkpoint(
        self,
        job_id: str,
        stage: str,
        data: Any,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Save checkpoint for current stage.

        Args:
            job_id: Unique identifier for this processing job
            stage: Processing stage (seed_detection, construction, etc.)
            data: Data to checkpoint (will be JSON serialized)
            metadata: Optional metadata (timestamps, costs, etc.)

        Returns:
            True if checkpoint saved successfully

        Example:
            >>> mgr = CheckpointManager()
            >>> mgr.save_checkpoint(
            ...     job_id="a3f9c8e2b1d4",
            ...     stage="seed_detection",
            ...     data={"seeds": [...]},
            ...     metadata={"cost": 0.05, "timestamp": "2025-01-30T12:00:00"}
            ... )
            True
        """
        if not self.enabled:
            return False

        try:
            checkpoint_file = self.checkpoint_dir / f"{job_id}_{stage}.json"

            checkpoint = {
                'job_id': job_id,
                'stage': stage,
                'timestamp': datetime.now().isoformat(),
                'data': data,
                'metadata': metadata or {}
            }

            # Write atomically (write to temp, then rename)
            temp_file = checkpoint_file.with_suffix('.json.tmp')
            with open(temp_file, 'w') as f:
                json.dump(checkpoint, f, indent=2, default=str)

            temp_file.replace(checkpoint_file)

            print(f"      💾 Checkpoint saved: {stage}")
            return True

        except Exception as e:
            print(f"      ⚠️  Failed to save checkpoint: {e}")
            return False

    def load_checkpoint(
        self,
        job_id: str,
        stage: str
    ) -> Optional[Any]:
        """
        Load checkpoint for stage.

        Args:
            job_id: Job identifier
            stage: Stage to load

        Returns:
            Checkpoint data or None if not found

        Example:
            >>> mgr = CheckpointManager()
            >>> seeds = mgr.load_checkpoint("a3f9c8e2b1d4", "seed_detection")
            >>> if seeds:
            ...     print(f"Loaded {len(seeds)} seeds from checkpoint")
        """
        if not self.enabled:
            return None

        try:
            checkpoint_file = self.checkpoint_dir / f"{job_id}_{stage}.json"

            if not checkpoint_file.exists():
                return None

            with open(checkpoint_file, 'r') as f:
                checkpoint = json.load(f)

            # Verify checkpoint integrity
            if checkpoint.get('job_id') != job_id or checkpoint.get('stage') != stage:
                print(f"      ⚠️  Checkpoint integrity check failed for {stage}")
                return None

            print(f"      ♻️  Loaded checkpoint: {stage} ({checkpoint['timestamp']})")
            return checkpoint['data']

        except Exception as e:
            print(f"      ⚠️  Failed to load checkpoint: {e}")
            return None

    def has_checkpoint(self, job_id: str, stage: str) -> bool:
        """
        Check if checkpoint exists for stage.

        Args:
            job_id: Job identifier
            stage: Stage name

        Returns:
            True if checkpoint exists

        Example:
            >>> if mgr.has_checkpoint("a3f9c8e2b1d4", "seed_detection"):
            ...     print("Can resume from seed detection")
        """
        if not self.enabled:
            return False

        checkpoint_file = self.checkpoint_dir / f"{job_id}_{stage}.json"
        return checkpoint_file.exists()

    def list_checkpoints(self, job_id: str) -> List[str]:
        """
        List all checkpoints for a job.

        Args:
            job_id: Job identifier

        Returns:
            List of stage names with checkpoints

        Example:
            >>> stages = mgr.list_checkpoints("a3f9c8e2b1d4")
            >>> print(f"Checkpoints: {', '.join(stages)}")
        """
        if not self.enabled:
            return []

        checkpoints = []
        for checkpoint_file in self.checkpoint_dir.glob(f"{job_id}_*.json"):
            # Extract stage name from filename
            stage = checkpoint_file.stem.replace(f"{job_id}_", "")
            checkpoints.append(stage)

        return sorted(checkpoints)

    def clear_checkpoints(self, job_id: str) -> int:
        """
        Remove all checkpoints for job.

        Args:
            job_id: Job identifier

        Returns:
            Number of checkpoints removed

        Example:
            >>> removed = mgr.clear_checkpoints("a3f9c8e2b1d4")
            >>> print(f"Removed {removed} checkpoints")
        """
        if not self.enabled:
            return 0

        count = 0
        for checkpoint_file in self.checkpoint_dir.glob(f"{job_id}_*.json"):
            try:
                checkpoint_file.unlink()
                count += 1
            except Exception as e:
                print(f"      ⚠️  Failed to remove {checkpoint_file.name}: {e}")

        if count > 0:
            print(f"      🗑️  Cleared {count} checkpoints for job {job_id}")

        return count

    def get_checkpoint_info(self, job_id: str, stage: str) -> Optional[Dict]:
        """
        Get checkpoint metadata without loading full data.

        Args:
            job_id: Job identifier
            stage: Stage name

        Returns:
            Checkpoint metadata or None

        Example:
            >>> info = mgr.get_checkpoint_info("a3f9c8e2b1d4", "seed_detection")
            >>> if info:
            ...     print(f"Created: {info['timestamp']}")
            ...     print(f"Cost: ${info['metadata'].get('cost', 0)}")
        """
        if not self.enabled:
            return None

        try:
            checkpoint_file = self.checkpoint_dir / f"{job_id}_{stage}.json"

            if not checkpoint_file.exists():
                return None

            with open(checkpoint_file, 'r') as f:
                checkpoint = json.load(f)

            return {
                'job_id': checkpoint['job_id'],
                'stage': checkpoint['stage'],
                'timestamp': checkpoint['timestamp'],
                'metadata': checkpoint.get('metadata', {}),
                'file_size': checkpoint_file.stat().st_size
            }

        except Exception as e:
            print(f"      ⚠️  Failed to get checkpoint info: {e}")
            return None

    def get_total_size(self, job_id: Optional[str] = None) -> int:
        """
        Get total size of checkpoints.

        Args:
            job_id: Optional job ID to filter by

        Returns:
            Total size in bytes

        Example:
            >>> size = mgr.get_total_size()
            >>> print(f"Checkpoint storage: {size / 1024 / 1024:.1f} MB")
        """
        if not self.enabled:
            return 0

        total_size = 0
        pattern = f"{job_id}_*.json" if job_id else "*.json"

        for checkpoint_file in self.checkpoint_dir.glob(pattern):
            try:
                total_size += checkpoint_file.stat().st_size
            except Exception:
                pass

        return total_size

    def cleanup_old_checkpoints(self, max_age_days: int = 7) -> int:
        """
        Remove checkpoints older than max_age_days.

        Args:
            max_age_days: Maximum age in days

        Returns:
            Number of checkpoints removed

        Example:
            >>> removed = mgr.cleanup_old_checkpoints(max_age_days=7)
            >>> print(f"Removed {removed} old checkpoints")
        """
        if not self.enabled:
            return 0

        import time
        max_age_seconds = max_age_days * 24 * 3600
        current_time = time.time()
        count = 0

        for checkpoint_file in self.checkpoint_dir.glob("*.json"):
            try:
                file_age = current_time - checkpoint_file.stat().st_mtime
                if file_age > max_age_seconds:
                    checkpoint_file.unlink()
                    count += 1
            except Exception as e:
                print(f"      ⚠️  Failed to remove {checkpoint_file.name}: {e}")

        if count > 0:
            print(f"      🗑️  Cleaned up {count} old checkpoints")

        return count


class CheckpointContext:
    """
    Context manager for automatic checkpoint cleanup.

    Example:
        >>> with CheckpointContext(mgr, job_id) as ctx:
        ...     # Process video
        ...     ctx.save("stage1", data1)
        ...     ctx.save("stage2", data2)
        >>> # Checkpoints automatically cleared on success
    """

    def __init__(
        self,
        manager: CheckpointManager,
        job_id: str,
        auto_cleanup: bool = True
    ):
        """
        Initialize checkpoint context.

        Args:
            manager: CheckpointManager instance
            job_id: Job identifier
            auto_cleanup: Automatically clear checkpoints on success
        """
        self.manager = manager
        self.job_id = job_id
        self.auto_cleanup = auto_cleanup
        self.success = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # If successful and auto_cleanup enabled, clear checkpoints
        if self.success and self.auto_cleanup and exc_type is None:
            self.manager.clear_checkpoints(self.job_id)
        return False  # Don't suppress exceptions

    def save(self, stage: str, data: Any, metadata: Optional[Dict] = None) -> bool:
        """Save checkpoint for stage"""
        return self.manager.save_checkpoint(self.job_id, stage, data, metadata)

    def load(self, stage: str) -> Optional[Any]:
        """Load checkpoint for stage"""
        return self.manager.load_checkpoint(self.job_id, stage)

    def mark_success(self):
        """Mark processing as successful (enables auto-cleanup)"""
        self.success = True
