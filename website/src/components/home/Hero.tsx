import { Badge } from "@/components/shared/Badge";
import { Button } from "@/components/shared/Button";
import { CodeBlock } from "@/components/shared/CodeBlock";
import { LINKS, INSTALL_COMMAND } from "@/lib/constants";

export function Hero() {
  return (
    <section className="py-14 sm:py-28">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="max-w-3xl mx-auto text-center">
          <div className="animate-hero-1 flex flex-wrap items-center justify-center gap-2 sm:gap-3 mb-8">
            <Badge>Open Source</Badge>
            <Badge variant="outline">MIT Licensed</Badge>
            <Badge variant="outline">From $0.20/video</Badge>
          </div>

          <h1 className="animate-hero-2 text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight leading-[1.1]">
            Turn Long-Form Video Into{" "}
            <span className="text-arena-600">Viral Clips</span>
          </h1>

          <p className="animate-hero-3 mt-4 sm:mt-6 text-base sm:text-xl text-muted max-w-2xl mx-auto leading-relaxed">
            An AI-powered clipping engine that automatically finds the best
            moments in your videos and exports platform-ready clips for TikTok,
            Reels, and Shorts.
          </p>

          <div className="animate-hero-4 mt-10 flex flex-col sm:flex-row items-center justify-center gap-4 w-full sm:w-auto">
            <Button href="/docs" size="lg" className="w-full sm:w-auto">
              Install Arena
            </Button>
            <Button
              href={LINKS.github}
              external
              variant="secondary"
              size="lg"
              className="w-full sm:w-auto"
            >
              <svg
                className="w-5 h-5"
                fill="currentColor"
                viewBox="0 0 24 24"
              >
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
              </svg>
              View on GitHub
            </Button>
          </div>
        </div>

        <div className="animate-hero-5 mt-10 sm:mt-16 max-w-2xl mx-auto">
          <div className="rounded-xl border border-border bg-foreground p-1 shadow-xl shadow-arena-600/5">
            <div className="flex items-center gap-2 px-3 sm:px-4 py-2">
              <span className="w-3 h-3 rounded-full bg-red-400"></span>
              <span className="w-3 h-3 rounded-full bg-yellow-400"></span>
              <span className="w-3 h-3 rounded-full bg-green-400"></span>
              <span className="ml-4 text-xs text-muted-foreground font-mono hidden sm:inline">
                terminal
              </span>
            </div>
            <div className="px-2 sm:px-4 pb-3 sm:pb-4 space-y-2 overflow-x-auto">
              <CodeBlock code={INSTALL_COMMAND} />
              <div className="flex items-center gap-2 sm:gap-3 font-mono text-xs sm:text-sm px-2 sm:px-4 py-2 whitespace-nowrap">
                <span className="text-muted-foreground select-none">$</span>
                <span className="text-green-400">arena process</span>
                <span className="text-white">video.mp4</span>
                <span className="text-arena-400">--captions</span>
                <span className="text-arena-400">-p tiktok</span>
              </div>
              <div className="font-mono text-xs text-muted-foreground px-2 sm:px-4 space-y-1">
                <p className="text-green-400">
                  ✓ Transcribed (2m 34s)
                </p>
                <p className="text-green-400">
                  ✓ Found 12 candidate moments
                </p>
                <p className="text-green-400">
                  ✓ 5 clips passed quality gate
                </p>
                <p className="text-green-400">
                  ✓ Exported to output/clips/
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
