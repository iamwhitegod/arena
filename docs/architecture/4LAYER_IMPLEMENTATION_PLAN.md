# 4-Layer Editorial Architecture Implementation Plan

## Executive Summary

Implement a sophisticated 4-layer editorial system to replace the current single-layer AI analysis, dramatically improving clip quality through separation of concerns: **moment detection → thought boundaries → standalone validation → packaging**.

**Current Problem:** Single GPT-4o call tries to do everything (find moments, ensure completeness, create titles) → conflicting objectives → short/incomplete clips

**Solution:** 4 specialized layers, each with one job, explicit quality gate at Layer 3

**Integration:** Drop-in replacement adapter - change ONE line in arena_process.py

---

## Architecture Overview

### Current System (Single-Layer)
```
Transcription → [Single AI Call: Find + Validate + Package] → Energy → Hybrid → Alignment → Clips
                 ❌ All-or-nothing, no validation
```

### New System (4-Layer)
```
Transcription → [Layer 1: Find Moments (25 candidates)]
                    ↓
                [Layer 2: Expand to Complete Thoughts (18 candidates)]
                    ↓
                [Layer 3: Validate Standalone Context (12 pass, 6 reject)]
                    ↓
                [Layer 4: Package with Titles/Descriptions]
                    ↓
                Energy → Hybrid → Alignment → Clips

✅ Explicit quality gate, iterative refinement
```

---

## Key Benefits

| Metric | Current (Single-Layer) | New (4-Layer) | Improvement |
|--------|----------------------|---------------|-------------|
| **Usable Clips** | ~60% pass manual review | >90% standalone clips | +50% quality |
| **Short Clips** | 30% clips <10s (incomplete) | <5% clips <15s | Solved short clip problem |
| **Cost Per Video** | $0.20 (cheap but low quality) | $0.78 (3.9x cost) | Acceptable trade-off |
| **Debugging** | All-or-nothing black box | Inspect each layer output | Debuggable |
| **Processing Time** | ~30s | ~2-3min (parallel layers) | Slower but acceptable |

**ROI:** 3.9x cost increase for 50%+ quality improvement and near-zero unusable clips

---

## Integration Strategy: Drop-in Adapter

### Minimal Integration (ONE Line Change!)

**Before** (arena_process.py line 245):
```python
ai_analyzer = TranscriptAnalyzer(api_key=api_key)
```

**After**:
```python
from arena.editorial.adapter import FourLayerAdapter
ai_analyzer = FourLayerAdapter(api_key=api_key)
```

**That's it!** Everything else works unchanged:
- HybridAnalyzer works as-is (uses dependency injection)
- Energy analysis works as-is
- Professional alignment works as-is
- Clip generation works as-is

**Why this works:** HybridAnalyzer expects `ai_analyzer.analyze_transcript()` interface. FourLayerAdapter implements this same interface, but uses 4 layers internally.

---

## Module Structure

