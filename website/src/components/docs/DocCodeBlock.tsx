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
    theme: "github-dark",
  });

  return (
    <div className="not-prose rounded-lg overflow-hidden border border-[#30363d] my-6 relative group">
      {filename && (
        <div className="flex items-center justify-between px-4 py-2 bg-[#161b22] border-b border-[#30363d]">
          <span className="text-xs text-[#8b949e] font-mono">{filename}</span>
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
