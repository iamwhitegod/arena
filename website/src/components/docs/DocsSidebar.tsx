"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { docsNav } from "@/lib/docs-nav";

export function DocsSidebar() {
  const pathname = usePathname();

  return (
    <nav className="w-64 shrink-0 hidden lg:block">
      <div className="sticky top-20 space-y-8 pr-6 border-r border-border max-h-[calc(100vh-5rem)] overflow-y-auto pb-10">
        {docsNav.map((section) => (
          <div key={section.title}>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted mb-3">
              {section.title}
            </h4>
            <ul className="space-y-1">
              {section.items.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className={`block text-sm py-1.5 px-3 rounded-md transition-colors ${
                        isActive
                          ? "bg-arena-50 text-arena-700 font-medium"
                          : "text-muted hover:text-foreground hover:bg-surface"
                      }`}
                    >
                      {item.title}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
    </nav>
  );
}