```
arena/editorial/                      # NEW module
├── __init__.py                       # Exports
├── adapter.py                        # FourLayerAdapter (drop-in replacement)
├── layer1_moment_detector.py        # Find interesting moments
├── layer2_boundary_analyzer.py      # Expand to thought boundaries
├── layer3_context_refiner.py        # Validate standalone context
├── layer4_packaging.py              # Generate titles/descriptions
└── utils.py                          # Shared utilities

arena/ai/
├── analyzer.py                       # KEEP for backward compatibility
└── hybrid.py                         # NO CHANGES NEEDED
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1, Day 1-2)

**Goal:** Set up module structure and adapter interface

#### Step 1.1: Create Module Structure
**Files to Create:**
- `arena/editorial/__init__.py`
- `arena/editorial/adapter.py` (stub)
- `arena/editorial/utils.py` (shared helpers)

**Deliverable:** Import structure works
```python
from arena.editorial import FourLayerAdapter
```

#### Step 1.2: Implement FourLayerAdapter Shell
**File:** `arena/editorial/adapter.py`

**Interface to Implement:**
```python
class FourLayerAdapter:
    """
    Drop-in replacement for TranscriptAnalyzer using 4-layer system.

    Maintains exact same interface for backward compatibility:
    - analyze_transcript(transcript_data, target_clips, min_duration, max_duration)
    - generate_clip_title(transcript_segment)  # For ProfessionalClipAligner
    """

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model
        # Layers initialized in Phase 2

    def analyze_transcript(
        self,
        transcript_data: Dict,
        target_clips: int = 10,
        min_duration: Optional[int] = None,
        max_duration: Optional[int] = None
    ) -> List[Dict]:
        """
        Run 4-layer analysis and return clips compatible with HybridAnalyzer.

        Returns:
            List[Dict] with format:
            {
                'id': str,           # "clip_001"
                'start_time': float,
                'end_time': float,
                'duration': float,
                'title': str,
                'reason': str,
                'interest_score': float,
                'content_type': str,
                # Metadata for debugging
                '_layer1': {...},
                '_layer2': {...},
                '_layer3': {...},
                '_layer4': {...}
            }
        """
        # Placeholder: Return empty list
        # Real implementation in Phase 2-5
        return []

    def generate_clip_title(self, transcript_segment: str) -> str:
        """
        Generate title for clip (called by ProfessionalClipAligner).
        Delegates to Layer 4.
        """
        # Placeholder
        return "Untitled Clip"
