import type { Metadata } from "next";
import Link from "next/link";
import { LINKS } from "@/lib/constants";

export const metadata: Metadata = {
  title: "Product Roadmap",
  description:
    "See the direction for Arena Terminal, Cloud, Desktop, and Mobile. Terminal is available now; future products build on the same local-first engine.",
};

const products = [
  {
    name: "Arena Terminal",
    status: "Available now",
    tone: "available",
    description:
      "The complete open-source, local-first engine and CLI. This remains Arena's foundation and reference workflow.",
    focus: ["Reliability and recovery", "Editorial quality", "Stable artifact contracts"],
  },
  {
    name: "Arena Cloud",
    status: "Planned",
    tone: "planned",
    description:
      "Optional managed compute, storage, collaboration, automation, and publishing around the same Arena engine.",
    focus: ["Secure remote jobs", "Hosted projects", "Private alpha"],
  },
  {
    name: "Arena Desktop",
    status: "Exploration",
    tone: "exploration",
    description:
      "A visual local workflow for reviewing clips, adjusting edits, styling captions, and managing projects.",
    focus: ["Visual clip review", "Local project workflow", "Optional Cloud handoff"],
  },
  {
    name: "Arena Mobile",
    status: "Exploration",
    tone: "exploration",
    description:
      "A companion for capture, upload, job monitoring, clip approval, and publishing—not initially a replacement for the full engine.",
    focus: ["Capture and upload", "Review and approvals", "Social export"],
  },
] as const;

const stages = [
  {
    number: "01",
    title: "Strengthen Terminal",
    body: "Make installation, processing, recovery, releases, and public artifact contracts production-grade.",
  },
  {
    number: "02",
    title: "Validate Cloud",
    body: "Prove secure managed processing, predictable unit economics, and demand through a private alpha.",
  },
  {
    number: "03",
    title: "Build Desktop",
    body: "Bring the same local engine to a visual clip-review and project-management experience.",
  },
  {
    number: "04",
    title: "Launch Mobile Companion",
    body: "Create a fast capture-to-review workflow connected to Cloud and Desktop projects.",
  },
] as const;

export default function RoadmapPage() {
  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 py-16 sm:py-24">
      <section className="max-w-3xl">
        <p className="font-mono text-sm text-arena-600 mb-4">PRODUCT DIRECTION</p>
        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight">
          One Engine. Four Experiences.
        </h1>
        <p className="mt-6 text-lg sm:text-xl text-muted leading-relaxed">
          Arena starts in the terminal. Cloud, Desktop, and Mobile will build on
          the same open-source, local-first engine without making local processing
          depend on an account or subscription.
        </p>
        <p className="mt-4 text-sm text-muted">
          This roadmap communicates direction, not guaranteed release dates.
        </p>
      </section>

      <section className="mt-14 grid md:grid-cols-2 gap-5" aria-label="Arena products">
        {products.map((product) => (
          <article key={product.name} className="rounded-2xl border border-border bg-surface p-6 sm:p-8">
            <div className="flex items-start justify-between gap-4">
              <h2 className="text-2xl font-bold">{product.name}</h2>
              <span className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold ${
                product.tone === "available"
                  ? "bg-arena-600 text-white"
                  : product.tone === "planned"
                    ? "bg-arena-600/10 text-arena-600"
                    : "bg-background text-muted border border-border"
              }`}>
                {product.status}
              </span>
            </div>
            <p className="mt-4 text-muted leading-relaxed">{product.description}</p>
            <ul className="mt-6 space-y-2">
              {product.focus.map((item) => (
                <li key={item} className="flex gap-3 text-sm">
                  <span className="text-arena-600">✓</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </article>
        ))}
      </section>

      <section className="mt-20">
        <p className="font-mono text-sm text-arena-600 mb-3">SEQUENCING</p>
        <h2 className="text-3xl sm:text-4xl font-bold">Development stages</h2>
        <div className="mt-8 grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {stages.map((stage) => (
            <article key={stage.number} className="rounded-xl border border-border p-5">
              <span className="font-mono text-sm text-arena-600">{stage.number}</span>
              <h3 className="mt-3 text-lg font-bold">{stage.title}</h3>
              <p className="mt-2 text-sm text-muted leading-relaxed">{stage.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="mt-20 rounded-2xl border border-arena-600/20 bg-arena-600/5 p-7 sm:p-10">
        <h2 className="text-2xl font-bold">Help shape what ships next</h2>
        <p className="mt-3 text-muted max-w-2xl">
          Roadmap priorities should follow real workflows and evidence. Share how
          you use Arena and which product surface would remove the most friction.
        </p>
        <div className="mt-6 flex flex-wrap gap-4">
          <a className="text-arena-600 font-semibold hover:underline" href={LINKS.discussions} target="_blank" rel="noopener noreferrer">
            Join the discussion →
          </a>
          <Link className="text-foreground font-semibold hover:underline" href="/docs">
            Use Arena Terminal →
          </Link>
        </div>
      </section>
    </main>
  );
}
