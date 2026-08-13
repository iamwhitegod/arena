# Arena website

Arena is an AI-powered, open-source, local-first video clipping engine for the terminal that automatically finds the best moments in your videos and exports platform-ready clips for TikTok, Reels, and Shorts. This directory contains its Next.js 16 marketing and documentation website.

## Development

From `website/`:

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The main routes live under `src/app/`, reusable UI under `src/components/`, and global styles in `src/app/globals.css`.

## Checks

```bash
npm run lint
npm run build
```

Use the Node.js version supported by the root project policy. Read [`AGENTS.md`](./AGENTS.md) before changing the site because the installed Next.js version may differ from older conventions.

## Documentation sources

The website presents product documentation, but the repository Markdown remains canonical:

- [Documentation index](../docs/README.md)
- [Installation](../docs/getting-started/installation.md)
- [CLI reference](../docs/reference/cli.md)
- [Arena Cloud proposals](../docs/cloud/plan.md)

When website copy changes command behavior, installation requirements, pricing proposals, or support claims, update the canonical Markdown in the same change.
