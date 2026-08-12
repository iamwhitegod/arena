import type { Metadata } from "next";
import { DocCodeBlock } from "@/components/docs/DocCodeBlock";

export const metadata: Metadata = {
  title: "Platform Formatting",
};

export default async function FormattingPage() {
  return (
    <>
      <h1>Platform Formatting</h1>
      <p>
        Format video clips for any social media platform with optimal aspect
        ratios, resolutions, and file size limits.
      </p>

      <h2>Supported platforms</h2>
      <table>
        <thead>
          <tr>
            <th>Platform</th>
            <th>Resolution</th>
            <th>Ratio</th>
            <th>Max Duration</th>
            <th>Max Size</th>
          </tr>
        </thead>
        <tbody>
          <tr><td><code>tiktok</code></td><td>1080x1920</td><td>9:16</td><td>180s</td><td>287MB</td></tr>
          <tr><td><code>instagram-reels</code></td><td>1080x1920</td><td>9:16</td><td>90s</td><td>100MB</td></tr>
          <tr><td><code>youtube-shorts</code></td><td>1080x1920</td><td>9:16</td><td>60s</td><td>100MB</td></tr>
          <tr><td><code>youtube</code></td><td>1920x1080</td><td>16:9</td><td>Unlimited</td><td>256GB</td></tr>
          <tr><td><code>instagram-feed</code></td><td>1080x1080</td><td>1:1</td><td>60s</td><td>100MB</td></tr>
          <tr><td><code>twitter</code></td><td>1280x720</td><td>16:9</td><td>140s</td><td>512MB</td></tr>
          <tr><td><code>linkedin</code></td><td>1920x1080</td><td>16:9</td><td>600s</td><td>5GB</td></tr>
        </tbody>
      </table>

      <h2>Usage</h2>
      <DocCodeBlock lang="bash" filename="Terminal" code={`arena format <input> -p <platform> [options]`} />

      <h3>Options</h3>
      <table>
        <thead>
          <tr><th>Option</th><th>Description</th><th>Default</th></tr>
        </thead>
        <tbody>
          <tr><td><code>-p, --platform</code></td><td>Target platform (required)</td><td>-</td></tr>
          <tr><td><code>-o, --output &lt;dir&gt;</code></td><td>Output directory</td><td>auto</td></tr>
          <tr><td><code>--crop &lt;strategy&gt;</code></td><td><code>center</code>, <code>smart</code>, <code>top</code>, <code>bottom</code></td><td><code>center</code></td></tr>
          <tr><td><code>--pad &lt;strategy&gt;</code></td><td><code>blur</code>, <code>black</code>, <code>white</code>, <code>color</code></td><td><code>blur</code></td></tr>
          <tr><td><code>--pad-color &lt;hex&gt;</code></td><td>Custom padding color</td><td><code>#000000</code></td></tr>
          <tr><td><code>--no-quality</code></td><td>Disable high quality encoding</td><td><code>false</code></td></tr>
        </tbody>
      </table>

      <h2>Crop strategies</h2>
      <p>Used when the source video is wider than the target aspect ratio (e.g., 16:9 to 9:16):</p>
      <ul>
        <li><strong>center</strong> — Crop from center (default, safe choice)</li>
        <li><strong>smart</strong> — Slight bias toward center-right (better for faces)</li>
        <li><strong>top</strong> — Crop from top edge</li>
        <li><strong>bottom</strong> — Crop from bottom edge</li>
      </ul>

      <h2>Pad strategies</h2>
      <p>Used when the source video is taller than the target aspect ratio:</p>
      <ul>
        <li><strong>blur</strong> — Gaussian-blurred background (looks professional)</li>
        <li><strong>black</strong> — Classic black bars</li>
        <li><strong>white</strong> — White bars</li>
        <li><strong>color</strong> — Custom color (use <code>--pad-color</code>)</li>
      </ul>

      <h2>Examples</h2>

      <h3>Single clip formatting</h3>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# Format for TikTok
arena format clip.mp4 -p tiktok -o tiktok/

# Format for Instagram with smart cropping
arena format clip.mp4 -p instagram-reels --crop smart -o reels/

# Format for YouTube with blur background
arena format clip.mp4 -p youtube --pad blur -o youtube/

# Custom padding color
arena format clip.mp4 -p instagram-feed --pad color --pad-color #FF5733`} />

      <h3>Batch formatting</h3>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# Format all clips in a directory
arena format clips/ -p tiktok -o formatted/tiktok/
arena format clips/ -p instagram-reels --crop smart -o formatted/reels/
arena format clips/ -p youtube-shorts -o formatted/shorts/`} />

      <h3>Multi-platform distribution</h3>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# Generate clips once
arena process video.mp4 -n 5 --captions

# Format for every platform
arena format output/clips/ -p tiktok -o social/tiktok/
arena format output/clips/ -p instagram-reels -o social/reels/
arena format output/clips/ -p youtube-shorts -o social/shorts/
arena format output/clips/ -p youtube -o social/youtube/
arena format output/clips/ -p instagram-feed -o social/instagram/

# Result: 5 clips × 5 platforms = 25 optimized videos`} />

      <h2>Tips</h2>
      <ul>
        <li>Use <code>--crop smart</code> for videos with faces or people</li>
        <li>Use <code>--pad blur</code> for professional letterboxing</li>
        <li>Format <em>after</em> generating clips to save processing time</li>
        <li>Check file size warnings if clips exceed platform limits</li>
        <li>Test one clip first before batch formatting</li>
      </ul>
    </>
  );
}
