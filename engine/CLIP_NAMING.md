# Clip Naming Convention

Arena uses a professional, descriptive naming convention for generated clips that makes them easy to identify, organize, and share.

## Naming Pattern

```
{title-slug}_{index}_{timestamps}.mp4
```

### Components

1. **Title Slug** (50 chars max) - **FIRST**
   - Sanitized clip title from AI analysis
   - Descriptive of the clip content
   - Lowercase, spaces/special chars replaced with hyphens
   - Example: `why-startups-fail`, `product-market-fit`, `ai-revolution`

2. **Index Number** (3 digits)
   - Sequential clip number: `001`, `002`, `003`, etc.
   - Zero-padded for proper sorting

3. **Timestamp Range** (optional, default: included)
   - Format: `MMmSSs-MMmSSs`
   - Example: `02m05s-02m48s` (2:05 to 2:48)
   - Helps quickly locate clip in source video

## Examples

### With Timestamps (Default)

```
why-startups-fail_001_02m05s-02m48s.mp4
product-market-fit_002_05m30s-06m15s.mp4
ai-and-automation_003_12m00s-13m20s.mp4
building-in-public_004_18m45s-20m10s.mp4
```

### Without Timestamps

```
career-advice_001.mp4
startup-journey_002.mp4
work-life-balance_003.mp4
growth-strategies_004.mp4
```

### Associated Files

Each clip has matching thumbnail and metadata files:

```
why-startups-fail_001_02m05s-02m48s.mp4              # Video clip
why-startups-fail_001_02m05s-02m48s_thumb.jpg        # Thumbnail
why-startups-fail_001_02m05s-02m48s_metadata.json    # Metadata
```

## Output Directory Structure

**Default location:** `arena/output/` (project root level)

```
arena/                              # Project root
├── cli/
├── engine/
└── output/                         # Default output
    ├── clips/
    │   ├── why-startups-fail_001_02m05s-02m48s.mp4
    │   ├── why-startups-fail_001_02m05s-02m48s_thumb.jpg
    │   ├── why-startups-fail_001_02m05s-02m48s_metadata.json
    │   ├── product-market-fit_002_05m30s-06m15s.mp4
    │   ├── product-market-fit_002_05m30s-06m15s_thumb.jpg
    │   ├── product-market-fit_002_05m30s-06m15s_metadata.json
    │   ├── ai-and-automation_003_12m00s-13m20s.mp4
    │   ├── ai-and-automation_003_12m00s-13m20s_thumb.jpg
    │   └── ai-and-automation_003_12m00s-13m20s_metadata.json
    ├── analysis_results.json
    └── .cache/
        └── video_transcript.json
```

## Benefits

### 1. **Immediately Identifiable**
- **Title comes first** - you know what the clip is about at a glance
- No need to open files to know content
- Perfect for file browsers, cloud storage, Finder/Explorer

### 2. **Topic-Based Organization**
- Similar topics naturally group together alphabetically
- All "AI" clips sort together, all "product" clips together
- Easy to find clips by subject matter

### 3. **Searchable**
- Find clips by topic: Search for "startups" or "product"
- Find clips by timestamp: Search for "02m" or "05m30s"
- Fuzzy search friendly (title is prominent)

### 4. **Sortable**
- Alphabetical sort groups by topic first
- Index number maintains creation order within topics
- Timestamp shows position in original video

### 5. **Shareable**
- Descriptive filenames look professional when shared
- Recipients immediately know what they're receiving
- Great for Slack, email, social media uploads

### 6. **Platform-Friendly**
- No special characters that break on different filesystems
- Max length ~100 chars (well under most limits)
- Works on Windows, Mac, Linux, cloud storage

## Real-World Examples

### Podcast Episodes

```
founder-mindset_001_03m15s-04m30s.mp4
raising-capital_002_08m00s-09m45s.mp4
hiring-mistakes_003_15m20s-17m10s.mp4
```

### Webinar Clips

```
demo-of-new-feature_001_05m00s-06m30s.mp4
qa-session-highlights_002_22m15s-24m00s.mp4
pricing-strategy_003_30m00s-32m15s.mp4
```

### Interview Snippets

```
how-i-got-started_001_02m00s-03m15s.mp4
biggest-lesson-learned_002_10m30s-12m00s.mp4
advice-for-beginners_003_18m45s-20m30s.mp4
```

## Sanitization Rules

Titles are sanitized for filename safety:

| Input | Output |
|-------|--------|
| `Why Startups Fail?` | `why-startups-fail` |
| `Product/Market Fit!` | `productmarket-fit` |
| `AI & Automation (2024)` | `ai-automation-2024` |
| `The #1 Mistake` | `the-1-mistake` |
| `How to 10x Your Growth` | `how-to-10x-your-growth` |

**Rules:**
- Convert to lowercase
- Remove special characters (keep alphanumeric, spaces, hyphens)
- Replace spaces with hyphens
- Collapse multiple hyphens into one
- Trim leading/trailing hyphens
- Truncate to 50 chars max, breaking at word boundaries

## Customization

Control naming via API:

```python
from arena.clipping.generator import ClipGenerator

generator = ClipGenerator(video_path)

# Generate with timestamps (default)
results = generator.generate_multiple_clips(
    segments=clips,
    output_dir="clips",
    include_timestamps=True
)

# Generate without timestamps (simpler names)
results = generator.generate_multiple_clips(
    segments=clips,
    output_dir="clips",
    include_timestamps=False
)
# Output: why-startups-fail_001.mp4

# Generate custom filename
filename = generator.generate_clip_filename(
    index=1,
    title="Why Startups Fail",
    start_time=125.5,
    end_time=168.3,
    include_timestamps=True
)
# Returns: "why-startups-fail_001_02m05s-02m48s"
```

## Migration from Old Format

**Old format (generic):**
```
clip_001.mp4
clip_002.mp4
clip_003.mp4
```

**New format (descriptive):**
```
why-startups-fail_001_02m05s-02m48s.mp4
product-market-fit_002_05m30s-06m15s.mp4
ai-and-automation_003_12m00s-13m20s.mp4
```

The new format is **much more useful** because:
- ✅ You know what each clip is about without opening it
- ✅ Files are self-documenting
- ✅ Easy to find specific clips in large collections
- ✅ Professional appearance when sharing

## Best Practices

### 1. **Keep Titles Descriptive**
- Good: `why-product-market-fit-matters`
- Bad: `interesting-clip`

### 2. **Be Specific**
- Good: `how-to-price-saas-products`
- Bad: `pricing-tips`

### 3. **Front-Load Keywords**
- Good: `startup-fundraising-mistakes`
- Bad: `mistakes-founders-make-when-fundraising`

### 4. **Use Timestamps for Source Reference**
- Helps you find the clip in the original video
- Useful for re-editing or extending clips later

### 5. **Organize by Collection**
- All clips from same video naturally group together
- Easy to batch process, upload, or share

---

**Questions or feedback?** Open an issue on GitHub!
