import type { Metadata } from "next";
import { DocCodeBlock } from "@/components/docs/DocCodeBlock";

export const metadata: Metadata = {
  title: "Editorial System",
};

export default async function EditorialPage() {
  return (
    <>
      <h1>4-Layer Editorial System</h1>
      <p>
        Arena&apos;s core differentiator is a 4-layer editorial system that
        produces standalone, high-quality clips while other AI tools output
        incomplete thoughts. Every clip passes through all four layers.
      </p>

      <h2>Layer 1: Hook &amp; Moment Detection</h2>
      <p>
        The engine scans the full transcript in sliding 2-minute windows,
        detecting approximately 40 &quot;seeds&quot; — compelling moments like claims,
        insights, hooks, stories, and conversational peaks. Seeds are
        deduplicated by time proximity and text similarity to produce ~25 raw
        candidate windows.
      </p>
      <DocCodeBlock
        lang="bash"
        filename="Terminal"
        code={`# Enable layer export to see Layer 1 output
arena process video.mp4 --export-layers

# Check: output/editorial_layers/layer1_moments.json`}
      />

      <h2>Layer 2: Thought Boundary Expansion</h2>
      <p>
        Raw clip windows are expanded outward to natural thought boundaries.
        Each candidate is analyzed for its <strong>premise</strong> (setup/context),{" "}
        <strong>claim</strong> (the core point), and <strong>resolution</strong>{" "}
        (conclusion or punchline). The boundaries are adjusted so clips capture
        the complete thought arc — premise to resolution.
      </p>
      <p>
        This prevents the common AI clipping problem of clips that start or end
        mid-sentence or mid-thought.
      </p>

      <h2>Layer 3: Standalone Quality Gate</h2>
      <p>
        The strictest layer. A validation agent checks whether each clip can
        stand completely alone on a social media feed without surrounding
        context. It checks for:
      </p>
      <ul>
        <li>Unresolved pronouns (&quot;it&quot;, &quot;this&quot;, &quot;that&quot; without clear referents)</li>
        <li>Missing subject introductions</li>
        <li>Dangling references to earlier conversation</li>
        <li>Incomplete premises or resolutions</li>
        <li>Structural issues requiring significant adjustments</li>
      </ul>
      <p>
        Each clip receives a <strong>standalone score</strong> from 0–10. Only
        clips scoring 7+ pass. Typical pass rate is around{" "}
        <strong>7–10%</strong> of candidates.
      </p>

      <h3>Debugging rejections</h3>
      <DocCodeBlock
        lang="bash"
        filename="Terminal"
        code={`# Export layer data
arena process video.mp4 --export-layers

# Check rejection reasons
cat output/editorial_layers/layer3_validated.json | \\
  jq '.[] | select(.verdict=="REJECT") | {thought_id, rejection_reason, standalone_score}'

# Check pass rate
cat output/editorial_layers/layer3_validated.json | \\
  jq '[.[] | select(.verdict=="PASS")] | length'`}
      />

      <h3>Common rejection reasons</h3>
      <table>
        <thead>
          <tr><th>Reason</th><th>Meaning</th></tr>
        </thead>
        <tbody>
          <tr><td><code>duration_constraint</code></td><td>Clip too short or long after boundary adjustment</td></tr>
          <tr><td><code>missing_premise</code></td><td>Doesn&apos;t explain what it&apos;s about</td></tr>
          <tr><td><code>dangling_reference</code></td><td>Uses pronouns without defining them</td></tr>
          <tr><td><code>incomplete_resolution</code></td><td>Cuts off mid-thought</td></tr>
          <tr><td><code>structural_issue</code></td><td>Would need 15+ seconds of adjustment to fix</td></tr>
        </tbody>
      </table>

      <h2>Layer 4: Viral Packaging</h2>
      <p>
        Clips that pass Layer 3 are packaged with professional metadata for
        social media distribution:
      </p>
      <ul>
        <li>Magnetic, high-CTR titles</li>
        <li>Detailed keyword summaries</li>
        <li>Platform-specific hashtags</li>
        <li>Hook text for captions</li>
      </ul>

      <h2>Hybrid scoring</h2>
      <p>
        Arena combines two signals to rank clips:
      </p>
      <ul>
        <li><strong>AI content score</strong> — GPT-based semantic analysis of content quality</li>
        <li><strong>Audio energy score</strong> — RMS amplitude and spectral centroid analysis detecting enthusiastic delivery</li>
      </ul>
      <p>
        Final score = <code>ai_score × 0.7 + energy_score × 0.3</code>. This
        ensures clips have both great content <em>and</em> dynamic delivery.
      </p>

      <h2>Semantic deduplication</h2>
      <p>
        Layer 4 also deduplicates clips using{" "}
        <code>text-embedding-3-small</code> cosine similarity. If multiple clips
        cover the same topic, the best variant per cluster is selected,
        preventing repetitive output.
      </p>

      <h2>Checkpointing</h2>
      <p>
        The <code>CheckpointManager</code> saves intermediate results between
        layers. If a run fails mid-pipeline (e.g., rate limit or network error),
        Arena resumes from the last completed layer instead of restarting. Job
        ID is a hash of the first 500 characters of the transcript.
      </p>

      <h2>Cost breakdown</h2>
      <table>
        <thead>
          <tr><th>Layer</th><th>Model</th><th>Typical cost</th></tr>
        </thead>
        <tbody>
          <tr><td>Transcription</td><td>Whisper API</td><td>~$0.006/min</td></tr>
          <tr><td>Layer 1–2</td><td>Configurable (<code>--editorial-model</code>)</td><td>~$0.05–0.20</td></tr>
          <tr><td>Layer 3–4</td><td>Always <code>gpt-4o-mini</code></td><td>~$0.03–0.05</td></tr>
          <tr><td>Deduplication</td><td><code>text-embedding-3-small</code></td><td>&lt;$0.01</td></tr>
        </tbody>
      </table>
      <p>
        Total for a 30-minute video: <strong>$0.15–0.25</strong> with{" "}
        <code>gpt-4o-mini</code>, or <strong>$0.40–0.60</strong> with{" "}
        <code>gpt-4o</code>.
      </p>
    </>
  );
}