```

**Test:** Verify adapter can be imported and instantiated

---

### Phase 2: Layer 1 - Moment Detector (Week 1, Day 3-4)

**Goal:** Identify 20-30 interesting moments WITHOUT worrying about completeness

#### Step 2.1: Implement MomentDetector
**File:** `arena/editorial/layer1_moment_detector.py`

**Key Components:**
1. **Class Structure:**
   ```python
   class MomentDetector:
       def __init__(self, api_key: str, model: str = "gpt-4o")
       def detect(self, transcript_data: Dict, target_moments: int = 25) -> List[Dict]
       def _format_transcript(self, segments: List[Dict]) -> str
       def _create_prompt(self, transcript: str, target_moments: int) -> str
       def _parse_response(self, response: Dict) -> List[Dict]
   ```

2. **Prompt Strategy** (from EDITORIAL_ARCHITECTURE.md lines 214-261):
   - Cast wide net: Find hooks, insights, controversial statements, advice, emotional peaks
   - Return rough timestamps (not exact boundaries)
   - Focus on "idea density", not polish
   - Over-identify rather than miss content

3. **Output Format:**
   ```python
   {
       'rough_start': float,      # Approximate start time
       'rough_end': float,        # Approximate end time
       'core_idea': str,          # One-sentence summary
       'why_interesting': str,    # Why this moment matters
       'interest_score': float,   # 0.0-1.0
       'content_type': str        # "hook", "insight", "advice", "story"
   }
   ```

4. **Metrics Tracking:**
   ```python
   self.metrics = {
       'api_calls': 0,
       'tokens_used': 0,
       'cost_usd': 0.0,
       'moments_found': 0
   }
   ```

**Test Cases:**
- Test with 8-minute transcript (should find 15-25 moments)
- Verify interest_score distribution (should span 0.5-1.0)
- Check content_type variety (not all "insight")
- Ensure rough timestamps are within video bounds

**Integration with Adapter:**
```python
# In FourLayerAdapter.analyze_transcript()
self.moment_detector = MomentDetector(self.api_key)
moments = self.moment_detector.detect(transcript_data, target_moments=target_clips * 2.5)
```

---

### Phase 3: Layer 2 - Thought Boundary Analyzer (Week 1, Day 5-7)

**Goal:** Expand each moment to complete thought boundaries (setup → core → payoff)

#### Step 3.1: Implement ThoughtBoundaryAnalyzer
**File:** `arena/editorial/layer2_boundary_analyzer.py`

**Key Components:**
1. **Class Structure:**
   ```python
   class ThoughtBoundaryAnalyzer:
       def __init__(self, api_key: str, model: str = "gpt-4o")
       def analyze_all(self, moments: List[Dict], transcript_data: Dict, parallel: bool = True) -> List[Dict]
       def _analyze_single(self, moment: Dict, transcript_data: Dict) -> Dict
       def _extract_context_window(self, transcript_data: Dict, center_time: float, window_seconds: float = 60.0) -> str
       def _create_prompt(self, moment: Dict, context: str) -> str
   ```

2. **Prompt Strategy** (from EDITORIAL_ARCHITECTURE.md lines 468-505):
   - Look backward: Where does the speaker START setting up this idea?
   - Look forward: Where does the idea reach COMPLETION/PAYOFF?
   - Include necessary setup and resolution
   - 60-second context window around moment

3. **Output Format:**
   ```python
   {
       'moment_id': str,           # "moment_001"
       'expanded_start': float,    # Thought start (earlier than rough_start)
       'expanded_end': float,      # Thought end (later than rough_end)
       'thought_summary': str,     # One-sentence summary of complete thought
       'confidence': float,        # 0.0-1.0 (how confident in boundaries)
       'original_moment': Dict     # Preserve Layer 1 output
   }
   ```

4. **Parallel Processing:**
   ```python
   from concurrent.futures import ThreadPoolExecutor

   with ThreadPoolExecutor(max_workers=5) as executor:
       futures = [executor.submit(self._analyze_single, m, transcript_data) for m in moments]
       thoughts = [f.result() for f in futures]
   ```

**Test Cases:**
- Test boundary expansion (should be 20-50% longer than rough timestamps)
- Verify completeness (should include setup and payoff)
- Check confidence scores (should be >0.7 for most)
- Ensure no overlapping thoughts (or minimal overlap)

**Integration with Adapter:**
```python
# In FourLayerAdapter.analyze_transcript()
self.boundary_analyzer = ThoughtBoundaryAnalyzer(self.api_key)
thoughts = self.boundary_analyzer.analyze_all(moments, transcript_data, parallel=True)
```

**Performance:** With 25 moments and 5 parallel workers, expect ~1-2 minutes processing time

---

### Phase 4: Layer 3 - Standalone Context Refiner (Week 2, Day 1-3)

**Goal:** QUALITY GATE - Ensure clips are understandable without prior context

#### Step 4.1: Implement StandaloneContextRefiner
**File:** `arena/editorial/layer3_context_refiner.py`

**Key Components:**
1. **Class Structure:**
   ```python
   class StandaloneContextRefiner:
       PASS_THRESHOLD = 0.7     # Must score ≥0.7 to pass
       REVISE_THRESHOLD = 0.4   # Below 0.4 = auto-reject

       def __init__(self, api_key: str, model: str = "gpt-4o-mini")  # Cheaper model!
       def refine_all(self, thoughts: List[Dict], transcript_data: Dict, min_duration: Optional[int], max_duration: Optional[int]) -> List[Dict]
       def _validate_and_refine(self, thought: Dict, transcript_data: Dict, max_iterations: int = 2) -> Optional[Dict]
       def _validate_single(self, clip_transcript: str, start: float, end: float) -> Tuple[float, float, float, str]
       def _extract_clip_text(self, transcript_data: Dict, start: float, end: float) -> str
   ```

2. **Prompt Strategy** (from EDITORIAL_ARCHITECTURE.md lines 751-783):
   - Can someone who JUST clicked on this clip understand it without prior context?
   - Evaluate: Who? What? Why? Missing assumptions?
   - Score 0.0-1.0 for standalone quality
   - Suggest fixes: extend start/end, or reject if fundamentally requires prior knowledge

3. **Validation Criteria:**
   ```python
   # Clip must answer:
   - Who is speaking/who is this about? (Clear or irrelevant?)
   - What topic/situation? (Explained in clip?)
   - Why should viewer care? (Stakes/relevance clear?)
   - Any unresolved pronouns? ("this", "that", "it" without referent?)
   ```

4. **Output Format:**
   ```python
   {
       'thought_id': str,           # "thought_001"
       'refined_start': float,      # May adjust from expanded_start
       'refined_end': float,        # May adjust from expanded_end
       'standalone_score': float,   # 0.0-1.0
       'verdict': str,              # "PASS", "REVISE", "REJECT"
       'editor_notes': str,         # Why passed/failed
       'complete_thought': Dict     # Preserve Layer 2 output
   }
   ```

5. **Iterative Refinement:**
   ```python
   for iteration in range(max_iterations):
       result = self._validate_single(clip_text, current_start, current_end)
       refined_start, refined_end, standalone_score, notes = result

       if standalone_score >= 0.7:
           return PASS
       elif standalone_score >= 0.4:
           # Try refining boundaries
           current_start, current_end = refined_start, refined_end
           continue
       else:
           return REJECT
   ```

6. **Metrics Tracking:**
   ```python
   self.metrics = {
       'passed': 0,      # ≥0.7 score
       'revised': 0,     # Needed boundary adjustments
       'rejected': 0,    # <0.4 or unfixable
       'pass_rate': 0.0  # passed / total_thoughts
   }
   ```

**Test Cases:**
- Test with incomplete clip (missing setup) → should revise or reject
- Test with complete clip → should pass with score >0.7
- Test with clip referencing earlier content → should reject
- Verify min/max duration constraints respected

**Critical Success Metric:** Pass rate should be 50-70% (if too high, not selective enough; if too low, Layer 2 boundaries are poor)

**Integration with Adapter:**
```python
# In FourLayerAdapter.analyze_transcript()
self.context_refiner = StandaloneContextRefiner(self.api_key, model="gpt-4o-mini")
validated_clips = self.context_refiner.refine_all(
    thoughts,
    transcript_data,
    min_duration,
    max_duration
)

