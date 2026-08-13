# Arena Editorial System - API Reference

**Version:** Week 8 (Production Ready)
**Last Updated:** January 30, 2026

---

## Table of Contents

1. [FourLayerAdapter](#fourlayeradapter) - Main interface
2. [CheckpointManager](#checkpointmanager) - Progress checkpointing
3. [Retry Functions](#retry-functions) - API error handling
4. [Error Handling](#error-handling) - Exception handling

---

## FourLayerAdapter

Main interface for the ThoughtUnit editorial system.

### Constructor

```python
FourLayerAdapter(
    api_key: str,
    model: str = "gpt-4o-mini",
    export_layers: bool = False,
    score_weights: Optional[Dict[str, float]] = None,
    enable_checkpoints: bool = True,
    checkpoint_dir: str = ".checkpoint"
)
```

**Parameters:**

- **`api_key`** (str, required): OpenAI API key for GPT access
- **`model`** (str, optional): Model to use. Options:
  - `"gpt-4o-mini"` (default) - Cost-effective, recommended for production
  - `"gpt-4o"` - Higher quality, 15x more expensive
- **`export_layers`** (bool, optional): Export intermediate layer outputs for debugging. Default: `False`
- **`score_weights`** (dict, optional): Custom scoring weights. Default: `{'completeness': 0.6, 'standalone': 0.4}`
- **`enable_checkpoints`** (bool, optional): Enable progress checkpointing (Week 8 feature). Default: `True`
- **`checkpoint_dir`** (str, optional): Directory for checkpoint files. Default: `".checkpoint"`

**Example:**

```python
from arena.editorial import FourLayerAdapter

# Basic usage (recommended)
adapter = FourLayerAdapter(api_key="sk-...")

# Advanced usage with custom configuration
adapter = FourLayerAdapter(
    api_key="sk-...",
    model="gpt-4o-mini",
    export_layers=True,            # Debug mode
    enable_checkpoints=True,       # Resume on failure
    score_weights={
        'completeness': 0.7,       # Prioritize completeness
        'standalone': 0.3
    }
)
```

---

### analyze_transcript()

Process transcript and generate editorial clips.

```python
analyze_transcript(
    transcript_data: Dict,
    target_clips: int = 10,
    min_duration: Optional[int] = None,
    max_duration: Optional[int] = None
) -> List[Dict]
```

**Parameters:**

- **`transcript_data`** (dict, required): Transcript with required fields:
  - `text` (str): Full transcript text
  - `segments` (list): List of segments with `start`, `end`, `text`
  - `duration` (float): Total duration in seconds
  - `words` (list, optional): Word-level timestamps

- **`target_clips`** (int, optional): Number of clips to generate. Default: `10`
  - System may return fewer if not enough quality moments found
  - Actual count depends on production quality bar (0.75 completeness)

- **`min_duration`** (int, optional): Minimum clip duration in seconds. Default: `30`
- **`max_duration`** (int, optional): Maximum clip duration in seconds. Default: `90`

**Returns:**

`List[Dict]` - List of clip dictionaries with structure:

```python
{
    # Required fields (HybridAnalyzer compatible)
    'id': str,                    # "clip_001"
    'start_time': float,          # Start time in seconds
    'end_time': float,            # End time in seconds
    'duration': float,            # Duration in seconds
    'title': str,                 # Auto-generated title (max 60 chars)
    'reason': str,                # Why this clip was selected
    'interest_score': float,      # 0.0-1.0 (uses completeness score)
    'content_type': str,          # Rhetorical type (argument, insight, etc.)

    # Editorial metadata (Week 8)
    '_4layer_metadata': {
        'completeness_score': float,    # 0.0-1.0
        'standalone_score': float,      # 0.0-1.0
        'premise_clarity': float,       # 0.0-10.0
        'claim_strength': float,        # 0.0-10.0
        'resolution_closure': float,    # 0.0-10.0
        'rhetorical_type': str,         # argument, insight, teaching, etc.
        'premise_text': str,            # Context/setup
        'claim_text': str,              # Main claim
        'resolution_text': str          # Conclusion
    }
}
```

**Example:**

```python
# Load transcript
import json
with open('transcript.json', 'r') as f:
    transcript_data = json.load(f)

# Generate clips
clips = adapter.analyze_transcript(
    transcript_data,
    target_clips=5,
    min_duration=45,
    max_duration=120
)

# Process results
for clip in clips:
    print(f"Title: {clip['title']}")
    print(f"  Duration: {clip['duration']:.1f}s")
    print(f"  Completeness: {clip['_4layer_metadata']['completeness_score']:.2f}")
    print(f"  Time: {clip['start_time']:.1f}s - {clip['end_time']:.1f}s")
    print()
```

**Performance:**

- **Short videos (< 15min):** ~2-3 minutes processing
- **Medium videos (15min - 1h):** ~5-10 minutes processing
- **Long videos (1h - 2h):** ~10-20 minutes processing
- **Cost (gpt-4o-mini):** ~$0.0045 per minute of video

**Checkpointing (Week 8):**

If processing fails mid-way, the system automatically saves progress. On restart, it resumes from the last completed stage:

```python
# First run (crashes after Week 2)
clips = adapter.analyze_transcript(transcript_data, target_clips=10)
# Processing... ⚠️  Crashed!

# Second run (resumes from checkpoint)
clips = adapter.analyze_transcript(transcript_data, target_clips=10)
#      ♻️  Resumed from checkpoint
# Processing continues from Week 2...
```

**Raises:**

- `ValueError`: If transcript_data is invalid or missing required fields
- `APIRetryError`: If API calls fail after all retry attempts (3 by default)

---

### generate_clip_title()

Generate title for clip (called by ProfessionalClipAligner).

```python
generate_clip_title(transcript_segment: str) -> str
```

**Parameters:**

- **`transcript_segment`** (str): Text content of the aligned clip

**Returns:**

`str` - Generated title (max 60 characters, title case)

**Example:**

```python
text = "What I've learned in the Bible is that obedience often precedes clarity."
title = adapter.generate_clip_title(text)
# Returns: "What I'Ve Learned In The Bible Is That Obedience Often..."
```

---

### export_layer_outputs()

Export intermediate layer results for debugging.

```python
export_layer_outputs(output_dir: Path) -> None
```

**Parameters:**

- **`output_dir`** (Path): Directory to export results to

**Creates:**

```
output_dir/
└── editorial/
    ├── week1_seeds.json          # Detected thought seeds
    ├── week2_units.json           # Constructed ThoughtUnits
    ├── week3_scored.json          # Completeness scores
    └── week4_deduplicated.json    # Final deduplicated units
```

**Example:**

```python
from pathlib import Path

adapter = FourLayerAdapter(api_key="sk-...", export_layers=True)
clips = adapter.analyze_transcript(transcript_data, target_clips=10)

# Export intermediate results
adapter.export_layer_outputs(Path("./output"))
```

---

## CheckpointManager

Manages progress checkpoints for resumable processing (Week 8 feature).

### Constructor

```python
CheckpointManager(
    checkpoint_dir: str = ".checkpoint",
    enabled: bool = True
)
```

**Parameters:**

- **`checkpoint_dir`** (str, optional): Directory to store checkpoint files. Default: `".checkpoint"`
- **`enabled`** (bool, optional): Enable checkpointing. Default: `True`

**Example:**

```python
from arena.editorial import CheckpointManager

mgr = CheckpointManager(
    checkpoint_dir=".cache/checkpoints",
    enabled=True
)
```

---

### save_checkpoint()

Save checkpoint for a processing stage.

```python
save_checkpoint(
    job_id: str,
    stage: str,
    data: Any,
    metadata: Optional[Dict] = None
) -> bool
```

**Parameters:**

- **`job_id`** (str): Unique identifier for this job (use `generate_job_id()`)
- **`stage`** (str): Processing stage name (e.g., "seed_detection", "construction")
- **`data`** (Any): Data to checkpoint (must be JSON-serializable)
- **`metadata`** (dict, optional): Optional metadata (timestamps, costs, etc.)

**Returns:**

`bool` - `True` if checkpoint saved successfully

**Example:**

```python
job_id = CheckpointManager.generate_job_id(transcript_data)

success = mgr.save_checkpoint(
    job_id=job_id,
    stage="seed_detection",
    data={"seeds": [...]},
    metadata={"cost": 0.05, "timestamp": "2026-01-30T12:00:00"}
)
```

---

### load_checkpoint()

Load checkpoint for a stage.

```python
load_checkpoint(
    job_id: str,
    stage: str
) -> Optional[Any]
```

**Parameters:**

- **`job_id`** (str): Job identifier
- **`stage`** (str): Stage name

**Returns:**

`Any` - Checkpoint data or `None` if not found

**Example:**

```python
seeds = mgr.load_checkpoint("a3f9c8e2b1d4", "seed_detection")
if seeds:
    print(f"Resuming with {len(seeds)} seeds from checkpoint")
else:
    print("No checkpoint found, starting fresh")
```

---

### generate_job_id() (static)

Generate unique job ID from transcript.

```python
@staticmethod
generate_job_id(transcript_data: Dict) -> str
```

**Parameters:**

- **`transcript_data`** (dict): Transcript with 'text' field

**Returns:**

`str` - 12-character hex job ID (stable for same transcript)

**Example:**

```python
job_id = CheckpointManager.generate_job_id(transcript_data)
print(job_id)  # e.g., "a3f9c8e2b1d4"
```

---

### clear_checkpoints()

Remove all checkpoints for a job.

```python
clear_checkpoints(job_id: str) -> int
```

**Parameters:**

- **`job_id`** (str): Job identifier

**Returns:**

`int` - Number of checkpoints removed

**Example:**

```python
removed = mgr.clear_checkpoints("a3f9c8e2b1d4")
print(f"Removed {removed} checkpoints")
```

---

## Retry Functions

API error handling with exponential backoff (Week 8 feature).

### call_api_with_retry()

Call API with automatic retry logic.

```python
call_api_with_retry(
    api_func: Callable,
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    verbose: bool = True
) -> Any
```

**Parameters:**

- **`api_func`** (Callable): Function that makes API call (lambda or function)
- **`max_retries`** (int, optional): Maximum retry attempts. Default: `3`
- **`backoff_factor`** (float, optional): Delay multiplier between retries. Default: `2.0`
- **`initial_delay`** (float, optional): Initial delay in seconds. Default: `1.0`
- **`verbose`** (bool, optional): Print retry messages. Default: `True`

**Returns:**

`Any` - API response from successful call

**Raises:**

`APIRetryError` - If all retries exhausted

**Example:**

```python
from arena.editorial import call_api_with_retry
from openai import OpenAI

client = OpenAI(api_key="sk-...")

# Automatically retries on failure (1s, 2s, 4s delays)
response = call_api_with_retry(
    lambda: client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello"}]
    ),
    max_retries=3
)
```

**Retry Behavior:**

- **Attempt 1:** Immediate
- **Attempt 2:** After 1.0s
- **Attempt 3:** After 2.0s (1.0 * 2.0)
- **Attempt 4:** After 4.0s (2.0 * 2.0)
- **After 4 failures:** Raises `APIRetryError`

---

### call_api_with_smart_retry()

Call API with smart retry logic (only retries retryable errors).

```python
call_api_with_smart_retry(
    api_func: Callable,
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    verbose: bool = True
) -> Any
```

**Parameters:** Same as `call_api_with_retry()`

**Returns:** Same as `call_api_with_retry()`

**Raises:**
- `APIRetryError` - If retryable error persists after all retries
- Original exception - If error is non-retryable (auth, invalid request)

**Retryable Errors:**
- Rate limit (429)
- Timeout errors
- Network/connection errors
- Internal server errors (500-504)

**Non-Retryable Errors (raises immediately):**
- Authentication errors (401)
- Invalid request (400)
- Permission denied (403)
- Not found (404)

**Example:**

```python
from arena.editorial import call_api_with_smart_retry

# Retries rate limits, but not auth errors
response = call_api_with_smart_retry(
    lambda: client.chat.completions.create(...)
)
```

---

### @with_retry decorator

Decorator to add retry logic to a function.

```python
@with_retry(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    verbose: bool = True
)
```

**Parameters:** Same as `call_api_with_retry()`

**Example:**

```python
from arena.editorial import with_retry

@with_retry(max_retries=3)
def my_api_call():
    return client.chat.completions.create(...)

# Automatically retries on failure
response = my_api_call()
```

---

## Error Handling

### APIRetryError

Raised when API retries are exhausted.

```python
class APIRetryError(Exception):
    """Raised when API retries are exhausted"""
    pass
```

**Example:**

```python
from arena.editorial import call_api_with_retry, APIRetryError

try:
    response = call_api_with_retry(lambda: failing_api_call())
except APIRetryError as e:
    print(f"API call failed after retries: {e}")
    # Handle failure (log, alert, fallback, etc.)
```

---

## Usage Patterns

### Pattern 1: Basic Usage (Recommended)

```python
from arena.editorial import FourLayerAdapter

# Simple and reliable
adapter = FourLayerAdapter(api_key="sk-...")
clips = adapter.analyze_transcript(transcript_data, target_clips=10)

for clip in clips:
    print(f"{clip['title']} ({clip['duration']:.1f}s)")
```

### Pattern 2: Production Usage with Checkpoints

```python
from arena.editorial import FourLayerAdapter

# Production configuration
adapter = FourLayerAdapter(
    api_key="sk-...",
    model="gpt-4o-mini",           # Cost-effective
    enable_checkpoints=True,        # Resume on failure
    checkpoint_dir=".cache/editorial"
)

clips = adapter.analyze_transcript(
    transcript_data,
    target_clips=10,
    min_duration=45,
    max_duration=120
)
```

### Pattern 3: Debug Mode

```python
from arena.editorial import FourLayerAdapter
from pathlib import Path

# Debug configuration
adapter = FourLayerAdapter(
    api_key="sk-...",
    export_layers=True              # Export intermediate results
)

clips = adapter.analyze_transcript(transcript_data, target_clips=10)

# Export debug outputs
adapter.export_layer_outputs(Path("./debug_output"))
```

### Pattern 4: Manual Checkpoint Management

```python
from arena.editorial import CheckpointManager

mgr = CheckpointManager()
job_id = CheckpointManager.generate_job_id(transcript_data)

# Manual checkpointing for custom workflows
if mgr.has_checkpoint(job_id, "custom_stage"):
    data = mgr.load_checkpoint(job_id, "custom_stage")
    print("Resuming from checkpoint...")
else:
    data = process_data()
    mgr.save_checkpoint(job_id, "custom_stage", data)
```

---

## Performance Tips

### 1. Use gpt-4o-mini (Default)

```python
# Recommended for production (15x cheaper)
adapter = FourLayerAdapter(api_key="sk-...", model="gpt-4o-mini")
```

### 2. Enable Checkpoints for Long Videos

```python
# Saves costs on re-runs (2h+ videos)
adapter = FourLayerAdapter(
    api_key="sk-...",
    enable_checkpoints=True  # Default
)
```

### 3. Use Duration Constraints

```python
# Filter out very short/long clips
clips = adapter.analyze_transcript(
    transcript_data,
    min_duration=45,    # Skip clips < 45s
    max_duration=120    # Skip clips > 2min
)
```

### 4. Adjust Target Clips Based on Video Length

```python
# More clips for longer videos
duration_minutes = transcript_data['duration'] / 60

if duration_minutes < 15:
    target_clips = 3-5
elif duration_minutes < 60:
    target_clips = 5-10
else:
    target_clips = 10-20
```

---

## Cost Estimation

**Model:** gpt-4o-mini
**Rate:** ~$0.0045 per minute of video

| Video Length | Estimated Cost | Estimated Time |
|--------------|----------------|----------------|
| 5 minutes | $0.02 | 1-2 min |
| 15 minutes | $0.07 | 2-3 min |
| 30 minutes | $0.14 | 5-7 min |
| 1 hour | $0.27 | 8-12 min |
| 2 hours | $0.54 | 15-20 min |

**Note:** Actual costs may vary based on transcript complexity and API pricing.

---

## Troubleshooting

### Issue: "OPENAI_API_KEY not set"

**Solution:** Set your API key before using the adapter:

```python
import os
os.environ['OPENAI_API_KEY'] = "sk-..."
```

### Issue: Processing crashes mid-way

**Solution:** Checkpointing is enabled by default. Just re-run:

```python
# First run (crashes)
clips = adapter.analyze_transcript(transcript_data)

# Second run (resumes automatically)
clips = adapter.analyze_transcript(transcript_data)
#      ♻️  Resumed from checkpoint
```

### Issue: Not enough clips generated

**Possible causes:**
- Duration constraints too strict (try wider range)
- Production bar too high (clips below 0.75 completeness filtered)
- Video doesn't have enough complete thoughts

**Solution:**

```python
# Widen constraints
clips = adapter.analyze_transcript(
    transcript_data,
    min_duration=30,    # Lower minimum
    max_duration=150    # Higher maximum
)
```

### Issue: API rate limit errors

**Solution:** Retry logic handles this automatically:

```python
# Automatically retries with exponential backoff
adapter = FourLayerAdapter(api_key="sk-...")
clips = adapter.analyze_transcript(transcript_data)
#      ⚠️  API call failed (attempt 1/4): Rate limit exceeded
#      ⏳ Retrying in 1.0s...
#      ✓ Success on retry
```

---

**Version:** Week 8 Production Ready
**Last Updated:** January 30, 2026
**Status:** ✅ Production-ready with checkpointing & error handling
