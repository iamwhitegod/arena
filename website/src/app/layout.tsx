import type { Metadata } from "next";
import { Outfit, JetBrains_Mono } from "next/font/google";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { SmoothScroll } from "@/components/providers/SmoothScroll";
import "./globals.css";

const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://getarena.vercel.app"),
  title: "Arena — AI-Powered Video Clip Generation",
  description:
    "Turn long-form video into viral, platform-optimized social media clips. Powered by a 4-layer editorial system and hybrid AI analysis.",
  keywords: [
    "video clipping",
    "AI video editor",
    "TikTok clips",
    "YouTube Shorts",
    "content repurposing",
    "podcast highlights",
  ],
  openGraph: {
    type: "website",
    title: "Arena — AI-Powered Video Clip Generation",
    description:
      "Turn long-form video into viral, platform-optimized social media clips.",
    images: ["/og-preview.png"],
  },
  twitter: {
    card: "summary_large_image",
    title: "Arena — AI-Powered Video Clip Generation",
    description:
      "Turn long-form video into viral, platform-optimized social media clips.",
  },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "Arena",
  applicationCategory: "MultimediaApplication",
  operatingSystem: "macOS, Linux, Windows",
  description:
    "AI-powered video clip generation tool. Turn long-form content into viral clips for TikTok, Instagram Reels, and YouTube Shorts.",
  offers: {
    "@type": "Offer",
    price: "0",
    priceCurrency: "USD",
  },
  url: "https://getarena.vercel.app",
  author: {
    "@type": "Person",
    name: "Whitegod Kingsley",
    url: "https://github.com/iamwhitegod",
  },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${outfit.variable} ${jetbrainsMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('theme');if(t==='dark'||(!t&&window.matchMedia('(prefers-color-scheme:dark)').matches)){document.documentElement.classList.add('dark')}}catch(e){}})()`,
          }}
        />
      </head>
      <body className="min-h-full flex flex-col font-sans">
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
        <SmoothScroll>
          <Navbar />
          <main className="flex-1">{children}</main>
          <Footer />
        </SmoothScroll>
      </body>
    </html>
  );
}
