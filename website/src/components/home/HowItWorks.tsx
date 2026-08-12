import { SectionHeader } from "@/components/shared/SectionHeader";
import { ScrollReveal } from "@/components/shared/ScrollReveal";
import { STEPS } from "@/lib/constants";

export function HowItWorks() {
  return (
    <section className="py-14 sm:py-28">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <SectionHeader
          title="Get Started in Minutes"
          subtitle="Three commands. That's all it takes to go from raw video to platform-ready clips."
        />

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8">
          {STEPS.map((step, i) => (
            <ScrollReveal key={step.number} delay={i * 150}>
              <div className="text-center">
                <div className="w-10 h-10 rounded-full bg-arena-600 text-white text-sm font-bold flex items-center justify-center mx-auto mb-5">
                  {step.number}
                </div>
                <h3 className="text-lg font-semibold mb-3">{step.title}</h3>
                <div className="rounded-lg bg-foreground px-4 py-3 font-mono text-sm text-left">
                  <span className="text-muted-foreground select-none">$ </span>
                  <span className="text-white">{step.command}</span>
                </div>
              </div>
            </ScrollReveal>
          ))}
        </div>
      </div>
    </section>
  );
}
