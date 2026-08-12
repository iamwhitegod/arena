export const LINKS = {
  github: "https://github.com/iamwhitegod/arena",
  npm: "https://www.npmjs.com/package/@whitegodkingsley/arena-cli",
  issues: "https://github.com/iamwhitegod/arena/issues",
  discussions: "https://github.com/iamwhitegod/arena/discussions",
  docs: "https://getarena.vercel.app/docs",
};

export const INSTALL_COMMAND = "npm install -g @whitegodkingsley/arena-cli";

export const FEATURES = [
  {
    title: "4-Layer Editorial System",
    description:
      "Professional-grade clip selection. Detects hooks, expands to thought boundaries, validates standalone context, and packages with titles and hashtags.",
    icon: "layers",
  },
  {
    title: "AI + Audio Energy Analysis",
    description:
      "Combines GPT semantic insights with audio energy peaks to find clips with both high-value content and dynamic delivery.",
    icon: "waveform",
  },
  {
    title: "Multi-Platform Formatting",
    description:
      "Instantly format clips for TikTok, Instagram Reels, YouTube Shorts, and more with smart cropping and blur backgrounds.",
    icon: "devices",
  },
  {
    title: "URL & Audio Support",
    description:
      "Process content from YouTube, Vimeo, Twitter, and 1000+ sites. Supports all audio formats including MP3, WAV, and FLAC.",
    icon: "link",
  },
] as const;

export const STEPS = [
  {
    number: 1,
    title: "Install the CLI",
    command: "npm install -g @whitegodkingsley/arena-cli",
  },
  {
    number: 2,
    title: "Point it at your video",
    command: "arena process video.mp4 -n 5",
  },
  {
    number: 3,
    title: "Get platform-ready clips",
    command: "arena format clips/ -p tiktok",
  },
] as const;

export const PRICING = {
  free: {
    name: "Free",
    price: 0,
    description: "Get started with Arena's core features",
    features: [
      "3 videos per month",
      "Up to 30-minute videos",
      "4 clips per video",
      "Basic formatting",
      "Community support",
    ],
    cta: "Get Started Free",
    highlighted: false,
  },
  pro: {
    name: "Pro",
    price: 9,
    description: "Everything you need for serious content creation",
    features: [
      "Unlimited videos",
      "Unlimited video length",
      "Unlimited clips per video",
      "Caption & subtitle burning",
      "Scene detection",
      "All formatting options",
      "Priority support",
    ],
    cta: "Join the Waitlist",
    highlighted: true,
  },
} as const;
