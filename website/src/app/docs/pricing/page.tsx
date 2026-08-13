import type { Metadata } from "next";
import { LINKS } from "@/lib/constants";

export const metadata: Metadata = {
  title: "Pricing & Cloud",
  description:
    "Understand what is free in Arena OSS and how the proposed Arena Cloud plans are measured.",
};

export default function PricingDocsPage() {
  return (
    <>
      <h1>Pricing &amp; Cloud</h1>
      <p>
        Arena uses an open-source-to-cloud model. The complete local product is
        free forever. Arena Cloud is a proposed managed service for customers
        who want hosted compute, storage, collaboration, automation, and support.
      </p>

      <div className="not-prose my-8 rounded-xl border border-arena-600/20 bg-arena-600/5 p-6">
        <p className="font-semibold text-arena-600">Arena OSS is not a trial</p>
        <p className="mt-2 text-sm text-muted">
          Local processing has no Arena-imposed video, duration, clip, seat, or
          export quota. You provide the machine, storage, and OpenAI credentials,
          and remain responsible for those third-party costs and limits.
        </p>
      </div>

      <h2>Product boundary</h2>
      <table>
        <thead>
          <tr><th>Capability</th><th>Arena OSS</th><th>Proposed Arena Cloud</th></tr>
        </thead>
        <tbody>
          <tr><td>4-layer editorial engine</td><td>Included</td><td>Managed</td></tr>
          <tr><td>Clip generation, captions, formatting</td><td>Included</td><td>Included</td></tr>
          <tr><td>Compute and model credentials</td><td>Bring your own</td><td>Managed</td></tr>
          <tr><td>Storage</td><td>Local</td><td>Hosted</td></tr>
          <tr><td>Accounts and teams</td><td>Not required</td><td>Included by plan</td></tr>
          <tr><td>Automation, publishing, analytics, API</td><td>Local workflows</td><td>Managed features</td></tr>
          <tr><td>Arena usage quota</td><td>None</td><td>Source-minute allocation</td></tr>
        </tbody>
      </table>

      <h2>Why source-video minutes?</h2>
      <p>
        Cloud usage is proposed to be measured by the duration of new source
        media analyzed. This is easier to understand than opaque AI credits and
        lets Arena estimate usage before a job starts.
      </p>
      <table>
        <thead>
          <tr><th>Operation</th><th>Proposed charge</th></tr>
        </thead>
        <tbody>
          <tr><td>Analyze a new 60-minute podcast</td><td>60 source minutes</td></tr>
          <tr><td>Generate clips from its saved analysis</td><td>0 additional source minutes</td></tr>
          <tr><td>Re-export an existing clip for another platform</td><td>0 source minutes</td></tr>
          <tr><td>Re-run the complete analysis</td><td>Source duration again</td></tr>
          <tr><td>Arena-controlled failed job</td><td>Refunded</td></tr>
        </tbody>
      </table>

      <h2>Proposed Cloud plans</h2>
      <table>
        <thead>
          <tr><th>Plan</th><th>Price</th><th>Minutes</th><th>Seats</th><th>Concurrent jobs</th></tr>
        </thead>
        <tbody>
          <tr><td>Cloud trial</td><td>$0 once</td><td>60</td><td>1</td><td>1</td></tr>
          <tr><td>Creator</td><td>$19/month</td><td>250/month</td><td>1</td><td>1</td></tr>
          <tr><td>Pro</td><td>$49/month</td><td>750/month</td><td>3</td><td>3</td></tr>
          <tr><td>Studio</td><td>$149/month</td><td>2,500/month</td><td>10</td><td>10</td></tr>
          <tr><td>Enterprise</td><td>From $499/month</td><td>Custom</td><td>Custom</td><td>Custom</td></tr>
        </tbody>
      </table>
      <p>
        These are planning prices, not an offer for a generally available
        service. Entitlements may change before launch as infrastructure costs
        and customer usage are validated.
      </p>

      <h2>Cloud billing principles</h2>
      <ul>
        <li>Cloud pricing must not degrade the editorial quality of Arena OSS.</li>
        <li>Failed Arena-controlled jobs should not consume customer allocation.</li>
        <li>Overage billing must be explicitly enabled with a spending cap.</li>
        <li>Usage and estimated charges should be visible before processing.</li>
        <li>Local artifacts and Cloud artifacts should remain version-compatible.</li>
      </ul>

      <h2>Follow the plan</h2>
      <p>
        Arena Cloud is being designed in public. Share feedback in{" "}
        <a href={LINKS.discussions} target="_blank" rel="noopener noreferrer">
          GitHub Discussions
        </a>
        .
      </p>
    </>
  );
}
