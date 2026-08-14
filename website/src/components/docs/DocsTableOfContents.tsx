"use client";

import { useEffect, useState, type MouseEvent } from "react";
import { usePathname } from "next/navigation";

interface TableOfContentsItem {
  id: string;
  label: string;
  level: 2 | 3;
}

function slugify(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-");
}

export function DocsTableOfContents() {
  const pathname = usePathname();
  const [items, setItems] = useState<TableOfContentsItem[]>([]);
  const [activeId, setActiveId] = useState("");

  useEffect(() => {
    const article = document.querySelector<HTMLElement>("[data-docs-article]");
    if (!article) return;

    const headings = Array.from(
      article.querySelectorAll<HTMLHeadingElement>("h2, h3"),
    );
    const usedIds = new Set<string>();
    const nextItems = headings.map((heading) => {
      const baseId =
        heading.id || slugify(heading.textContent || "section") || "section";
      let id = baseId;
      let suffix = 2;

      while (usedIds.has(id)) {
        id = `${baseId}-${suffix}`;
        suffix += 1;
      }

      usedIds.add(id);
      heading.id = id;
      heading.classList.add("scroll-mt-24");

      return {
        id,
        label: heading.textContent?.trim() || "Section",
        level: heading.tagName === "H2" ? 2 : 3,
      } as TableOfContentsItem;
    });

    const initializationFrame = window.requestAnimationFrame(() => {
      setItems(nextItems);
      setActiveId(window.location.hash.slice(1) || nextItems[0]?.id || "");
    });

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);

        if (visible[0]) setActiveId(visible[0].target.id);
      },
      { rootMargin: "-96px 0px -70% 0px", threshold: 0 },
    );

    headings.forEach((heading) => observer.observe(heading));
    return () => {
      window.cancelAnimationFrame(initializationFrame);
      observer.disconnect();
    };
  }, [pathname]);

  if (items.length === 0) return null;

  const scrollToSection = (
    event: MouseEvent<HTMLAnchorElement>,
    id: string,
  ) => {
    event.preventDefault();

    const heading = document.getElementById(id);
    if (!heading) return;

    setActiveId(id);
    window.history.pushState(null, "", `#${id}`);
    heading.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <aside className="hidden xl:block w-52 shrink-0" aria-label="On this page">
      <nav className="sticky top-20 max-h-[calc(100vh-6rem)] overflow-y-auto pb-8">
        <h2 className="text-sm font-semibold text-foreground mb-4">
          On this page
        </h2>
        <ol className="space-y-2.5 border-l border-border">
          {items.map((item) => (
            <li key={item.id} className={item.level === 3 ? "pl-3" : ""}>
              <a
                href={`#${item.id}`}
                onClick={(event) => scrollToSection(event, item.id)}
                aria-current={activeId === item.id ? "location" : undefined}
                className={`block -ml-px border-l py-0.5 text-sm leading-5 transition-colors ${
                  item.level === 3 ? "pl-4" : "pl-3"
                } ${
                  activeId === item.id
                    ? "border-arena-600 text-arena-600 font-medium"
                    : "border-transparent text-muted hover:text-foreground"
                }`}
              >
                {item.label}
              </a>
            </li>
          ))}
        </ol>
      </nav>
    </aside>
  );
}
