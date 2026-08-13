import type { Metadata } from "next";
import { SectionHeader } from "@/components/shared/SectionHeader";
import { ScrollReveal } from "@/components/shared/ScrollReveal";
import { PricingTable } from "@/components/pricing/PricingTable";

export const metadata: Metadata = {
  title: "Pricing — Arena",
  description:
    "Arena OSS is free forever. Review the proposed usage-based plans for Arena Cloud.",
};

export default function PricingPage() {
  return (
    <section className="py-14 sm:py-28">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="animate-hero-1">
          <SectionHeader
            title="Local is Free. Cloud is Optional."
            subtitle="Use the complete Arena engine on your own machine with no Arena quota. Proposed Cloud plans add managed compute, storage, collaboration, and automation."
          />
        </div>
        <ScrollReveal delay={150}>
          <PricingTable />
        </ScrollReveal>
      </div>
    </section>
  );
}
