import { PricingTier } from "./PricingTier";
import { PRICING, LINKS } from "@/lib/constants";

export function PricingTable() {
  return (
    <div>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
        <PricingTier {...PRICING.oss} />
        <PricingTier {...PRICING.creator} />
        <PricingTier {...PRICING.pro} />
        <PricingTier {...PRICING.studio} />
      </div>

      <div className="mt-12 rounded-2xl border border-border bg-surface p-6 text-center sm:p-8">
        <h3 className="text-lg font-semibold mb-2">Cloud pricing is a proposal</h3>
        <p className="mx-auto max-w-3xl text-sm text-muted">
          Arena Cloud is not generally available yet. Proposed plans are billed by
          source-video minutes so usage remains predictable. Arena OSS stays free,
          complete, local-first, and independent of a Cloud subscription. Enterprise
          plans are expected to start at $499/month with custom capacity, security,
          and support.
        </p>
        <a
          href={LINKS.cloudAccess}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-4 inline-block text-sm font-semibold text-arena-600 hover:text-arena-700"
        >
          Reserve Cloud access on GitHub →
        </a>
      </div>
    </div>
  );
}
