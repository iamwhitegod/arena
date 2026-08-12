"use client";

import { useState } from "react";

interface Tab {
  id: string;
  label: string;
}

interface TabsProps {
  tabs: Tab[];
  children: React.ReactNode[];
}

export function Tabs({ tabs, children }: TabsProps) {
  const [active, setActive] = useState(tabs[0].id);

  return (
    <div className="not-prose my-6">
      <div className="flex border-b border-border">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActive(tab.id)}
            className={`px-5 py-2.5 text-sm font-medium transition-colors cursor-pointer ${
              active === tab.id
                ? "text-arena-700 border-b-2 border-arena-600 -mb-px"
                : "text-muted hover:text-foreground"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {tabs.map((tab, i) => (
        <div
          key={tab.id}
          className={active === tab.id ? "mt-6" : "hidden"}
        >
          {children[i]}
        </div>
      ))}
    </div>
  );
}
