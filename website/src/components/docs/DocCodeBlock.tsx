import { codeToHtml } from "shiki";
import { CopyButton } from "./CopyButton";

interface DocCodeBlockProps {
  code: string;
  lang?: string;
  filename?: string;
}

export async function DocCodeBlock({
  code,
  lang = "bash",
  filename,
}: DocCodeBlockProps) {
  const trimmedCode = code.trim();

  const html = await codeToHtml(trimmedCode, {
    lang,
    theme: "monokai",
  });

  return (
    <div className="not-prose rounded-xl overflow-hidden border border-[#403e41] bg-[#191919] my-6 relative group shadow-[0_14px_35px_rgba(0,0,0,0.18)]">
      {filename && (
        <div className="flex items-center justify-between px-4 py-2.5 bg-[#221f22] border-b border-[#403e41]">
          <div className="flex items-center gap-3">
            <span className="flex gap-1.5" aria-hidden="true">
              <span className="size-2.5 rounded-full bg-[#ff6188]" />
              <span className="size-2.5 rounded-full bg-[#ffd866]" />
              <span className="size-2.5 rounded-full bg-[#a9dc76]" />
            </span>
            <span className="text-xs text-[#c1c0c0] font-mono">{filename}</span>
          </div>
          <CopyButton code={trimmedCode} />
        </div>
      )}
      <div
        className="shiki-wrapper"
        dangerouslySetInnerHTML={{ __html: html }}
      />
      {!filename && (
        <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <CopyButton code={trimmedCode} />
        </div>
      )}
    </div>
  );
}