# Only use clips that PASSED
validated_clips = [c for c in validated_clips if c['verdict'] == 'PASS']
```

---

### Phase 5: Layer 4 - Packaging Layer (Week 2, Day 4-5)

**Goal:** Polish validated clips with titles, descriptions, hashtags

#### Step 5.1: Implement PackagingLayer
**File:** `arena/editorial/layer4_packaging.py`

**Key Components:**
1. **Class Structure:**
   ```python
   class PackagingLayer:
       def __init__(self, api_key: str, model: str = "gpt-4o-mini")  # Cheap model
       def package_all(self, validated_clips: List[Dict], transcript_data: Dict) -> List[Dict]
       def _package_single(self, clip: Dict, transcript_data: Dict) -> Dict
       def _generate_packaging(self, clip_text: str, start: float, end: float) -> Dict
       def _extract_clip_text(self, transcript_data: Dict, start: float, end: float) -> str
   ```

2. **Prompt Strategy** (from EDITORIAL_ARCHITECTURE.md lines 879-896):
   - Generate in one API call: title + description + hashtags + thumbnail time
   - Title: max 60 chars, specific not generic, compelling
   - Description: 2-3 sentences (hook + context + value)
   - Hashtags: 5 tags for tech/business audience
   - Thumbnail: best frame timestamp within clip

3. **Output Format:**
   ```python
   {
       'clip_id': str,                  # "clip_001"
       'start_time': float,
       'end_time': float,
       'duration': float,
       'title': str,                    # Final title
       'description': str,              # 2-3 sentence description
       'hashtags': List[str],           # 5 relevant hashtags
       'thumbnail_time': float,         # Best frame for thumbnail
       'thumbnail_reasoning': str,      # Why this frame
       'interest_score': float,         # From Layer 1
       'standalone_score': float,       # From Layer 3
       'content_type': str,             # From Layer 1
       # Preserve all layer outputs for debugging
       '_layer1': Dict,
       '_layer2': Dict,
       '_layer3': Dict
   }
   ```

**Test Cases:**
- Verify titles are <60 chars
- Check hashtags are relevant (not generic like #content, #video)
- Ensure thumbnail_time is within clip bounds
- Test description quality (has hook + context)

**Integration with Adapter:**
```python
# In FourLayerAdapter.analyze_transcript()
self.packager = PackagingLayer(self.api_key, model="gpt-4o-mini")
packaged_clips = self.packager.package_all(validated_clips, transcript_data)

