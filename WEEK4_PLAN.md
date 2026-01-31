# Week 4 Plan: Deduplication and Variant Selection

**Status**: Planning → Implementation

**Date**: January 30, 2026

---

## Objective

Remove duplicate/similar ThoughtUnits and select the best variant when multiple versions exist.

**Success Criteria:**
- Reduce 36 units to ~20-25 unique moments (40-50% deduplication rate)
- Keep the highest quality variant of each moment
- Preserve diversity (don't over-cluster)
- Maintain user's 3 ground truth clips

---

## Architecture

### 1. Semantic Deduplicator

**File**: `engine/arena/editorial/semantic_deduplicator.py`

**What It Does:**
- Generate embeddings for each ThoughtUnit (claim text)
- Calculate cosine similarity between all pairs
- Cluster similar units (similarity >= 0.85 threshold)
- Return clusters of duplicate/similar units

**Method:**
```python
def deduplicate(
    thought_units: List[ThoughtUnit],
    similarity_threshold: float = 0.85
) -> List[List[ThoughtUnit]]:
    """
    Returns:
        List of clusters, each containing similar ThoughtUnits
    """
```

**Embedding Strategy:**
- Use OpenAI text-embedding-3-small ($0.02/1M tokens)
- Embed claim text (the core insight)
- Cache embeddings in ThoughtUnit metadata
- Cost: ~$0.001 for 36 units

### 2. Variant Selector

**File**: `engine/arena/editorial/variant_selector.py`

**What It Does:**
- Given a cluster of similar ThoughtUnits, pick the best one
- Scoring criteria:
  1. Completeness score (highest weight: 40%)
  2. Duration (prefer 30-90s range: 30%)
  3. Claim strength (20%)
  4. Boundary quality (10%)

**Method:**
```python
def select_best_variant(
    cluster: List[ThoughtUnit]
) -> ThoughtUnit:
    """
    Returns:
        The best ThoughtUnit from the cluster
    """
```

### 3. Integration

**Update**: `engine/arena/editorial/thought_unit_constructor.py`

Add final step:
```python
def deduplicate_units(
    thought_units: List[ThoughtUnit]
) -> List[ThoughtUnit]:
    # 1. Cluster similar units
    # 2. Select best variant from each cluster
    # 3. Return deduplicated list
```

---

## Implementation Steps

### Step 1: Semantic Deduplicator (30 minutes)

**Create** `semantic_deduplicator.py`:
- `__init__(api_key)` - Initialize with OpenAI API
- `generate_embeddings(units)` - Get embeddings for all units
- `calculate_similarity_matrix(embeddings)` - Pairwise cosine similarity
- `cluster_similar_units(units, threshold)` - Group by similarity
- `deduplicate(units)` - Main method

**Key Design Decisions:**
- Threshold: 0.85 (85% similar = duplicate)
- Embed claim text only (the core insight)
- Use cosine similarity (standard for semantic similarity)

### Step 2: Variant Selector (20 minutes)

**Create** `variant_selector.py`:
- `score_variant(unit)` - Calculate variant quality score
- `select_best_variant(cluster)` - Pick best from cluster
- Scoring formula:
  ```
  score = (
      completeness_score * 0.4 +
      duration_score * 0.3 +
      claim_strength / 10 * 0.2 +
      boundary_quality * 0.1
  )
  ```

**Duration Scoring:**
- Ideal: 30-90s (score = 1.0)
- Too short (<20s): score = 0.5
- Too long (>120s): score = 0.7

### Step 3: Integration (15 minutes)

**Update** constructor to add deduplication step:
```python
# After scoring and validation
deduplicated = deduplicate_units(thought_units)
```

### Step 4: Testing (30 minutes)

**Create** `tests/test_week4_deduplication.py`:
- Load Week 3 output (36 units)
- Run deduplication
- Validate:
  - 20-25 units remain (40-50% reduction)
  - User's 3 clips preserved
  - Highest quality variants kept
  - No over-clustering

---

## Success Metrics

### Deduplication Rate
- **Target**: 40-50% reduction
- **Example**: 36 units → 20-25 unique moments

### Quality Preservation
- **Target**: Keep highest scoring variants
- Average completeness should increase or stay same
- Production units should increase (better selection)

### Diversity
- **Target**: Don't over-cluster
- Keep distinct moments even if somewhat similar
- Preserve rhetorical type diversity

### User Clips
- **Critical**: All 3 user clips must remain
- Should be selected as best variants in their clusters

---

## Cost Estimate

**Embeddings**: 36 units × 50 tokens = 1,800 tokens
- Cost: $0.0001 (negligible)

**Total Week 4 Cost**: ~$0.0001

**Full Pipeline** (Weeks 1-4): ~$0.11

---

## Risk Mitigation

### Risk 1: Over-Deduplication
**Issue**: Removing too many units, losing diversity
**Mitigation**:
- Use conservative threshold (0.85)
- Test on ground truth clips
- Manual review of clusters

### Risk 2: Wrong Variant Selection
**Issue**: Keeping lower quality variant
**Mitigation**:
- Weight completeness score heavily (40%)
- Validate against user's ground truth
- Test multiple scoring formulas

### Risk 3: Losing User Clips
**Issue**: User's favorite moments removed
**Mitigation**:
- Test preserves all 3 user clips
- If any removed, adjust clustering

---

## Next Steps After Week 4

**Week 5**: Clip generation and export
**Week 6**: Integration with Arena CLI
**Week 7**: End-to-end testing
**Week 8**: Production release

---

**Status**: Ready to implement
**Estimated Time**: 1.5 hours
**Confidence**: 95%
