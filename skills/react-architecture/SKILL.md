---
name: react-architecture
description: Apply and validate feature-based architecture for Vite, React, and TypeScript apps. Use when creating, reviewing, or refactoring React features, component boundaries, route/page composition, feature public indexes, shared UI/utilities, or architecture checker/generator scripts.
---

# React Architecture

Use this skill to keep React apps organized by business feature with one-way dependencies, small public feature APIs, and deterministic architecture checks.

## When to Use

Use this skill when creating, reviewing, or refactoring React feature folders, shared layers, route/page composition, feature public indexes, or architecture checker/generator scripts. Do not use it for isolated visual styling that does not affect component boundaries.

## 1. Choose the App Shape

Detect the app shape before changing files:

- **Routed app:** `shared -> features -> pages -> app shell`
- **Tab SPA / no pages layer:** `shared -> features -> App.tsx/app shell`

Treat either `src/shared/*` or flat top-level `src/components`, `src/hooks`, `src/utils`, `src/types`, and `src/assets` as the shared layer. Use the existing shape; do not introduce `pages/`, `layouts/`, or `shared/` only because this skill mentions them.

## 2. Dependency Rules

- **Shared layer:** Reusable UI primitives, hooks, utilities, types, and assets. It must not import features, pages, layouts, or app shell files.
- **Features:** `src/features/<feature-name>/` modules. A feature may import shared code and its own private files only. It must not import sibling features.
- **Feature public index:** `features/<name>/index.tsx` is the public API and compound component. Compose feature hooks and private view components here. Do not make it a barrel file that re-exports internals, including `import { Foo } from "./components/Foo"; export { Foo }`.
- **Private feature components:** Keep these mostly presentational. They may compose same-feature components, but must not import feature hooks; move hook-driven composition to the feature index.
- **Pages, when present:** Pages compose shared components, layouts, and feature public indexes only. They must not import feature internals.
- **Layouts, when present:** Keep them app-generic and shared-only.
- **App shell:** `App.tsx`, `main.tsx`, providers, routers, and route registration may import any layer.

Import feature functionality through the feature public index:

```tsx
import { DashboardSection } from "@/features/dashboard";
```

The feature index must declare the public component:

```tsx
import { DashboardView } from "./components/DashboardView";
import { useDashboard } from "./hooks/useDashboard";

export function DashboardSection() {
  const state = useDashboard();
  return <DashboardView {...state} />;
}
```

Avoid reaching into feature internals:

```tsx
import { StatsCard } from "@/features/dashboard/components/StatsCard/StatsCard";
```

## 3. Naming and Structure

- Feature folders: kebab-case, for example `dashboard-stats/`
- Feature component folders/files: `components/Foo/index.tsx`
- Shared/common component folders/files: `components/Foo/index.tsx` or `shared/components/Foo/index.tsx`
- Hook files: `useThing.ts`
- API files: `thingApi.ts`
- Type files: `thing.types.ts` or `types.ts`
- Constants: `constants/index.ts`
- Utils: camelCase filenames

Keep code feature-local unless at least two features need it.

## 4. Scripts

Run scripts from the React app root, or pass the app root to the checker.

```bash
# From a React app root such as frontend/
node ../skills/react-architecture/scripts/check-architecture.mjs

# From this repo root against the frontend app
node skills/react-architecture/scripts/check-architecture.mjs frontend

# Generate a feature from the React app root
python3 ../skills/react-architecture/scripts/generate-feature.py user-profile

# Generate a component into a target components directory
python3 ../skills/react-architecture/scripts/generate-component.py status-badge src/components --scss
```

The feature generator creates:

- `features/<name>/index.tsx` as the public compound component
- `components/<Feature>View/index.tsx` as a presentational view
- `hooks/use<Feature>.ts`
- `api/<feature>Api.ts`
- `types/<feature>.types.ts`

Replace generated placeholder API behavior with the real request logic before shipping.

## 5. Validation

Use the checker after React architecture edits. It validates import boundaries, feature-index barrels, component folder naming, private component hook usage, and JSX inline style props.

```bash
python3 scripts/test_react_architecture_skill.py
node skills/react-architecture/scripts/check-architecture.mjs frontend
```

For app builds, also run the app's normal verification commands, for example `npm run build` and `npm run lint` from `frontend/`.
