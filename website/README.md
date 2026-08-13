# Arena website

The Arena marketing and documentation website is a Next.js 16 application in the main Arena repository.

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
