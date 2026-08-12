import type { Metadata } from "next";
import { Hero } from "@/components/home/Hero";
import { Features } from "@/components/home/Features";
import { HowItWorks } from "@/components/home/HowItWorks";
import { InstallCTA } from "@/components/home/InstallCTA";

export const metadata: Metadata = {
  title: "Arena — AI-Powered Video Clip Generation",
  description:
    "Turn long-form video into viral clips for TikTok, Reels, and Shorts. Open-source, developer-first, runs locally. From $0.20 per video.",
  openGraph: {
    title: "Arena — Turn Long-Form Video Into Viral Clips",
    description:
      "AI-powered clipping engine with a 4-layer editorial system. Open source, runs locally, costs $0.20 per video.",
  },
};

export default function Home() {
  return (
    <>
      <Hero />
      <Features />
      <HowItWorks />
      <InstallCTA />
    </>
  );
}
