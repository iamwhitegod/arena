import type { Metadata } from "next";
import { SectionHeader } from "@/components/shared/SectionHeader";
import { ScrollReveal } from "@/components/shared/ScrollReveal";
import { PricingTable } from "@/components/pricing/PricingTable";

export const metadata: Metadata = {
  title: "Pricing — Arena",
  description:
    "Simple, transparent pricing. Start free and upgrade when you need more.",
};

export default function PricingPage() {
  return (
    <section className="py-14 sm:py-28">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="animate-hero-1">
          <SectionHeader
            title="Simple, Transparent Pricing"
            subtitle="Start free. Upgrade when you're ready for more."
          />
        </div>
        <ScrollReveal delay={150}>
          <PricingTable />
        </ScrollReveal>
      </div>
    </section>
  );
}