# Select top N by combined score
combined_score = lambda c: (c['interest_score'] * 0.6) + (c['standalone_score'] * 0.4)
top_clips = sorted(packaged_clips, key=combined_score, reverse=True)[:target_clips]
```

---

### Phase 6: Complete Adapter Integration (Week 2, Day 6)

**Goal:** Wire all 4 layers together in FourLayerAdapter

#### Step 6.1: Implement analyze_transcript()
**File:** `arena/editorial/adapter.py`

**Full Implementation:**
```python
def analyze_transcript(
    self,
    transcript_data: Dict,
    target_clips: int = 10,
    min_duration: Optional[int] = None,
    max_duration: Optional[int] = None
) -> List[Dict]:
    """Run 4-layer editorial pipeline"""

    print("\n🎬 4-LAYER EDITORIAL ANALYSIS")
    print("="*70)

    # Layer 1: Find moments (over-detect 2.5x)
    print("\n[1/4] 🔍 Detecting interesting moments...")
    self.moment_detector = MomentDetector(self.api_key, model="gpt-4o")
    moments = self.moment_detector.detect(
        transcript_data,
        target_moments=int(target_clips * 2.5)
    )
    print(f"      ✓ Found {len(moments)} candidate moments")

    if not moments:
        print("      ❌ No interesting moments found")
        return []

    # Layer 2: Expand to complete thoughts
    print("\n[2/4] 🧠 Analyzing thought boundaries...")
    self.boundary_analyzer = ThoughtBoundaryAnalyzer(self.api_key, model="gpt-4o")
    thoughts = self.boundary_analyzer.analyze_all(
        moments,
        transcript_data,
        parallel=True
    )
    print(f"      ✓ Analyzed {len(thoughts)} complete thoughts")

    if not thoughts:
        print("      ❌ No complete thoughts identified")
        return []

    # Layer 3: Validate standalone context
    print("\n[3/4] ✂️  Validating standalone context...")
    self.context_refiner = StandaloneContextRefiner(self.api_key, model="gpt-4o-mini")
    validated_clips = self.context_refiner.refine_all(
        thoughts,
        transcript_data,
        min_duration,
        max_duration
    )

    # Filter to only PASS clips
    passed_clips = [c for c in validated_clips if c['verdict'] == 'PASS']
    print(f"      ✓ {len(passed_clips)} clips passed validation")
    print(f"      ✗ {len(validated_clips) - len(passed_clips)} clips rejected")

    if not passed_clips:
        print("      ❌ No clips passed standalone validation")
        return []

    # Layer 4: Package top clips
    print("\n[4/4] 📦 Packaging clips...")
    self.packager = PackagingLayer(self.api_key, model="gpt-4o-mini")
    packaged_clips = self.packager.package_all(passed_clips, transcript_data)

    # Select top N by combined score (60% interest + 40% standalone)
    combined_score = lambda c: (c['interest_score'] * 0.6) + (c['standalone_score'] * 0.4)
    top_clips = sorted(packaged_clips, key=combined_score, reverse=True)[:target_clips]

    print(f"      ✓ Packaged {len(top_clips)} final clips")

    # Convert to TranscriptAnalyzer format
    legacy_clips = self._convert_to_legacy_format(top_clips)

    # Print summary
    self._print_summary(legacy_clips)

    return legacy_clips

def _convert_to_legacy_format(self, clips: List[Dict]) -> List[Dict]:
    """Convert 4-layer output to format expected by HybridAnalyzer"""
    legacy_clips = []
    for i, clip in enumerate(clips, 1):
        legacy_clips.append({
            # Required fields (HybridAnalyzer expects these)
            'id': f"clip_{i:03d}",
            'start_time': clip['start_time'],
            'end_time': clip['end_time'],
            'duration': clip['duration'],
            'title': clip['title'],
            'reason': clip['description'],  # Use description as reason
            'interest_score': clip['interest_score'],
            'content_type': clip['content_type'],
            # Extra metadata (preserved through pipeline)
            '_4layer_metadata': {
                'standalone_score': clip['standalone_score'],
                'hashtags': clip['hashtags'],
                'thumbnail_time': clip['thumbnail_time'],
                'layer1': clip.get('_layer1'),
                'layer2': clip.get('_layer2'),
                'layer3': clip.get('_layer3')
            }
        })
    return legacy_clips

