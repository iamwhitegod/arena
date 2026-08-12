"use client";

import { useClipboard } from "@/hooks/useClipboard";

interface CodeBlockProps {
  code: string;
  prefix?: string;
}

export function CodeBlock({ code, prefix = "$" }: CodeBlockProps) {
  const { copied, copy } = useClipboard();

  return (
    <div className="flex items-center gap-2 sm:gap-3 rounded-lg bg-surface border border-border px-3 sm:px-4 py-3 font-mono text-xs sm:text-sm overflow-x-auto">
      <span className="text-muted-foreground select-none">{prefix}</span>
      <code className="flex-1 text-white whitespace-nowrap">{code}</code>
      <button
        onClick={() => copy(code)}
        className="text-muted-foreground hover:text-white transition-colors shrink-0 cursor-pointer"
        aria-label="Copy to clipboard"
      >
        {copied ? (
          <svg
            className="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M5 13l4 4L19 7"
            />
          </svg>
        ) : (
          <svg
            className="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
            />
          </svg>
        )}
      </button>
    </div>
  );
}
