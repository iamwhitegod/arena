import type { Metadata } from "next";
import { DocCodeBlock } from "@/components/docs/DocCodeBlock";

export const metadata: Metadata = {
  title: "Commands",
};

export default async function CommandsPage() {
  return (
    <>
      <h1>Command Reference</h1>
      <p>
        Arena provides 11 commands for flexible video clip generation workflows.
        All commands that accept a video file also accept audio files and URLs.
      </p>

      <table>
        <thead>
          <tr>
            <th>Command</th>
            <th>Purpose</th>
          </tr>
        </thead>
        <tbody>
          <tr><td><code>arena init</code></td><td>Interactive setup wizard</td></tr>
          <tr><td><code>arena process</code></td><td>All-in-one clip generation</td></tr>
          <tr><td><code>arena transcribe</code></td><td>Transcription only</td></tr>
          <tr><td><code>arena analyze</code></td><td>Find moments without generating clips</td></tr>
          <tr><td><code>arena generate</code></td><td>Generate clips from analysis</td></tr>
          <tr><td><code>arena format</code></td><td>Format clips for social platforms</td></tr>
          <tr><td><code>arena detect-scenes</code></td><td>Detect visual scene changes</td></tr>
          <tr><td><code>arena config</code></td><td>Manage configuration</td></tr>
          <tr><td><code>arena extract-audio</code></td><td>Extract audio from video</td></tr>
          <tr><td><code>arena setup</code></td><td>Install dependencies automatically</td></tr>
          <tr><td><code>arena diagnose</code></td><td>System diagnostics</td></tr>
        </tbody>
      </table>

      <h2>arena process</h2>
      <p>The all-in-one command. Transcribes, analyzes, and generates clips in a single pipeline.</p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`arena process <video-or-url> [options]`} />

      <h3>Options</h3>
      <table>
        <thead>
          <tr><th>Option</th><th>Description</th><th>Default</th></tr>
        </thead>
        <tbody>
          <tr><td><code>-o, --output &lt;dir&gt;</code></td><td>Output directory</td><td><code>.arena/output</code></td></tr>
          <tr><td><code>-n, --num-clips &lt;number&gt;</code></td><td>Target number of clips</td><td><code>5</code></td></tr>
          <tr><td><code>--min &lt;seconds&gt;</code></td><td>Minimum clip duration</td><td><code>30</code></td></tr>
          <tr><td><code>--max &lt;seconds&gt;</code></td><td>Maximum clip duration</td><td><code>90</code></td></tr>
          <tr><td><code>--fast</code></td><td>Stream copy mode (10x faster, no re-encoding)</td><td><code>false</code></td></tr>
          <tr><td><code>--captions</code></td><td>Burn subtitles into clips</td><td><code>false</code></td></tr>
          <tr><td><code>-p, --platform</code></td><td>Target platform for formatting</td><td>-</td></tr>
          <tr><td><code>--editorial-model</code></td><td><code>gpt-4o</code> or <code>gpt-4o-mini</code></td><td><code>gpt-4o</code></td></tr>
          <tr><td><code>--no-cache</code></td><td>Ignore cached transcript</td><td><code>false</code></td></tr>
          <tr><td><code>--padding &lt;seconds&gt;</code></td><td>Padding before/after clips</td><td><code>0.5</code></td></tr>
          <tr><td><code>--export-editorial-layers</code></td><td>Export intermediate layer results</td><td><code>false</code></td></tr>
          <tr><td><code>--cookies-from-browser</code></td><td>Browser cookies for YouTube</td><td>-</td></tr>
        </tbody>
      </table>

      <h3>Examples</h3>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# Local video file
arena process video.mp4

# YouTube URL
arena process "https://www.youtube.com/watch?v=VIDEO_ID" -n 5

# With captions for TikTok
arena process video.mp4 --captions -p tiktok

# Cost-optimized
arena process video.mp4 --editorial-model gpt-4o-mini -n 5

# Fast mode (stream copy)
arena process video.mp4 --fast

# Audio file
arena process podcast.mp3 -n 5

# YouTube with browser cookies
arena process "https://www.youtube.com/watch?v=VIDEO_ID" --cookies-from-browser chrome`} />

      <h2>arena transcribe</h2>
      <p>Transcribe video or audio without analysis or clip generation. Supports local files and URLs.</p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`arena transcribe <video-or-url> [options]`} />

      <h3>Options</h3>
      <table>
        <thead>
          <tr><th>Option</th><th>Description</th><th>Default</th></tr>
        </thead>
        <tbody>
          <tr><td><code>-o, --output &lt;file&gt;</code></td><td>Output transcript path</td><td><code>transcript.json</code></td></tr>
          <tr><td><code>--no-cache</code></td><td>Force re-transcription</td><td><code>false</code></td></tr>
          <tr><td><code>--cookies-from-browser</code></td><td>Browser cookies for YouTube</td><td>-</td></tr>
        </tbody>
      </table>

      <h3>Examples</h3>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# Transcribe local video
arena transcribe video.mp4

# Transcribe YouTube URL
arena transcribe "https://www.youtube.com/watch?v=VIDEO_ID" -o transcript.json

# Transcribe audio file
arena transcribe podcast.mp3 -o transcript.json

# Force re-transcription
arena transcribe video.mp4 --no-cache`} />

      <h2>arena analyze</h2>
      <p>Analyze video and identify clips without generating video files. Useful for reviewing moments before committing to generation.</p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`arena analyze <video> [options]`} />

      <h3>Options</h3>
      <table>
        <thead>
          <tr><th>Option</th><th>Description</th><th>Default</th></tr>
        </thead>
        <tbody>
          <tr><td><code>-o, --output &lt;file&gt;</code></td><td>Output analysis path</td><td><code>analysis.json</code></td></tr>
          <tr><td><code>-n, --num-clips</code></td><td>Number of clips to analyze</td><td><code>5</code></td></tr>
          <tr><td><code>--min / --max</code></td><td>Duration constraints</td><td><code>30 / 90</code></td></tr>
          <tr><td><code>--editorial-model</code></td><td>Model for analysis</td><td><code>gpt-4o</code></td></tr>
          <tr><td><code>--transcript &lt;file&gt;</code></td><td>Use existing transcript</td><td>-</td></tr>
        </tbody>
      </table>

      <h3>Examples</h3>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# Analyze and find 10 potential clips
