export interface DocNavItem {
  title: string;
  href: string;
}

export interface DocNavSection {
  title: string;
  items: DocNavItem[];
}

export const docsNav: DocNavSection[] = [
  {
    title: "Getting Started",
    items: [
      { title: "Installation", href: "/docs" },
      { title: "Configuration", href: "/docs/configuration" },
    ],
  },
  {
    title: "Usage",
    items: [
      { title: "Commands", href: "/docs/commands" },
      { title: "Workflows", href: "/docs/workflows" },
      { title: "Platform Formatting", href: "/docs/formatting" },
    ],
  },
  {
    title: "Architecture",
    items: [
      { title: "Editorial System", href: "/docs/editorial" },
    ],
  },
  {
    title: "Product",
    items: [
      { title: "Pricing & Cloud", href: "/docs/pricing" },
      { title: "Product Roadmap", href: "/roadmap" },
    ],
  },
  {
    title: "Support",
    items: [
      { title: "Troubleshooting", href: "/docs/troubleshooting" },
    ],
  },
];