def _print_summary(self, clips: List[Dict]):
    """Print summary of 4-layer analysis"""
    print("\n" + "="*70)
    print("📊 EDITORIAL SUMMARY")
    print("="*70)
    print(f"Final clips: {len(clips)}")

    # Calculate total cost
    total_cost = (
        self.moment_detector.metrics.get('cost_usd', 0) +
        self.boundary_analyzer.metrics.get('cost_usd', 0) +
        self.context_refiner.metrics.get('cost_usd', 0) +
        self.packager.metrics.get('cost_usd', 0)
    )
    print(f"Estimated cost: ${total_cost:.2f}")

    # Show top 3 clips
    print("\nTop 3 Clips:")
    for i, clip in enumerate(clips[:3], 1):
        print(f"  {i}. [{clip['duration']:.1f}s] {clip['title']}")
        score = (clip['interest_score'] * 0.6) + (clip['_4layer_metadata']['standalone_score'] * 0.4)
        print(f"     Combined Score: {score:.2f}")

    print("="*70 + "\n")
```

#### Step 6.2: Implement generate_clip_title()
**For ProfessionalClipAligner compatibility:**
```python
def generate_clip_title(self, transcript_segment: str) -> str:
    """
    Generate title for aligned clip.
    Called by ProfessionalClipAligner after boundary adjustments.
    """
    if not hasattr(self, 'packager'):
        self.packager = PackagingLayer(self.api_key, model="gpt-4o-mini")

    # Use Layer 4 to generate title
    return self.packager._generate_title_only(transcript_segment)
```

---

### Phase 7: Pipeline Integration (Week 2, Day 7)

**Goal:** Integrate FourLayerAdapter into main pipeline

#### Step 7.1: Update arena_process.py
**File:** `arena_process.py`

**Change Line 245:**
```python
# BEFORE:
from arena.ai.analyzer import TranscriptAnalyzer
ai_analyzer = TranscriptAnalyzer(api_key=api_key)

# AFTER:
from arena.editorial.adapter import FourLayerAdapter
ai_analyzer = FourLayerAdapter(api_key=api_key)
```

**Add CLI Flag (Line 576+):**
```python
parser.add_argument(
    '--use-4layer',
    action='store_true',
    help='Use 4-layer editorial system (higher quality, slower, more expensive)'
)

parser.add_argument(
    '--export-editorial-layers',
    action='store_true',
    help='Export intermediate results from each editorial layer for debugging'
)
```

**Conditional Usage (Line 245):**
```python
if args.use_4layer:
    from arena.editorial.adapter import FourLayerAdapter
    ai_analyzer = FourLayerAdapter(
        api_key=api_key,
        export_layers=args.export_editorial_layers
    )
else:
    from arena.ai.analyzer import TranscriptAnalyzer
    ai_analyzer = TranscriptAnalyzer(api_key=api_key)
```

#### Step 7.2: Layer Export Feature
**In FourLayerAdapter.__init__():**
```python
def __init__(self, api_key: str, model: str = "gpt-4o", export_layers: bool = False):
    self.api_key = api_key
    self.model = model
    self.export_layers = export_layers
    self.layer_outputs = {}  # Store for export

def export_layer_outputs(self, output_dir: Path):
    """Export intermediate layer results for debugging"""
    if not self.export_layers:
        return

    layer_dir = output_dir / "editorial"
    layer_dir.mkdir(exist_ok=True, parents=True)

    for layer_name, data in self.layer_outputs.items():
        output_file = layer_dir / f"{layer_name}.json"
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"   Exported {layer_name}.json")
```

---

## Testing Strategy

### Unit Tests (Per Layer)

**File:** `tests/editorial/test_layer1_moment_detector.py`
```python
def test_moment_detector_finds_hooks():
    detector = MomentDetector(api_key=test_key)
    transcript = load_test_transcript("tech_talk_8min.json")
    moments = detector.detect(transcript, target_moments=10)

    assert len(moments) >= 8  # Should find most requested moments
    assert len(moments) <= 15  # But not too many
    assert any(m['content_type'] == 'hook' for m in moments)
    assert all(0 <= m['interest_score'] <= 1.0 for m in moments)

