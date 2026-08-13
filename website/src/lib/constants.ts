export const LINKS = {
  github: "https://github.com/iamwhitegod/arena",
  npm: "https://www.npmjs.com/package/@whitegodkingsley/arena-cli",
  issues: "https://github.com/iamwhitegod/arena/issues",
  feedback: "https://github.com/iamwhitegod/arena/issues",
  cloudAccess:
    "https://github.com/iamwhitegod/arena/issues/new?title=Reserve%20Arena%20Cloud%20access&body=Tell%20us%20about%20your%20video%20workflow%2C%20monthly%20source-video%20minutes%2C%20and%20the%20Cloud%20features%20you%20need.",
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
  oss: {
    name: "Arena OSS",
    price: "$0",
    priceSuffix: "free forever",
    badge: "Available now",
    description: "The complete local-first product for creators and developers.",
    features: [
      "Unlimited local processing",
      "Complete 4-layer editorial engine",
      "Captions and platform formatting",
      "Local storage, cache, and project artifacts",
      "Bring your own compute and OpenAI API key",
      "No account, watermark, or Arena usage quota",
    ],
    cta: "Install Arena",
    ctaHref: "/docs",
    highlighted: true,
  },
  creator: {
    name: "Cloud Creator",
    price: "$19",
    priceSuffix: "/month",
    badge: "Proposed",
    description: "Managed processing for individual creators publishing every week.",
    features: [
      "250 source-video minutes per month",
      "1 seat and 1 concurrent job",
      "50 GB hosted storage",
      "Full-HD exports",
      "30-day raw-media retention",
      "Hosted project history",
    ],
    cta: "Reserve Access",
    ctaHref: LINKS.cloudAccess,
    highlighted: false,
  },
  pro: {
    name: "Cloud Pro",
    price: "$49",
    priceSuffix: "/month",
    badge: "Proposed",
    description: "For professional creators, podcasts, marketers, and small teams.",
    features: [
      "750 source-video minutes per month",
      "3 seats and 3 concurrent jobs",
      "250 GB hosted storage",
      "Batch processing and brand templates",
      "Publishing, analytics, API, and webhooks",
      "Priority queue and support",
    ],
    cta: "Reserve Access",
    ctaHref: LINKS.cloudAccess,
    highlighted: false,
  },
  studio: {
    name: "Cloud Studio",
    price: "$149",
    priceSuffix: "/month",
    badge: "Proposed",
    description: "For agencies and production teams managing multiple shows or clients.",
    features: [
      "2,500 source-video minutes per month",
      "10 seats and 10 concurrent jobs",
      "1 TB hosted storage",
      "Client workspaces and approval workflows",
      "Shared brand kits and advanced analytics",
      "Higher API limits and priority support",
    ],
    cta: "Reserve Access",
    ctaHref: LINKS.cloudAccess,
    highlighted: false,
  },
} as const;
