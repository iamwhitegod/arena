import type { Metadata } from "next";
import { DocCodeBlock } from "@/components/docs/DocCodeBlock";

export const metadata: Metadata = {
  title: "Workflows",
};

export default async function WorkflowsPage() {
  return (
    <>
      <h1>Workflows &amp; Examples</h1>
      <p>
        Arena supports flexible workflows from quick one-command runs to
        multi-step production pipelines.
      </p>

      <h2>Quick clips</h2>
      <p>The simplest workflow — one command, done.</p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`arena process video.mp4 --editorial-model gpt-4o-mini -n 5`} />
      <p><strong>Cost:</strong> ~$0.20 | <strong>Time:</strong> 5–8 minutes</p>

      <h2>Review before generate</h2>
      <p>Analyze first, review the moments, then generate only the best clips.</p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# Step 1: Analyze (fast, cheap)
arena analyze video.mp4 -n 10 -o moments.json

# Step 2: Review
cat moments.json | jq '.clips[] | {id, title, duration, standalone_score}'

# Step 3: Generate only the best
arena generate video.mp4 moments.json --select 1,3,5,7`} />

      <h2>Multi-platform distribution</h2>
      <p>Generate clips once, format for every platform.</p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# Step 1: Generate clips with captions
arena process video.mp4 -n 5 --captions

# Step 2: Format for each platform
arena format output/clips/ -p tiktok -o social/tiktok/
arena format output/clips/ -p instagram-reels -o social/reels/
arena format output/clips/ -p youtube-shorts -o social/shorts/
arena format output/clips/ -p youtube -o social/youtube/

# Result: 5 clips × 4 platforms = 20 optimized videos`} />

      <h2>Process from URL</h2>
      <p>Process content directly from YouTube, Vimeo, Twitter, and 1000+ sites.</p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# YouTube video
arena process "https://www.youtube.com/watch?v=VIDEO_ID" -n 5

# With browser cookies (if authentication required)
arena process "https://www.youtube.com/watch?v=VIDEO_ID" --cookies-from-browser chrome

# Vimeo
arena transcribe https://vimeo.com/123456789

# Any yt-dlp supported site
arena process "https://twitter.com/user/status/123456789" -n 3`} />

      <h2>Content creator pipeline</h2>
      <p>Short-form clips optimized for social media.</p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`arena process video.mp4 \\
  --editorial-model gpt-4o-mini \\
  -n 3 \\
  --min 15 \\
  --max 30 \\
  --captions \\
  -p tiktok`} />

      <h2>Podcast highlights</h2>
      <p>Extract the best moments from long-form podcast episodes.</p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`arena process podcast-episode.mp4 \\
  --editorial-model gpt-4o-mini \\
  -n 8 \\
  --min 60 \\
  --max 120

# Format for YouTube and LinkedIn
arena format output/clips/ -p youtube -o social/youtube/
arena format output/clips/ -p linkedin -o social/linkedin/`} />

      <h2>Course creator</h2>
      <p>Extract educational snippets with captions.</p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`arena process lecture.mp4 \\
  -n 8 \\
  --min 45 \\
  --max 90 \\
  --captions \\
  --caption-color yellow`} />

      <h2>Iterative refinement</h2>
      <p>Experiment with different parameters using cached transcripts.</p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# Initial run (creates transcript cache)
arena process video.mp4

# Try different clip counts (reuses cached transcript — free)
arena process video.mp4 -n 3
arena process video.mp4 -n 10

# Try different durations
arena process video.mp4 --min 20 --max 45
arena process video.mp4 --min 45 --max 90`} />

      <h2>Debug quality issues</h2>
      <p>Export editorial layer data to understand why clips were rejected.</p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# Export layer data
arena process video.mp4 --export-layers

# Check rejection reasons
cat output/editorial_layers/layer3_validated.json | \\
  jq '.[] | select(.verdict=="REJECT") | {thought_id, rejection_reason}'

# Check pass rate
cat output/editorial_layers/layer3_validated.json | \\
  jq '[.[] | select(.verdict=="PASS")] | length'`} />

      <h2>Batch processing</h2>
      <p>Process an entire directory of videos.</p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`for video in videos/*.mp4; do
  echo "Processing: $video"
  arena process "$video" \\
    --editorial-model gpt-4o-mini \\
    -n 5 \\
    -o "output/$(basename $video .mp4)"
done`} />

      <h2>Content repurposing pipeline</h2>
      <p>Turn a single long-form video into a week&apos;s worth of social media content.</p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# Step 1: Transcribe and analyze
arena transcribe webinar.mp4 -o transcript.json
arena analyze webinar.mp4 --transcript transcript.json -n 20 -o analysis.json

# Step 2: Review and select
cat analysis.json | jq '.clips[] | {id, title, duration}' | less

# Step 3: Generate selected clips
arena generate webinar.mp4 analysis.json --select 1,3,5,7,9,11,13 -o clips/

# Step 4: Format for platforms
arena format clips/ -p tiktok --crop smart -o social/tiktok/
arena format clips/ -p instagram-reels --crop smart -o social/reels/
arena format clips/ -p linkedin --pad blur -o social/linkedin/
arena format clips/ -p youtube -o social/youtube/

# Result: 1 webinar → 7 clips × 4 platforms = 28 social posts`} />

      <h2>Docker workflow</h2>
      <p>Run Arena without installing dependencies locally.</p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# Using Docker Compose
docker compose run arena process video.mp4 -n 5
docker compose run arena format output/clips/ -p tiktok

# Using Docker directly
docker run -v $(pwd):/workspace \\
  -e OPENAI_API_KEY=$OPENAI_API_KEY \\
  whitegodkingsley/arena process video.mp4 -n 5`} />
    </>
  );
}