def test_moment_detector_respects_target_count():
    detector = MomentDetector(api_key=test_key)
    transcript = load_test_transcript("long_video_30min.json")
    moments = detector.detect(transcript, target_moments=25)

    assert len(moments) == 25
```

**Similar tests for Layers 2, 3, 4**

### Integration Tests

**File:** `tests/editorial/test_adapter_integration.py`
```python
def test_adapter_returns_legacy_format():
    """Verify adapter output is compatible with HybridAnalyzer"""
    adapter = FourLayerAdapter(api_key=test_key)
    transcript = load_test_transcript("tech_talk_8min.json")

    clips = adapter.analyze_transcript(transcript, target_clips=5)

    # Check required fields
    assert all('id' in clip for clip in clips)
    assert all('start_time' in clip for clip in clips)
    assert all('end_time' in clip for clip in clips)
    assert all('title' in clip for clip in clips)
    assert all('interest_score' in clip for clip in clips)

    # Check metadata preserved
    assert all('_4layer_metadata' in clip for clip in clips)

def test_full_pipeline_with_4layer():
    """Test complete pipeline with 4-layer system"""
    # This would run arena_process.py with --use-4layer flag
    result = subprocess.run([
        'python', 'arena_process.py',
        'test_video.mp4',
        '--use-4layer',
        '-n', '3'
    ], capture_output=True)

    assert result.returncode == 0
    assert Path('output/clips/clip_001.mp4').exists()
```

### Manual Review

**Generate Review Report:**
```bash
python arena_process.py video.mp4 --use-4layer --export-editorial-layers -n 10

