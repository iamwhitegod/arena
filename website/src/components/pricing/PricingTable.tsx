"use client";

import { useState } from "react";
import { PricingTier } from "./PricingTier";
import { PRICING, LINKS } from "@/lib/constants";

export function PricingTable() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleWaitlist = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
  };

  return (
    <div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-3xl mx-auto">
        <PricingTier {...PRICING.free} ctaHref="/docs" />
        <PricingTier {...PRICING.pro} />
      </div>

      <div className="mt-16 max-w-md mx-auto text-center">
        <h3 className="text-lg font-semibold mb-2">
          Get notified when Pro launches
        </h3>
        <p className="text-sm text-muted mb-6">
          Join the waitlist to be first in line for unlimited clips, captions,
          and priority support.
        </p>

        {submitted ? (
          <div className="rounded-lg bg-arena-600/10 border border-arena-600/20 p-4">
            <p className="text-sm text-arena-600 font-medium">
              You&apos;re on the list! We&apos;ll let you know when Pro is
              ready.
            </p>
          </div>
        ) : (
          <form onSubmit={handleWaitlist} className="flex flex-col sm:flex-row gap-2">
            <input
              type="email"
              required
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="flex-1 rounded-lg border border-border px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-arena-600 focus:border-transparent"
            />
            <button
              type="submit"
              className="rounded-lg bg-arena-600 text-white px-6 py-2.5 text-sm font-medium hover:bg-arena-700 transition-colors cursor-pointer whitespace-nowrap"
            >
              Join Waitlist
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
