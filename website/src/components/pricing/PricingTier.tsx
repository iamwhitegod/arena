import { Button } from "@/components/shared/Button";

interface PricingTierProps {
  name: string;
  price: number;
  description: string;
  features: readonly string[];
  cta: string;
  highlighted: boolean;
  ctaHref?: string;
}

export function PricingTier({
  name,
  price,
  description,
  features,
  cta,
  highlighted,
  ctaHref,
}: PricingTierProps) {
  return (
    <div
      className={`rounded-2xl border p-5 sm:p-8 flex flex-col ${
        highlighted
          ? "border-arena-600 shadow-lg shadow-arena-600/10 relative"
          : "border-border"
      }`}
    >
      {highlighted && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-arena-600 text-white text-xs font-semibold px-3 py-1 rounded-full">
          Popular
        </span>
      )}

      <div className="mb-6">
        <h3 className="text-xl font-semibold">{name}</h3>
        <p className="mt-1 text-sm text-muted">{description}</p>
      </div>

      <div className="mb-8">
        <span className="text-4xl font-extrabold tracking-tight">
          ${price}
        </span>
        {price > 0 && <span className="text-muted text-sm">/month</span>}
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

      {ctaHref ? (
        <Button
          href={ctaHref}
          external
          variant={highlighted ? "primary" : "secondary"}
          size="lg"
          className="w-full"
        >
          {cta}
        </Button>
      ) : (
        <WaitlistButton highlighted={highlighted} cta={cta} />
      )}
    </div>
  );
}

function WaitlistButton({
  highlighted,
  cta,
}: {
  highlighted: boolean;
  cta: string;
}) {
  return (
    <Button
      variant={highlighted ? "primary" : "secondary"}
      size="lg"
      className="w-full"
    >
      {cta}
    </Button>
  );
}