# Generates:
# - output/editorial/layer1_moments.json
# - output/editorial/layer2_boundaries.json
# - output/editorial/layer3_validated.json
# - output/editorial/layer4_packaged.json
```

**Review Checklist:**
- [ ] Are Layer 1 moments actually interesting?
- [ ] Do Layer 2 boundaries feel complete (setup → payoff)?
- [ ] Are Layer 3 rejections justified (missing context)?
- [ ] Are Layer 4 titles compelling and accurate?
- [ ] Do final clips work standalone (watch without prior context)?

---

## Cost Analysis

### Token Estimates (30-minute video)

| Layer | Model | Input Tokens | Output Tokens | Cost |
|-------|-------|--------------|---------------|------|
| **Layer 1** | GPT-4o | 8,000 (full transcript) | 1,000 (25 moments) | $0.30 |
| **Layer 2** | GPT-4o | 500 × 25 calls (context windows) | 200 × 25 (boundaries) | $0.60 |
| **Layer 3** | GPT-4o-mini | 300 × 18 calls (clip text) | 150 × 18 (validation) | $0.05 |
| **Layer 4** | GPT-4o-mini | 300 × 10 calls (clip text) | 400 × 10 (packaging) | $0.03 |
| **Total** | - | ~21,000 | ~7,000 | **~$0.98** |

**Comparison:**
- Current single-layer: ~$0.20 per video
- New 4-layer: ~$0.98 per video
- **Increase: 4.9x** but quality improvement justifies cost

**Optimization Opportunities:**
- Use prompt caching for Layer 1 (save ~30%)
- Batch Layer 2 calls (save ~20%)
- Fine-tune GPT-4o-mini for Layer 3 (save ~40% Layer 3 cost)

---

## Performance Benchmarks

### Processing Time (30-minute video)

| Phase | Current (Single-Layer) | New (4-Layer Sequential) | New (4-Layer Parallel) |
|-------|----------------------|-------------------------|----------------------|
| **Layer 1** | - | 15s | 15s |
| **Layer 2** | - | 150s (25 × 6s) | 30s (5 parallel workers) |
| **Layer 3** | - | 90s (18 × 5s) | 18s (5 parallel workers) |
| **Layer 4** | - | 30s (10 × 3s) | 6s (5 parallel workers) |
| **Total** | 30s | 285s (~5min) | **69s (~1min)** |

**Speedup:** Parallel processing provides 4.1x speedup

**Implementation:** Use `concurrent.futures.ThreadPoolExecutor` with 5 workers for Layers 2-4

---

## Success Metrics

### Quality Metrics
- **Clip Validity Rate:** >90% (vs. current ~60%)
- **Average Standalone Score:** >0.75 (Layer 3 metric)
- **Short Clip Rate:** <5% clips <15s (vs. current ~30%)
- **Manual Review Score:** >4.0/5.0 (human rating)

### Performance Metrics
- **Processing Time:** <2 minutes for 30min video (parallel mode)
- **Pass Rate:** 50-70% clips pass Layer 3 validation
- **API Reliability:** <5% layer failures

### Cost Metrics
- **Cost Per Video:** <$1.50
- **Cost Per Final Clip:** <$0.15
- **ROI:** Quality improvement justifies 4-5x cost increase

---

## Rollout Plan

### Week 1: Core Implementation
- **Day 1-2:** Module structure + Adapter shell
- **Day 3-4:** Layer 1 (Moment Detector)
- **Day 5-7:** Layer 2 (Boundary Analyzer)

### Week 2: Validation & Packaging
- **Day 1-3:** Layer 3 (Context Refiner) - CRITICAL
- **Day 4-5:** Layer 4 (Packaging)
- **Day 6:** Complete adapter integration
- **Day 7:** Pipeline integration + testing

### Week 3: Testing & Optimization
- **Day 1-2:** Unit tests for all layers
- **Day 3-4:** Integration tests + manual review
- **Day 5:** Parallel processing optimization
- **Day 6-7:** Bug fixes + prompt tuning

### Week 4: Production
- **Day 1-2:** Documentation + metrics dashboard
- **Day 3:** Beta testing with real videos
- **Day 4-5:** Production deployment
- **Day 6-7:** Monitor metrics + iterate

---

## Critical Files Summary

### Files to Create
```
arena/editorial/
├── __init__.py                       # ~20 lines
├── adapter.py                        # ~300 lines (main adapter)
├── layer1_moment_detector.py        # ~200 lines
├── layer2_boundary_analyzer.py      # ~300 lines (parallel processing)
├── layer3_context_refiner.py        # ~350 lines (validation + refinement)
├── layer4_packaging.py              # ~150 lines
└── utils.py                          # ~100 lines (shared helpers)

Total: ~1,420 lines of new code
```

### Files to Modify
```
arena_process.py                      # 3 lines changed (import + CLI flag)
arena/ai/__init__.py                  # 1 line (export FourLayerAdapter)
```

**Total Changes:** ~1,425 lines added, ~4 lines modified

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Layer 3 rejects too many clips** | High | Tune PASS_THRESHOLD (start at 0.65, monitor pass rate) |
| **Cost exceeds budget** | Medium | Implement prompt caching, use GPT-4o-mini where possible |
| **Processing too slow** | Medium | Parallel processing (Layers 2-4), optimize context windows |
| **Backward compatibility break** | High | Maintain TranscriptAnalyzer interface exactly, add feature flag |
| **GPT-4o API rate limits** | Medium | Add retry logic with exponential backoff, queue requests |

---

## Next Steps

1. **Review this plan** - Approve/modify implementation approach
2. **Start with Phase 1** - Create module structure and adapter shell
3. **Iterate layer by layer** - Test each layer thoroughly before moving to next
4. **Enable feature flag** - Deploy with `--use-4layer` flag for opt-in testing
5. **Collect metrics** - Monitor quality, cost, and performance
6. **Make default** - Once proven, replace single-layer as default

**Estimated Timeline:** 3 weeks full implementation + 1 week testing/optimization

**Ready to proceed?** Start with Phase 1 (Module Structure + Adapter Shell)
