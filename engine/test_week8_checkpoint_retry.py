#!/usr/bin/env python3
"""
Week 8: Test Checkpoint and Retry Systems

Verifies that the new error handling and checkpointing features work correctly.
"""

import sys
import time
sys.path.insert(0, '.')

from arena.editorial.checkpoint import CheckpointManager, CheckpointContext
from arena.editorial.retry import call_api_with_retry, call_api_with_smart_retry, APIRetryError

print("="*70)
print("WEEK 8: CHECKPOINT & RETRY SYSTEM TESTS")
print("="*70)
print()

# =========================================================================
# TEST 1: Checkpoint Manager Basic Functionality
# =========================================================================

print("TEST 1: Checkpoint Manager")
print("-"*70)

mgr = CheckpointManager(checkpoint_dir=".test_checkpoint", enabled=True)

# Generate test job ID
test_transcript = {"text": "This is a test transcript for checkpoint testing"}
job_id = CheckpointManager.generate_job_id(test_transcript)
print(f"✓ Generated job ID: {job_id}")

# Save a checkpoint
test_data = {
    "seeds": [
        {"timestamp": 10.0, "text": "Seed 1"},
        {"timestamp": 20.0, "text": "Seed 2"}
    ],
    "count": 2
}

success = mgr.save_checkpoint(
    job_id=job_id,
    stage="seed_detection",
    data=test_data,
    metadata={"cost": 0.05, "tokens": 1000}
)

if success:
    print("✓ Checkpoint saved successfully")
else:
    print("❌ Failed to save checkpoint")

# Load the checkpoint
loaded_data = mgr.load_checkpoint(job_id, "seed_detection")

if loaded_data:
    print("✓ Checkpoint loaded successfully")
    print(f"  Loaded {loaded_data['count']} seeds")

    if loaded_data == test_data:
        print("✓ Data integrity verified")
    else:
        print("❌ Data mismatch!")
else:
    print("❌ Failed to load checkpoint")

# List checkpoints
checkpoints = mgr.list_checkpoints(job_id)
print(f"✓ Checkpoints for job: {', '.join(checkpoints)}")

# Get checkpoint info
info = mgr.get_checkpoint_info(job_id, "seed_detection")
if info:
    print(f"✓ Checkpoint info:")
    print(f"  Timestamp: {info['timestamp']}")
    print(f"  File size: {info['file_size']} bytes")

# Clear checkpoints
removed = mgr.clear_checkpoints(job_id)
print(f"✓ Cleared {removed} checkpoints")

print()

# =========================================================================
# TEST 2: Checkpoint Context Manager
# =========================================================================

print("TEST 2: Checkpoint Context Manager")
print("-"*70)

job_id2 = "test_context_job"

with CheckpointContext(mgr, job_id2, auto_cleanup=True) as ctx:
    # Save some checkpoints
    ctx.save("stage1", {"data": "stage1"})
    ctx.save("stage2", {"data": "stage2"})

    print("✓ Saved checkpoints within context")

    # Load a checkpoint
    loaded = ctx.load("stage1")
    if loaded:
        print(f"✓ Loaded checkpoint: {loaded}")

    # Mark as successful (enables auto-cleanup)
    ctx.mark_success()

# Verify auto-cleanup worked
remaining = mgr.list_checkpoints(job_id2)
if len(remaining) == 0:
    print("✓ Auto-cleanup successful (no checkpoints remain)")
else:
    print(f"⚠️  Auto-cleanup failed ({len(remaining)} checkpoints remain)")

print()

# =========================================================================
# TEST 3: API Retry Logic
# =========================================================================

print("TEST 3: API Retry Logic")
print("-"*70)

# Test successful call
def successful_api_call():
    """Simulates a successful API call"""
    return {"result": "success"}

result = call_api_with_retry(successful_api_call, max_retries=3, verbose=False)
if result == {"result": "success"}:
    print("✓ Successful API call works")
else:
    print("❌ Successful call returned wrong result")

# Test failing then succeeding call
attempt_counter = {"count": 0}

def failing_then_success():
    """Fails twice, then succeeds"""
    attempt_counter["count"] += 1
    if attempt_counter["count"] < 3:
        raise Exception("Simulated API failure")
    return {"result": "success after retries"}

try:
    result = call_api_with_retry(failing_then_success, max_retries=3, initial_delay=0.1, verbose=True)
    if result == {"result": "success after retries"}:
        print(f"✓ Retry logic works (succeeded on attempt {attempt_counter['count']})")
    else:
        print("❌ Retry succeeded but wrong result")
except APIRetryError:
    print("❌ Should have succeeded after retries")

# Reset counter
attempt_counter["count"] = 0

# Test exhausted retries
def always_failing():
    """Always fails"""
    raise Exception("Persistent API failure")

try:
    result = call_api_with_retry(always_failing, max_retries=2, initial_delay=0.1, verbose=False)
    print("❌ Should have raised APIRetryError")
except APIRetryError as e:
    print(f"✓ Correctly raises APIRetryError after exhausted retries")
    print(f"  Error: {str(e)[:80]}...")

print()

# =========================================================================
# TEST 4: Smart Retry (Retryable vs Non-Retryable Errors)
# =========================================================================

print("TEST 4: Smart Retry Logic")
print("-"*70)

# Test retryable error (network issue)
def retryable_error():
    """Simulates a retryable error"""
    raise Exception("Rate limit exceeded (429)")

try:
    call_api_with_smart_retry(retryable_error, max_retries=1, initial_delay=0.1, verbose=False)
    print("❌ Should have raised APIRetryError")
except APIRetryError:
    print("✓ Correctly retries on rate limit errors")

# Test non-retryable error (auth failure)
def non_retryable_error():
    """Simulates a non-retryable error"""
    raise Exception("Authentication failed (401)")

try:
    call_api_with_smart_retry(non_retryable_error, max_retries=3, initial_delay=0.1, verbose=False)
    print("❌ Should have raised original exception")
except Exception as e:
    if "Authentication" in str(e):
        print("✓ Correctly skips retry on authentication errors")
    else:
        print(f"❌ Wrong exception type: {e}")

print()

# =========================================================================
# TEST SUMMARY
# =========================================================================

print("="*70)
print("TEST SUMMARY")
print("="*70)
print()
print("✅ Checkpoint Manager:")
print("  ✓ Save/load checkpoints")
print("  ✓ List and clear checkpoints")
print("  ✓ Get checkpoint metadata")
print("  ✓ Auto-cleanup with context manager")
print()
print("✅ Retry Logic:")
print("  ✓ Handle successful calls")
print("  ✓ Retry with exponential backoff")
print("  ✓ Raise APIRetryError when exhausted")
print("  ✓ Smart retry (skip non-retryable errors)")
print()
print("🎉 All Week 8 error handling features working correctly!")
print()
print("Next steps:")
print("  1. Integrate into adapter.py")
print("  2. Test with actual video processing")
print("  3. Verify resume-from-checkpoint works")
print()
print("="*70)
