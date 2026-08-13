import type { Metadata } from "next";
import { DocCodeBlock } from "@/components/docs/DocCodeBlock";
import { Tabs } from "@/components/docs/Tabs";

export const metadata: Metadata = {
  title: "Installation",
};

const installTabs = [
  { id: "npm", label: "npm" },
  { id: "source", label: "Source" },
  { id: "docker", label: "Docker" },
];

export default async function DocsPage() {
  return (
    <>
      <h1>Installation</h1>
      <p>
        Arena is an AI-powered, open-source, local-first video clipping engine
        for the terminal that automatically finds the best moments in your videos
        and exports platform-ready clips for TikTok, Reels, and Shorts.
      </p>

      <div className="not-prose rounded-xl border border-arena-600/20 bg-arena-600/5 p-6 my-8">
        <p className="text-sm font-semibold text-arena-600 mb-2">
          Quick start — run without a global npm install
        </p>
        <DocCodeBlock
          lang="bash"
          code={`npx --yes @whitegodkingsley/arena-cli@0.4.2 setup
npx --yes @whitegodkingsley/arena-cli@0.4.2 process video.mp4 -n 5`}
        />
        <p className="text-xs text-muted mt-2">
          Requires Node.js 22–24, Python 3.10–3.12, and FFmpeg. Set{" "}
          <code className="text-xs bg-arena-600/10 px-1 rounded">OPENAI_API_KEY</code>{" "}
          first.
        </p>
      </div>

      <h2>Choose your install method</h2>

      <Tabs tabs={installTabs}>
        {/* npm tab */}
        <div>
          <p className="text-sm text-muted mb-4">
            The quickest way to get started. Requires Node.js 22–24, Python
            3.10–3.12, and FFmpeg/ffprobe.
          </p>

          <p className="text-sm font-medium mb-2">1. Install the stable release</p>
          <DocCodeBlock lang="bash" filename="Terminal" code={`npm install --global @whitegodkingsley/arena-cli@0.4.2
arena --version`} />

          <p className="text-sm font-medium mb-2">2. Create and verify the private runtime</p>
          <DocCodeBlock lang="bash" filename="Terminal" code={`arena setup
arena setup --check`} />

          <p className="text-sm font-medium mb-2">3. Run the configuration wizard</p>
          <DocCodeBlock lang="bash" filename="Terminal" code="arena init" />

          <div className="mt-6 rounded-lg border border-border bg-surface p-4">
            <p className="text-sm text-muted mb-2">
              <strong className="text-foreground">Permission issues?</strong>{" "}
              Configure npm to use a writable directory:
            </p>
            <DocCodeBlock lang="bash" filename="Terminal" code={`npm config set prefix "$HOME/.local"
export PATH="$HOME/.local/bin:$PATH"
npm install --global @whitegodkingsley/arena-cli@0.4.2`} />
            <p className="text-xs text-muted mt-2">
              Add the <code className="text-xs bg-surface-alt px-1 rounded">export PATH</code> line
              to your <code className="text-xs bg-surface-alt px-1 rounded">~/.bashrc</code> or{" "}
              <code className="text-xs bg-surface-alt px-1 rounded">~/.zshrc</code> to make it permanent.
            </p>
          </div>
        </div>

        {/* Source tab */}
        <div>
          <p className="text-sm text-muted mb-4">
            Clone the repo and build from source. Best for development and
            contributing.
          </p>

          <DocCodeBlock lang="bash" filename="Terminal" code={`# Clone the repository
git clone https://github.com/iamwhitegod/arena.git
cd arena

# Install CLI dependencies
cd cli && npm install

# Build TypeScript
npm run build

# Link globally for development
npm link

# Build Arena's managed Python runtime
arena setup`} />

          <p className="text-sm font-medium mb-2 mt-4">Verify</p>
          <DocCodeBlock lang="bash" filename="Terminal" code={`arena --version
arena setup --check`} />
        </div>

        {/* Docker tab */}
        <div>
          <p className="text-sm text-muted mb-4">
            Run Arena without installing any dependencies locally. Docker handles
            everything.
          </p>

          <div className="rounded-lg border border-border bg-surface p-4 mb-6">
            <p className="text-sm font-medium mb-1">Prerequisites</p>
            <p className="text-sm text-muted mb-2">
              Set your OpenAI API key before running Docker commands:
            </p>
            <DocCodeBlock lang="bash" code='export OPENAI_API_KEY="sk-..."' />
          </div>

          <p className="text-sm font-semibold mb-2">Pull and run the official image</p>
          <DocCodeBlock lang="bash" filename="Terminal" code={`docker pull whitegodkingsley/arena:0.4.2
docker volume create arena-data
docker run --rm \\
  --read-only \\
  --cap-drop ALL \\
  --security-opt no-new-privileges \\
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=2g \\
  --mount "type=bind,source=$PWD,target=/workspace" \\
  --mount type=volume,source=arena-data,target=/home/node/.arena \\
  --env OPENAI_API_KEY \\
  whitegodkingsley/arena:0.4.2 process /workspace/video.mp4 -n 5`} />
          <p className="text-xs text-muted mb-4">
            Docker selects the Linux AMD64 or ARM64 image for the host. Pin
            <code className="text-xs bg-surface-alt px-1 rounded"> 0.4.2 </code>
            in scripts; <code className="text-xs bg-surface-alt px-1 rounded">latest</code>
            is a moving stable tag. Building from source is a contributor workflow,
            not an end-user Docker installation step.
          </p>

          <p className="text-sm font-semibold mt-6 mb-3">What&apos;s included in the Docker image</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border border-border rounded-lg overflow-hidden">
              <thead>
                <tr className="bg-surface">
                  <th className="text-left px-4 py-2 font-medium border-b border-border">Dependency</th>
                  <th className="text-left px-4 py-2 font-medium border-b border-border">Version</th>
                  <th className="text-left px-4 py-2 font-medium border-b border-border">Purpose</th>
                </tr>
              </thead>
              <tbody className="text-muted">
                <tr>
                  <td className="px-4 py-2 border-b border-border font-medium text-foreground">Python</td>
                  <td className="px-4 py-2 border-b border-border">3.11</td>
                  <td className="px-4 py-2 border-b border-border">AI engine, video processing</td>
                </tr>
                <tr>
                  <td className="px-4 py-2 border-b border-border font-medium text-foreground">Node.js</td>
                  <td className="px-4 py-2 border-b border-border">22</td>
                  <td className="px-4 py-2 border-b border-border">CLI runtime</td>
                </tr>
                <tr>
                  <td className="px-4 py-2 border-b border-border font-medium text-foreground">FFmpeg</td>
                  <td className="px-4 py-2 border-b border-border">System</td>
                  <td className="px-4 py-2 border-b border-border">Video encoding, clip extraction</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="text-xs text-muted mt-2">
            <strong className="text-foreground">Note:</strong> yt-dlp is installed
            from Arena&apos;s Python requirements. yt-dlp uses the included Node.js
            runtime for YouTube&apos;s JavaScript challenge solving; Deno is not required.
          </p>
        </div>
      </Tabs>

      <h2>Install dependencies</h2>
      <p>
        If you installed via npm or source (not Docker), you need these
        dependencies on your system.
      </p>

      <h3>FFmpeg (required)</h3>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# Verify
ffmpeg -version`} />

      <h3>Python (required)</h3>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# macOS
brew install python@3.12

# Ubuntu/Debian
sudo apt install python3 python3-venv

# Verify
python3 --version`} />

      <p>
        Run <code>arena setup</code> to create Arena&apos;s isolated Python runtime,
        install yt-dlp and the engine dependencies, and verify FFmpeg. You do not
        need to install Arena packages into global Python:
      </p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`arena setup
arena setup --check`} />

      <h2>Set up your API key</h2>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# Option 1: Environment variable (add to ~/.bashrc or ~/.zshrc)
export OPENAI_API_KEY="sk-..."

# Option 2: Owner-only Arena credential store (interactive prompt)
arena config set openai_api_key

# Verify
arena config get openai_api_key`} />

      <h2>Run the setup wizard</h2>
      <DocCodeBlock lang="bash" filename="Terminal" code="arena init" />
      <p>
        The wizard helps you configure your workflow type, clip duration
        preferences, and quality vs cost balance.
      </p>

      <h2>Quick start</h2>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# Process a local video
arena process video.mp4 -n 5

# Process a YouTube URL
arena process "https://www.youtube.com/watch?v=VIDEO_ID" -n 5

# Transcribe audio
arena transcribe podcast.mp3

# Process with captions for TikTok
arena process video.mp4 --captions -p tiktok`} />
    </>
  );
}
