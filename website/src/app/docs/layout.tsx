import type { Metadata } from "next";
import { DocsSidebar } from "@/components/docs/DocsSidebar";
import { DocsMobileNav } from "@/components/docs/DocsMobileNav";

export const metadata: Metadata = {
  title: {
    template: "%s — Arena Docs",
    default: "Arena Documentation",
  },
  description: "Complete documentation for Arena CLI — AI-powered video clip generation.",
};

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
      <div className="flex gap-10">
        <DocsSidebar />
        <div className="flex-1 min-w-0">
          <DocsMobileNav />
          <article className="prose prose-slate max-w-none
            prose-headings:font-semibold prose-headings:tracking-tight
            prose-h1:text-3xl prose-h1:mb-4
            prose-h2:text-xl prose-h2:mt-10 prose-h2:mb-4 prose-h2:border-b prose-h2:border-border prose-h2:pb-2
            prose-h3:text-lg prose-h3:mt-8 prose-h3:mb-3
            prose-p:text-muted prose-p:leading-relaxed
            prose-code:font-mono prose-code:text-sm prose-code:bg-surface prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none
            prose-a:text-arena-600 prose-a:no-underline hover:prose-a:underline
            prose-li:text-muted
            prose-table:text-sm prose-table:overflow-x-auto prose-table:block
            prose-th:text-left prose-th:font-semibold prose-th:border-b prose-th:border-border prose-th:pb-2
            prose-td:border-b prose-td:border-border prose-td:py-2
            prose-strong:text-foreground
          ">
            {children}
          </article>
        </div>
      </div>
    </div>
  );
}
