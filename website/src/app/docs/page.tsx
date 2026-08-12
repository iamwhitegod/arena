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
        Arena is an AI-powered video clip generation tool. It runs locally on
        your machine and uses OpenAI for AI analysis.
      </p>

      <div className="not-prose rounded-xl border border-arena-200 bg-arena-50 p-6 my-8">
        <p className="text-sm font-semibold text-arena-800 mb-2">
          Quick start — try it without installing
        </p>
        <DocCodeBlock
          lang="bash"
          code="npx @whitegodkingsley/arena-cli process video.mp4 -n 5"
        />
        <p className="text-xs text-arena-700 mt-2">
          Requires Node.js 18+, Python 3.9+, and FFmpeg. Set{" "}
          <code className="text-xs bg-arena-100 px-1 rounded">OPENAI_API_KEY</code>{" "}
          first.
        </p>
      </div>

      <h2>Choose your install method</h2>

      <Tabs tabs={installTabs}>
        {/* npm tab */}
        <div>
          <p className="text-sm text-muted mb-4">
            The quickest way to get started. Requires Node.js 18+.
          </p>

          <p className="text-sm font-medium mb-2">1. Install globally</p>
          <DocCodeBlock lang="bash" filename="Terminal" code="npm install -g @whitegodkingsley/arena-cli" />

          <p className="text-sm font-medium mb-2">2. Verify installation</p>
          <DocCodeBlock lang="bash" filename="Terminal" code="arena --version" />

          <p className="text-sm font-medium mb-2">3. Run setup wizard</p>
          <DocCodeBlock lang="bash" filename="Terminal" code="arena init" />

          <div className="mt-6 rounded-lg border border-border bg-surface p-4">
            <p className="text-sm text-muted mb-2">
              <strong className="text-foreground">Permission issues?</strong>{" "}
              Configure npm to use a writable directory:
            </p>
            <DocCodeBlock lang="bash" filename="Terminal" code={`mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
export PATH=~/.npm-global/bin:$PATH
npm install -g @whitegodkingsley/arena-cli`} />
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

# Install Python engine dependencies
cd ../engine
pip install -r requirements.txt`} />

          <p className="text-sm font-medium mb-2 mt-4">Verify</p>
          <DocCodeBlock lang="bash" filename="Terminal" code="arena --version" />
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

          <p className="text-sm font-semibold mb-2">
            Option 1: Docker Compose (recommended)
          </p>
          <DocCodeBlock lang="bash" filename="Terminal" code={`git clone https://github.com/iamwhitegod/arena.git
cd arena
docker compose build
docker compose run arena process video.mp4 -n 5`} />
          <p className="text-xs text-muted mb-4">
            Docker Compose automatically mounts your current directory and passes
            your <code className="text-xs bg-surface-alt px-1 rounded">OPENAI_API_KEY</code>.
          </p>

          <p className="text-sm font-semibold mb-2">Option 2: Docker Hub</p>
          <DocCodeBlock lang="bash" filename="Terminal" code={`docker pull whitegodkingsley/arena:latest
docker run -v $(pwd):/workspace \\
  -e OPENAI_API_KEY=$OPENAI_API_KEY \\
  whitegodkingsley/arena process video.mp4 -n 5`} />

          <p className="text-sm font-semibold mb-2">Option 3: Build yourself</p>
          <DocCodeBlock lang="bash" filename="Terminal" code={`docker build -t arena .
docker run -v $(pwd):/workspace \\
  -e OPENAI_API_KEY=$OPENAI_API_KEY \\
  arena process video.mp4`} />

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
                  <td className="px-4 py-2 border-b border-border">3.10</td>
                  <td className="px-4 py-2 border-b border-border">AI engine, video processing</td>
                </tr>
                <tr>
                  <td className="px-4 py-2 border-b border-border font-medium text-foreground">Node.js</td>
                  <td className="px-4 py-2 border-b border-border">20</td>
                  <td className="px-4 py-2 border-b border-border">CLI runtime</td>
                </tr>
                <tr>
                  <td className="px-4 py-2 border-b border-border font-medium text-foreground">FFmpeg</td>
                  <td className="px-4 py-2 border-b border-border">System</td>
                  <td className="px-4 py-2 border-b border-border">Video encoding, clip extraction</td>
                </tr>
                <tr>
                  <td className="px-4 py-2 font-medium text-foreground">Deno</td>
                  <td className="px-4 py-2">Latest</td>
                  <td className="px-4 py-2">YouTube URL downloads</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="text-xs text-muted mt-2">
            <strong className="text-foreground">Note:</strong> yt-dlp is not
            pre-installed in the Docker image. URL support uses Deno. To add
            yt-dlp, extend the Dockerfile with{" "}
            <code className="text-xs bg-surface-alt px-1 rounded">RUN pip install yt-dlp</code>.
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
brew install python3

# Ubuntu/Debian
sudo apt install python3 python3-pip

# Install Arena engine dependencies
cd engine && pip install -r requirements.txt

# Verify
python3 --version`} />

      <h3>yt-dlp (optional, for URL support)</h3>
      <DocCodeBlock lang="bash" filename="Terminal" code="pip install yt-dlp" />

      <h3>Deno (optional, for YouTube downloads)</h3>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# macOS
brew install deno

# Other platforms
curl -fsSL https://deno.land/install.sh | sh`} />

      <p>
        Or skip manual dependency setup entirely — run{" "}
        <code>arena setup</code> to auto-detect and install missing
        dependencies:
      </p>
      <DocCodeBlock lang="bash" filename="Terminal" code="arena setup" />

      <h2>Set up your API key</h2>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# Option 1: Environment variable (add to ~/.bashrc or ~/.zshrc)
export OPENAI_API_KEY="sk-..."

# Option 2: Via Arena config
arena config set openai_api_key "sk-..."

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
