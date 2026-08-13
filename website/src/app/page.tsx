import type { Metadata } from "next";
import { Hero } from "@/components/home/Hero";
import { Features } from "@/components/home/Features";
import { LocalFirst } from "@/components/home/LocalFirst";
import { HowItWorks } from "@/components/home/HowItWorks";
import { InstallCTA } from "@/components/home/InstallCTA";

export const metadata: Metadata = {
  title: "Arena — Local-First Video Clipping for the Terminal",
  description:
    "Arena is an AI-powered, open-source, local-first video clipping engine for the terminal that automatically finds the best moments in your videos and exports platform-ready clips for TikTok, Reels, and Shorts.",
  openGraph: {
    title: "Arena — Local-First Video Clipping for the Terminal",
    description:
      "Automatically find the best moments in your videos and export platform-ready clips for TikTok, Reels, and Shorts.",
  },
};

export default function Home() {
  return (
    <>
      <Hero />
      <Features />
      <LocalFirst />
      <HowItWorks />
      <InstallCTA />
    </>
  );
}
