---
name: nextjs-turbopack
description: Next.js 16+ Turbopack dev bundler — faster cold start, HMR, file-system caching. Use when developing or debugging Next.js apps, diagnosing slow dev startup, or optimizing bundles.
---

# Next.js and Turbopack

Next.js 16+ uses Turbopack by default for local dev: incremental Rust-based bundler.

## When to Use

- **Turbopack (default dev)**: Day-to-day development. Faster cold start and HMR.
- **Webpack (legacy dev)**: Only for Turbopack bugs or webpack-only plugins. Disable with `--webpack`.
- **Production**: `next build` may use Turbopack or webpack depending on version.

## Commands

```bash
next dev          # Dev with Turbopack (default)
next build        # Production build
next start        # Production server
```

## How It Works

- Incremental bundler: only rebuilds changed files
- File-system caching: restarts reuse previous work (5-14x faster on large projects)
- Cache stored under `.next/`
- No extra config needed for basic use

## Bundle Analyzer (16.1+)

Experimental tool to inspect output and find heavy dependencies.
Enable via config or experimental flag (check docs for your version).

## Best Practices

- Stay on recent Next.js 16.x for stable Turbopack
- If dev is slow, verify Turbopack is active (default) and cache isn't being cleared
- For production bundle size, use official Next.js bundle analysis
- Prefer App Router and server components where possible
- Use `dynamic()` for heavy client components
