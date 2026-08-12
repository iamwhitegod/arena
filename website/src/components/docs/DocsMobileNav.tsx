"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { docsNav } from "@/lib/docs-nav";

export function DocsMobileNav() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  const currentPage = docsNav
    .flatMap((s) => s.items)
    .find((item) => item.href === pathname);

  return (
    <div className="lg:hidden mb-8">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between rounded-lg border border-border px-4 py-3 text-sm cursor-pointer"
      >
        <span className="font-medium">{currentPage?.title ?? "Docs"}</span>
        <svg
          className={`w-4 h-4 text-muted transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="mt-2 rounded-lg border border-border bg-white shadow-lg p-4 space-y-6">
          {docsNav.map((section) => (
            <div key={section.title}>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted mb-2">
                {section.title}
              </h4>
              <ul className="space-y-1">
                {section.items.map((item) => {
                  const isActive = pathname === item.href;
                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        onClick={() => setOpen(false)}
                        className={`block text-sm py-1.5 px-3 rounded-md ${
                          isActive
                            ? "bg-arena-600/10 text-arena-600 font-medium"
                            : "text-muted hover:text-foreground"
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
      )}
    </div>
  );
}
