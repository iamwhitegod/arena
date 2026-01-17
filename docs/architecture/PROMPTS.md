# Arena AI Prompts

This document catalogs all AI prompts used in Arena, their purpose, and design decisions.

---

## 1. Content Analysis Prompt

**Location**: `arena/ai/analyzer.py` → `_create_analysis_prompt()`
**Model**: GPT-4o (default)
**Purpose**: Identify the most interesting, engaging segments in a video transcript that would make compelling short-form content.

### Prompt Structure

```
Analyze this video transcript and identify the {target_clips} most interesting segments
that would make engaging short clips for social media.

{duration_guidance}

Each clip should:
- Have a clear hook or attention-grabbing opening
- Contain a complete thought or story arc
- Be engaging and valuable on its own
- Appeal to developers, founders, or technical content creators
- Start and end at natural sentence boundaries (complete sentences)

Look for:
1. Hooks and attention-grabbing statements
2. Key insights or "aha" moments
3. Controversial or thought-provoking statements
4. Actionable advice or tips
5. Emotional or passionate moments
6. Clear problem-solution narratives
7. Surprising facts or statistics
8. Relatable struggles or experiences

Transcript with timestamps:
{transcript}

Return ONLY a JSON object in this exact format:
{
  "clips": [
    {
      "start_time": 125.5,
      "end_time": 168.3,
      "title": "Why most startups fail at product-market fit",
      "reason": "Strong hook with controversial insight, complete narrative arc",
      "interest_score": 0.95,
      "content_type": "insight"
    }
  ]
}

Important:
{duration_constraint}
- Use actual timestamp values from the transcript
- Make titles compelling and specific (not generic)
- Interest score should be 0.0 to 1.0
- Content types: "hook", "insight", "advice", "story", "controversial", "emotional"
- Return exactly {target_clips} clips, ranked by interest_score (highest first)
- Prioritize complete thoughts over arbitrary time constraints
```

### Duration Guidance Variations

The `{duration_guidance}` and `{duration_constraint}` sections adapt based on user input:

#### No Constraints (Default)
```
Duration Guidance: "Identify complete thoughts, stories, or insights. Each clip MUST contain
a full arc: setup/context → core statement → resolution/conclusion. A complete standalone idea
typically requires at least 15-20 seconds to establish context and deliver value. Let the
natural boundaries of the content determine the exact length, but ensure every clip has
complete context."

Duration Constraint: "- Each clip must be a complete, self-contained idea with full context
- Include setup, development, and conclusion
- Do NOT cut mid-thought or mid-explanation
- Clips should be substantial enough that a viewer can understand and appreciate the idea
  without prior context"
```

**Design Decision**: Guides AI toward complete thoughts with full arcs. The "15-20 seconds"
is GUIDANCE (not a constraint) about what's typically needed for context. Combined with
8-second sanity filtering in validation, this prevents meaningless short clips while
maintaining content-driven flexibility.

#### User Specifies Both Min and Max
```
Duration Guidance: "Each clip should be between {min}-{max} seconds long."
Duration Constraint: "Ensure clips are between {min}-{max} seconds"
```

Example: `--min 20 --max 60` → Clips must be 20-60 seconds

#### User Specifies Only Min
```
Duration Guidance: "Each clip should be at least {min} seconds long."
Duration Constraint: "Ensure clips are at least {min} seconds"
```

Example: `--min 30` → Clips must be ≥30 seconds

#### User Specifies Only Max
```
Duration Guidance: "Each clip should be no longer than {max} seconds."
Duration Constraint: "Ensure clips are no longer than {max} seconds"
```

Example: `--max 45` → Clips must be ≤45 seconds

### Design Decisions

1. **Content-First Approach**: Default mode has no time constraints, letting natural content boundaries dictate clip length

2. **Social Media Focus**: Targets "developers, founders, or technical content creators" - adjust this for different audiences

3. **8 Content Types**: Specifically looks for hooks, insights, advice, stories, controversial takes, emotional moments, problem-solution narratives, and surprising facts

4. **Sentence Boundaries**: Explicitly instructs AI to respect sentence boundaries for professional cuts

5. **JSON Output**: Structured format ensures consistent parsing and validation

6. **Interest Scoring**: 0.0-1.0 scale allows ranking by engagement potential

---

## 2. Clip Title Generation Prompt

