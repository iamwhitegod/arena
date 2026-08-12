import Link from "next/link";
import { LINKS } from "@/lib/constants";

export function Footer() {
  return (
    <footer className="border-t border-border bg-surface py-10 sm:py-16">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 sm:gap-10">
          <div className="md:col-span-1">
            <Link href="/" className="flex items-center gap-2">
              <span className="font-mono text-lg font-bold text-arena-500">
                &gt;_
              </span>
              <span className="font-semibold text-lg tracking-tight">
                arena
              </span>
            </Link>
            <p className="mt-3 text-sm text-muted">
              AI-powered video clip generation. Turn long-form content into
              viral clips.
            </p>
          </div>

          <div>
            <h4 className="text-sm font-semibold mb-4">Product</h4>
            <ul className="space-y-2.5">
              <li>
                <Link
                  href="/#features"
                  className="text-sm text-muted hover:text-foreground transition-colors"
                >
                  Features
                </Link>
              </li>
              <li>
                <Link
                  href="/pricing"
                  className="text-sm text-muted hover:text-foreground transition-colors"
                >
                  Pricing
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="text-sm font-semibold mb-4">Resources</h4>
            <ul className="space-y-2.5">
              <li>
                <Link
                  href="/docs"
                  className="text-sm text-muted hover:text-foreground transition-colors"
                >
                  Documentation
                </Link>
              </li>
              <li>
                <a
                  href={LINKS.github}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-muted hover:text-foreground transition-colors"
                >
                  GitHub
                </a>
              </li>
              <li>
                <a
                  href={LINKS.discussions}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-muted hover:text-foreground transition-colors"
                >
                  Discussions
                </a>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="text-sm font-semibold mb-4">Legal</h4>
            <ul className="space-y-2.5">
              <li>
                <p className="text-sm text-muted">MIT License</p>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-12 pt-8 border-t border-border">
          <p className="text-sm text-muted text-center">
            &copy; {new Date().getFullYear()} Arena Contributors
          </p>
        </div>
      </div>
    </footer>
  );
}
