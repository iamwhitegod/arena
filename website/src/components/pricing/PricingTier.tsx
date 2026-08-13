import { Button } from "@/components/shared/Button";

interface PricingTierProps {
  name: string;
  price: string;
  priceSuffix: string;
  badge: string;
  description: string;
  features: readonly string[];
  cta: string;
  highlighted: boolean;
  ctaHref: string;
}

export function PricingTier({
  name,
  price,
  priceSuffix,
  badge,
  description,
  features,
  cta,
  highlighted,
  ctaHref,
}: PricingTierProps) {
  return (
    <div
      className={`rounded-2xl border bg-background p-5 sm:p-8 flex flex-col ${
        highlighted
          ? "border-arena-600 shadow-lg shadow-arena-600/10 relative"
          : "border-border"
      }`}
    >
      {highlighted && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-arena-600 text-white text-xs font-semibold px-3 py-1 rounded-full">
          {badge}
        </span>
      )}

      {!highlighted && (
        <span className="self-start mb-4 rounded-full border border-border bg-surface px-3 py-1 text-xs font-semibold text-muted">
          {badge}
        </span>
      )}

      <div className="mb-6">
        <h3 className="text-xl font-semibold">{name}</h3>
        <p className="mt-1 text-sm text-muted">{description}</p>
      </div>

      <div className="mb-8">
        <span className="text-4xl font-extrabold tracking-tight">
          {price}
        </span>
        <span className="ml-2 text-muted text-sm">{priceSuffix}</span>
      </div>

      <ul className="space-y-3 mb-8 flex-1">
        {features.map((feature) => (
          <li key={feature} className="flex items-start gap-3 text-sm">
            <svg
              className="w-5 h-5 text-arena-600 shrink-0 mt-0.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M5 13l4 4L19 7"
              />
            </svg>
            <span>{feature}</span>
          </li>
        ))}
      </ul>

      <Button
        href={ctaHref}
        external={ctaHref.startsWith("http")}
        variant={highlighted ? "primary" : "secondary"}
        size="lg"
        className="w-full"
      >
        {cta}
      </Button>
    </div>
  );
}