**Location**: `arena/ai/analyzer.py` → `generate_clip_title()`
**Model**: GPT-4o-mini (cost optimization)
**Purpose**: Generate compelling, specific titles for clips after professional alignment adjusts timestamps.

### Prompt Structure

```
Create a compelling, specific title (max 60 chars) for this video clip:

{transcript_segment}
```

### Usage Context

This prompt is called **after** sentence alignment when timestamps have been adjusted. Since the aligned clip may contain different content than originally analyzed, we regenerate the title based on the actual transcript text.

### Design Decisions

1. **GPT-4o-mini**: Cheaper model sufficient for title generation (vs. GPT-4o for analysis)

2. **60 Character Limit**: Optimal for:
   - Social media previews
   - Filename compatibility
   - Quick scanability

3. **"Compelling and Specific"**: Guidance for engaging, non-generic titles

4. **Temperature 0.8**: Creative output with some variability

5. **Max 50 Tokens**: Short, focused output

### Example Outputs

Good:
- "Why most startups fail at product-market fit"
- "The counterintuitive path to 10x growth"
- "Three mistakes that killed our first product"

Bad (generic):
- "Interesting insight"
- "Tech discussion"
- "Important tip"

---

## 3. Hashtag Suggestion Prompt

**Location**: `arena/ai/analyzer.py` → `suggest_hashtags()`
**Model**: GPT-4o-mini (cost optimization)
**Purpose**: Generate relevant hashtags for social media distribution.

### Prompt Structure

```
Suggest {max_tags} relevant hashtags for this video clip (return only hashtags,
space-separated):

{transcript_segment}
```

### Design Decisions

1. **Space-Separated Output**: Simple parsing format

2. **Configurable Count**: Default 5, adjustable via `max_tags` parameter

3. **Relevance Over Popularity**: AI chooses tags based on content, not trending topics

4. **Automatic '#' Handling**: System strips '#' prefix if AI includes it

### Usage

Currently not integrated into main pipeline but available via the `TranscriptAnalyzer` API for custom workflows.

---

## Prompt Engineering Principles

### 1. **Explicit Constraints**
All prompts clearly state output format, constraints, and expectations upfront.

### 2. **JSON Structure**
Primary prompts use JSON for consistent, parseable output.

### 3. **Temperature Settings**
- Analysis: Default (0.7) - Balanced creativity and consistency
- Titles: 0.8 - More creative
- Hashtags: Default - Standard relevance

### 4. **Token Limits**
- Analysis: 2000 tokens (comprehensive)
- Titles: 50 tokens (concise)
- Hashtags: 100 tokens (list format)

### 5. **Fallback Handling**
All prompts have try-catch blocks with sensible defaults:
- Analysis: Returns empty list
- Titles: "Untitled Clip"
- Hashtags: Empty list

### 6. **Cost Optimization**
- Heavy analysis: GPT-4o (smarter, more expensive)
- Light tasks: GPT-4o-mini (cheaper)

---

## Future Prompt Additions

### Potential Enhancements

1. **Scene Description Prompt**: Generate visual descriptions for thumbnail selection
2. **Subtitle Styling Prompt**: AI-suggested subtitle positioning and timing
3. **B-Roll Suggestion Prompt**: Identify moments needing visual overlays
4. **Audience Adaptation Prompt**: Rewrite for different target audiences
5. **Hook Rewrite Prompt**: Optimize opening seconds for retention

---

## Modifying Prompts

### Best Practices

1. **Test Incrementally**: Change one element at a time
2. **Validate Output**: Ensure JSON format remains parseable
3. **Monitor Token Usage**: Track cost implications
4. **A/B Test**: Compare old vs. new prompts on same content
5. **Document Changes**: Update this file with rationale

### Performance Metrics

Track these metrics when modifying prompts:
- Clip relevance (manual review)
- Title specificity (generic vs. specific)
- Duration distribution (when using constraints)
- JSON parse success rate
- Token usage per analysis
- Cost per 100 clips generated

---

## Version History

**v0.1.0** (2025-01-15)
- Initial prompt system
- Content-driven duration approach
- No hardcoded time constraints in default mode
- Professional sentence boundary alignment

---

## Contact

For prompt improvements or A/B test results, document findings in GitHub issues with:
1. Original prompt
2. Modified prompt
3. Sample outputs (5+ examples)
4. Metrics comparison
5. Recommended action
