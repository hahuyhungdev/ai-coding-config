---
name: react-of-titan
description: Apply React of Titan feature-based architecture for Vite, React, and TypeScript apps. Use when Codex is creating, refactoring, reviewing, or auditing React projects/features that should enforce shared/features/pages/app-shell layering, feature public indexes, React 19 patterns, route registration, tests, and architecture boundary checks.
---

# React of Titan

Use this skill to keep React applications organized by business feature, with one-way dependencies and thin route pages.

## First Pass

1. Inspect the target app's local instructions and scripts before editing.
2. Confirm the stack, routing style, and shared-layer shape. This skill assumes Vite + React + TypeScript and works best with React Router.
3. Prefer the target repo's established folder/file naming when it already follows React of Titan principles.
4. Read [references/architecture.md](references/architecture.md) when adding a feature, doing a boundary review, or deciding where code belongs.

## Layer Rules

Dependency flow:

```text
shared -> features -> pages -> app shell
```

- `shared/` may import external packages and other `shared/` code only.
- Some repos use flat shared folders (`src/components`, `src/hooks`, `src/utils`, `src/types.ts`) instead of `src/shared/`; treat those as the shared layer when that is the local convention.
- `features/<feature>/` may import `shared/` and same-feature files only.
- `pages/` may import `shared/`, `layouts/`, and feature public indexes only.
- `layouts/` should stay app-generic and import `shared/` only.
- App shell files such as `main.tsx`, `App.tsx`, `providers.tsx`, and `router.tsx` compose all layers. In tab-based SPAs without a `pages/` layer, `App.tsx` is the page/app composition boundary.

Never import feature internals from a page or another feature:

```tsx
// Good
import { StatsSection } from "@/features/dashboard-stats";

// Bad
import { StatsCard } from "@/features/dashboard-stats/components/StatsCard";
```

## Feature Shape

Each feature is a self-contained business module:

```text
src/features/<feature-name>/
├── index.tsx
├── api/
├── components/
├── constants/
├── hooks/
├── types/
└── utils/
```

Create only folders the feature actually needs. The feature `index.tsx` is the public boundary and should compose private internals into one exported feature component.
Do not use the feature index as a barrel such as `export { Foo } from "./components/Foo"`.
Component files must use the folder-index convention: `components/Foo/index.tsx`.
Do not hide feature composition inside a private component such as `components/ConversationViewer/index.tsx` that imports `ChatView`, `TokenStats`, `WorkspaceView`, and `useConversations`. Those imports belong in `features/conversations/index.tsx`; private components should be focused pieces used by that index.

```tsx
import { ProductList } from "./components/ProductList";
import { useProducts } from "./hooks/useProducts";

export function ProductsSection() {
  const { products, isLoading, error } = useProducts();
  if (isLoading) return <div className="page-loading">Loading products...</div>;
  if (error) return <div role="alert">{error}</div>;
  return <ProductList products={products} />;
}

export default ProductsSection;
```

## Add A Page-Backed Feature

1. Create `src/features/<feature-name>/` with feature-local components, hooks, API, types, utils, and styles as needed.
2. Export one public compound component from `src/features/<feature-name>/index.tsx`.
3. Create `src/pages/<route-name>/index.tsx`.
4. In the page, import only from `@/features/<feature-name>`.
5. Export both a named page component and a default export.
6. Register the route in `src/router.tsx` for explicit routing.
7. Add a navigation item in `src/layouts/MainLayout.tsx` only when the route belongs in primary navigation.
8. Add or update feature-level tests under `src/features/<feature-name>/__tests__/`.

## Implementation Defaults

- Use strict TypeScript and avoid `any` unless a third-party adapter requires a narrow escape hatch.
- Use `@/` for cross-layer imports when the target repo has that alias; otherwise preserve the local relative-import convention while keeping dependency direction intact.
- Move code to `shared/` only after at least two features need it.
- Keep API request functions in feature-local `api/` unless the client itself is shared infrastructure.
- Prefer React 19 patterns: `use()` for context reads, context objects as providers, and `ref` as a regular prop.
- Keep accessible form controls wired with `useId`, visible labels, `aria-invalid`, and `aria-describedby`.
- Use CSS Modules, existing utility classes, or the target repo's Tailwind setup. Do not use JSX `style={{ ... }}` for normal layout, spacing, color, typography, or state variants.
- For demo/reference data, feature hooks may own mock data. For network-bound behavior, test through MSW rather than stubbing request clients.

## Review Checklist

- Pages, routes, or tab-shell app components import features through feature indexes only.
- Features do not import sibling features.
- Shared code does not import app, layouts, pages, or features.
- Shared code is business-agnostic or used by at least two features.
- Feature indexes define the public feature component; they are not barrel files.
- Components live at `components/Foo/index.tsx`, including shared components.
- A private feature component must not act as the feature composer by importing sibling components and feature hooks; move that composition to `features/<name>/index.tsx`.
- Pages and layouts export both named and default components when the repo supports multiple routing strategies.
- Tests cover meaningful behavior, not just render smoke tests.

## Validation

Run the target repo's checks before finishing:

```bash
npm run format:check
npm run lint
npm run arch:check
npm run typecheck
npm test
npm run build
```

If the target repo does not have `npm run arch:check`, run the bundled checker from the target repo root:

```bash
node /path/to/react-of-titan/scripts/check-architecture.mjs
```

The checker assumes a `src/` directory, parses TypeScript imports, ignores tests, supports both `src/shared/` and flat shared folders, and reports layer violations, feature-index barrels, component file naming violations, plus JSX inline style props.
