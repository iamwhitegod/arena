"use client";

import { useClipboard } from "@/hooks/useClipboard";

interface CopyButtonProps {
  code: string;
  floating?: boolean;
}

export function CopyButton({ code, floating }: CopyButtonProps) {
  const { copied, copy } = useClipboard();

  return (
    <button
      onClick={() => copy(code)}
      className={`text-[#6e7681] hover:text-[#c9d1d9] transition-colors cursor-pointer ${
        floating ? "absolute top-3 right-3" : ""
      }`}
      aria-label="Copy to clipboard"
    >
      {copied ? (
        <svg className="w-4 h-4 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      ) : (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
      )}
    </button>
  );
}