arena analyze video.mp4 -n 10 -o moments.json

# Use existing transcript
arena analyze video.mp4 --transcript transcript.json

# Cost-optimized analysis
arena analyze video.mp4 --editorial-model gpt-4o-mini`} />

      <h2>arena generate</h2>
      <p>Generate video clips from an existing analysis JSON file.</p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`arena generate <video> <analysis> [options]`} />

      <h3>Options</h3>
      <table>
        <thead>
          <tr><th>Option</th><th>Description</th><th>Default</th></tr>
        </thead>
        <tbody>
          <tr><td><code>-o, --output &lt;dir&gt;</code></td><td>Output directory</td><td><code>output/clips</code></td></tr>
          <tr><td><code>--select &lt;1,3,5&gt;</code></td><td>Generate specific clips by index</td><td>all</td></tr>
          <tr><td><code>--fast</code></td><td>Stream copy mode</td><td><code>false</code></td></tr>
          <tr><td><code>--padding &lt;seconds&gt;</code></td><td>Padding before/after</td><td><code>0.5</code></td></tr>
        </tbody>
      </table>

      <h3>Examples</h3>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# Generate all clips from analysis
arena generate video.mp4 analysis.json

# Generate only clips 1, 3, and 5
arena generate video.mp4 analysis.json --select 1,3,5

# Fast generation with stream copy
arena generate video.mp4 analysis.json --fast`} />

      <h2>arena format</h2>
      <p>
        Format video clips for specific social media platforms. See the{" "}
        <a href="/docs/formatting">Platform Formatting</a> page for full details.
      </p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`arena format <input> -p <platform> [options]`} />

      <h3>Examples</h3>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# Format for TikTok
arena format clip.mp4 -p tiktok -o tiktok/

# Batch format directory
arena format clips/ -p instagram-reels --crop smart -o reels/

# With blur background
arena format video.mp4 -p youtube --pad blur -o youtube/`} />

      <h2>arena detect-scenes</h2>
      <p>Analyze and output visual scene change boundaries.</p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`arena detect-scenes <video> [options]`} />

      <h3>Examples</h3>
      <DocCodeBlock lang="bash" filename="Terminal" code={`arena detect-scenes video.mp4
arena detect-scenes video.mp4 --threshold 0.35`} />

      <h2>arena config</h2>
      <p>View and manage Arena configuration.</p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`arena config                        # View current config
arena config set <key> <value>      # Set config value
arena config get <key>              # Get specific value
arena config reset                  # Reset to defaults`} />

      <h3>Common config keys</h3>
      <table>
        <thead>
          <tr><th>Key</th><th>Description</th></tr>
        </thead>
        <tbody>
          <tr><td><code>openai_api_key</code></td><td>OpenAI API key</td></tr>
          <tr><td><code>whisper_mode</code></td><td>Transcription mode (<code>api</code> or <code>local</code>)</td></tr>
          <tr><td><code>clip_duration</code></td><td>Default duration range</td></tr>
          <tr><td><code>output_format</code></td><td>Video output format</td></tr>
        </tbody>
      </table>

      <h2>arena extract-audio</h2>
      <p>Extract audio from video or URL in various formats.</p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`arena extract-audio <video-or-url> [options]`} />

      <h3>Options</h3>
      <table>
        <thead>
          <tr><th>Option</th><th>Description</th><th>Default</th></tr>
        </thead>
        <tbody>
          <tr><td><code>-o, --output &lt;file&gt;</code></td><td>Output audio path</td><td>auto</td></tr>
          <tr><td><code>--format</code></td><td><code>mp3</code>, <code>wav</code>, <code>aac</code>, <code>flac</code></td><td><code>mp3</code></td></tr>
          <tr><td><code>--bitrate</code></td><td>Audio bitrate</td><td><code>192k</code></td></tr>
          <tr><td><code>--sample-rate</code></td><td>Sample rate in Hz</td><td>auto</td></tr>
          <tr><td><code>--mono</code></td><td>Convert to mono</td><td><code>false</code></td></tr>
        </tbody>
      </table>

      <h3>Examples</h3>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# Extract to MP3
arena extract-audio video.mp4

# High-quality WAV
arena extract-audio video.mp4 --format wav -o audio.wav

# Mono for speech processing
arena extract-audio video.mp4 --mono --bitrate 128k`} />

      <h2>arena setup</h2>
      <p>Automatically install and verify all required dependencies.</p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`arena setup`} />

      <h2>arena diagnose</h2>
      <p>Run system diagnostics to check your environment.</p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`arena diagnose`} />
    </>
  );
}
