import { SectionHeader } from "@/components/shared/SectionHeader";
import { ScrollReveal } from "@/components/shared/ScrollReveal";

const benefits = [
  {
    title: "No Upfront Upload",
    description:
      "Start processing immediately from your terminal. Arena does not require you to upload large source videos to the cloud.",
  },
  {
    title: "Save Time and Data",
    description:
      "Avoid lengthy uploads and unnecessary bandwidth usage before processing can begin.",
  },
  {
    title: "Built for Unreliable Connections",
    description:
      "Creators in low-bandwidth regions can process videos locally without repeatedly restarting failed uploads when their connection drops.",
  },
  {
    title: "Your Files Stay With You",
    description:
      "Source videos, transcripts, analysis results, and generated clips remain on your machine unless you explicitly use an external provider or Arena Cloud.",
  },
  {
    title: "Ready for Local AI Models",
    description:
      "Arena's local-first architecture creates a path toward optional local transcription, analysis, and embedding models in the future.",
  },
  {
    title: "Creator and Developer Friendly",
    description:
      "Creators get a fast, private workflow. Developers get a scriptable terminal interface, inspectable artifacts, and automation-friendly commands.",
  },
] as const;

export function LocalFirst() {
  return (
    <section id="local-first" className="py-14 sm:py-28">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <SectionHeader
          title="Why Local-First?"
          subtitle="Your videos should not need to leave your computer before you can start creating."
        />

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
          {benefits.map((benefit, index) => (
            <ScrollReveal key={benefit.title} delay={index * 75}>
              <article className="h-full rounded-xl border border-border bg-surface p-5 sm:p-7">
                <span className="font-mono text-xs text-arena-600">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <h3 className="mt-4 text-lg font-semibold">{benefit.title}</h3>
                <p className="mt-2 text-sm text-muted leading-relaxed">
                  {benefit.description}
                </p>
              </article>
            </ScrollReveal>
          ))}
        </div>
      </div>
    </section>
  );
}
