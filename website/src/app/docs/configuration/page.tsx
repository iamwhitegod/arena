import type { Metadata } from "next";
import { DocCodeBlock } from "@/components/docs/DocCodeBlock";

export const metadata: Metadata = {
  title: "Configuration",
};

export default async function ConfigurationPage() {
  return (
    <>
      <h1>Configuration</h1>
      <p>
        Arena uses a layered configuration system. Global settings apply
        everywhere, while project-level settings override them for specific
        directories.
      </p>

      <h2>Global config</h2>
      <p>
        Stored at <code>~/.arena/config.json</code>. Applies to all Arena
        projects.
      </p>
      <DocCodeBlock
        lang="json"
        filename="~/.arena/config.json"
        code={`{
  "whisper_mode": "api",
  "clip_duration": [30, 90],
  "output_format": "mp4",
  "subtitle_style": {
    "font": "Arial",
    "size": 24,
    "color": "white",
    "bg_color": "black",
    "position": "bottom"
  }
}`}
      />

      <h3>Managing via CLI</h3>
      <DocCodeBlock
        lang="bash"
        filename="Terminal"
        code={`# View current config
arena config

# Set a normal value
arena config set output_format mp4

# Store an API key with an interactive hidden prompt
arena config set openai_api_key

# Get a specific value
arena config get output_format

# Reset to defaults
arena config reset`}
      />

      <h2>Project config</h2>
      <p>
        Stored at <code>.arena/config.json</code> in your project directory.
        Auto-generated when you run <code>arena init</code> or process a video.
      </p>
      <DocCodeBlock
        lang="json"
        filename=".arena/config.json"
        code={`{
  "video_path": "/path/to/video.mp4",
  "created_at": "2026-01-12T19:52:00Z",
  "preferences": {
    "clip_count": 10,
    "focus_topics": ["startups", "marketing"]
  }
}`}
      />

      <h2>Environment variables</h2>
      <table>
        <thead>
          <tr><th>Variable</th><th>Description</th><th>Required</th></tr>
        </thead>
        <tbody>
          <tr><td><code>OPENAI_API_KEY</code></td><td>OpenAI API key for AI analysis and transcription</td><td>Yes</td></tr>
          <tr><td><code>ARENA_HOME</code></td><td>Override the Arena runtime, config, log, and cache directory</td><td>No</td></tr>
          <tr><td><code>ARENA_PYTHON</code></td><td>Choose the Python interpreter used by <code>arena setup</code></td><td>No</td></tr>
          <tr><td><code>ARENA_SETUP_TIMEOUT_MINUTES</code></td><td>Extend setup&apos;s package-install timeout</td><td>No</td></tr>
        </tbody>
      </table>

      <DocCodeBlock
        lang="bash"
        filename="Terminal"
        code={`# Set in your shell profile (~/.bashrc or ~/.zshrc)
export OPENAI_API_KEY="sk-your-key-here"

# Or use Arena's interactive owner-only credential store
arena config set openai_api_key`}
      />

      <h2>Workspace cache</h2>
      <p>
        Arena stores project configuration in <code>.arena/</code>, downloads in
        the Arena home cache, and generated artifacts under the selected output
        directory.
      </p>
      <DocCodeBlock
        lang="text"
        filename="Output"
        code={`.arena/
└── config.json              # Project configuration

output/
├── clips/                   # Generated video clips and metadata
└── .cache/                  # Reusable transcript/audio intermediates`}
      />
      <p>
        Use <code>--no-cache</code> to force re-transcription and ignore cached
        results.
      </p>

      <h2>Logs</h2>
      <p>
        Arena writes rotating logs beneath the Arena home directory (normally
        <code>~/.arena/logs/</code>). Use <code>--debug</code> for verbose output.
      </p>

      <h2>Cost optimization</h2>
      <table>
        <thead>
          <tr><th>Model</th><th>Cost per video</th><th>Quality</th></tr>
        </thead>
        <tbody>
          <tr><td><code>gpt-4o-mini</code> (recommended)</td><td>~$0.15–0.25</td><td>Near-identical to gpt-4o</td></tr>
          <tr><td><code>gpt-4o</code></td><td>~$0.40–0.60</td><td>Premium</td></tr>
        </tbody>
      </table>
      <p>Tips to reduce costs:</p>
      <ul>
        <li>Use <code>--editorial-model gpt-4o-mini</code> (60% cheaper)</li>
        <li>Analyze first, generate later (reuse analysis)</li>
        <li>Cache transcripts (reuse for multiple runs)</li>
        <li>Use selective generation (<code>--select 1,3,5</code>)</li>
      </ul>
    </>
  );
}
