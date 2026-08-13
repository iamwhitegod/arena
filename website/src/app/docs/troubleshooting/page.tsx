import type { Metadata } from "next";
import { DocCodeBlock } from "@/components/docs/DocCodeBlock";

export const metadata: Metadata = {
  title: "Troubleshooting",
};

export default async function TroubleshootingPage() {
  return (
    <>
      <h1>Troubleshooting</h1>
      <p>Common issues and solutions for Arena CLI.</p>

      <h2>Installation issues</h2>

      <h3>npm install fails with permission errors</h3>
      <p>Configure npm to use a directory you own:</p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`mkdir ~/.npm-global
npm config set prefix '~/.npm-global'

# Add to ~/.bashrc or ~/.zshrc
export PATH=~/.npm-global/bin:$PATH

# Install without sudo
npm install -g @whitegodkingsley/arena-cli`} />

      <h3>arena: command not found</h3>
      <p>The npm global bin directory is not in your PATH:</p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# Find where npm installs global packages
npm config get prefix

# Add to PATH
export PATH="$(npm config get prefix)/bin:$PATH"

# Or use npx instead
npx @whitegodkingsley/arena-cli process video.mp4`} />

      <h2>Python issues</h2>

      <h3>Python not found</h3>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# macOS
brew install python3

# Ubuntu/Debian
sudo apt install python3 python3-pip

# Verify
python3 --version`} />

      <h3>Python version too old</h3>
      <p>Arena requires Python 3.10–3.12. Using pyenv is recommended:</p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`curl https://pyenv.run | bash
pyenv install 3.11.0
pyenv global 3.11.0`} />

      <h3>Python dependencies missing</h3>
      <p>
        Repair Arena&apos;s isolated runtime rather than installing packages into
        global Python:
      </p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`arena setup --check
arena setup --force`} />

      <h2>FFmpeg issues</h2>

      <h3>FFmpeg not found</h3>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# Verify
ffmpeg -version`} />

      <h3>Unsupported codec errors</h3>
      <p>Reinstall FFmpeg with all codecs:</p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# macOS
brew reinstall ffmpeg

# Ubuntu (enable multiverse)
sudo add-apt-repository multiverse
sudo apt update && sudo apt install ffmpeg`} />

      <h2>API issues</h2>

      <h3>OpenAI API key not found</h3>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# Set environment variable
export OPENAI_API_KEY="sk-..."

# Or use Arena's interactive owner-only credential store
arena config set openai_api_key

# Verify
arena config get openai_api_key`} />

      <h3>Rate limit exceeded (429)</h3>
      <p>
        Arena handles rate limits automatically with exponential backoff. If
        you&apos;re consistently hitting limits:
      </p>
      <ul>
        <li>Use <code>gpt-4o-mini</code> (higher rate limits)</li>
        <li>Process fewer clips at once (<code>-n 3</code>)</li>
        <li>Add delays between batch jobs</li>
        <li>Upgrade your OpenAI API tier</li>
      </ul>

      <h3>Insufficient quota</h3>
      <p>
        Add credits at{" "}
        <a href="https://platform.openai.com/account/billing" target="_blank" rel="noopener noreferrer">
          platform.openai.com/account/billing
        </a>.
      </p>

      <h2>Processing issues</h2>

      <h3>No clips generated</h3>
      <p>Possible causes:</p>
      <ul>
        <li><strong>Video too short</strong> — Use videos longer than 2 minutes</li>
        <li><strong>Duration constraints too strict</strong> — Try <code>--min 20 --max 90</code></li>
        <li><strong>All clips failed quality gate</strong> — Export layers to debug</li>
      </ul>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# Check why clips were rejected
arena process video.mp4 --export-layers
cat output/editorial_layers/layer3_validated.json | \\
  jq '.[] | select(.verdict=="REJECT") | {rejection_reason}'`} />

      <h3>No clips passed validation</h3>
      <p>
        Layer 3 is a strict quality gate. Relax your duration constraints:
      </p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# More permissive constraints
arena process video.mp4 --min 15 --max 120`} />

      <h3>Processing is very slow</h3>
      <ul>
        <li>Use <code>gpt-4o-mini</code> instead of <code>gpt-4o</code></li>
        <li>Reduce clip count (<code>-n 3</code>)</li>
        <li>Check your internet connection</li>
      </ul>

      <h3>Memory errors</h3>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# Use fast mode (less memory)
arena process video.mp4 --fast

# Or reduce video resolution first
ffmpeg -i video.mp4 -vf scale=-1:720 -c:a copy video_720p.mp4
arena process video_720p.mp4`} />

      <h2>Quality issues</h2>

      <h3>Clips have poor cut points</h3>
      <p>
        The 4-layer editorial system should handle this. If clips still start
        or end awkwardly, try adding more padding:
      </p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`arena process video.mp4 --padding 1.0`} />

      <h3>Clips are too similar</h3>
      <ul>
        <li>Reduce clip count (<code>-n 3</code>) for more diversity</li>
        <li>Increase duration range for more variety</li>
      </ul>

      <h3>Low video quality output</h3>
      <p>
        If using <code>--fast</code> mode, clips are stream-copied without
        re-encoding. Remove the flag for full re-encoding:
      </p>
      <DocCodeBlock lang="bash" filename="Terminal" code={`arena process video.mp4  # Without --fast`} />

      <h2>Diagnostics</h2>
      <DocCodeBlock lang="bash" filename="Terminal" code={`# Run full system check
arena diagnose

# Check versions
arena --version
node --version
python3 --version
ffmpeg -version

# Debug mode (verbose output)
arena process video.mp4 --debug

# Save debug log
arena process video.mp4 --debug 2>&1 | tee debug.log`} />

      <h2>Getting more help</h2>
      <ul>
        <li>
          <a href="https://github.com/iamwhitegod/arena/issues" target="_blank" rel="noopener noreferrer">
            GitHub Issues
          </a>{" "}
          — Report bugs and request features
        </li>
        <li>
          <a href="https://github.com/iamwhitegod/arena/issues" target="_blank" rel="noopener noreferrer">
            GitHub Issues
          </a>{" "}
          — Ask questions and share tips
        </li>
      </ul>
      <p>When reporting an issue, include:</p>
      <ul>
        <li>Full error message</li>
        <li>Command you ran</li>
        <li>Output from <code>arena diagnose</code></li>
        <li>Your OS and version</li>
      </ul>
    </>
  );
}
