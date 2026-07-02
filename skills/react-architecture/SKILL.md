---
name: react-architecture
description: Apply React feature-based architecture for Vite, React, and TypeScript apps. Enforces shared/features/pages/app-shell layering, feature public indexes, React 19 patterns, route registration, and architecture boundary checks.
---

# React of Titan Architecture

Use this skill to keep React applications organized by business feature, with one-way dependencies and thin route pages.

## 1. Layer Rules & Dependency Flow

Ensure all file imports respect the one-way dependency flow:
```text
shared -> features -> pages -> app shell
```

- **shared/**: Presentation-only primitives (Design System) and technical helper utilities. CANNOT import from features, pages, or app shell.
- **features/<feature-name>/**: Self-contained business modules. CANNOT import from pages, app shell, or sibling features. Must only import from shared/ and feature-local files (using relative imports).
  - Internal structure:
    - `index.tsx`: Public API (Compound Component export).
    - `components/`: UI sub-components (private).
    - `hooks/`: Feature-scoped state & hooks (private).
    - `api/`: API request clients (private).
    - `types/`: Domain-specific types (private).
    - `utils/`: Private utility functions (private).
- **pages/**: Route views. Composes features. Can import from shared/, layouts/, and feature public indexes. Cannot import from root entry files. Must only import feature components through the feature's public `index` file.
- **layouts/**: Should stay app-generic and import shared/ only.
- **App Shell (src/)**: Global setup (`main.tsx`, `App.tsx`, `providers.tsx`, `router.tsx`, `routes.ts`). Can import from any layer.

> [!WARNING]
> Never import feature internals from a page or another feature. For example, import from `@/features/dashboard` instead of `@/features/dashboard/components/StatsCard`.

---

## 2. Naming Conventions (Strict)

These conventions must be followed without exception to match the project's standard (`AGENTS.md`):

- **Feature folders**: kebab-case (e.g. `dashboard-stats`)
- **Component**: Folder + PascalCase file (e.g. `StatsCard/StatsCard.tsx`, NOT `components/Foo/index.tsx`)
- **Page**: Folder + PascalCase file (e.g. `Dashboard/DashboardPage.tsx`)
- **Hook files**: `use` + camelCase (e.g. `useStats.ts`)
- **API files**: camelCase + `Api` (e.g. `statsApi.ts`)
- **Type files**: kebab-case + `.types.ts` or single `types.ts`
- **Constants**: `index.ts` inside `constants/` folder
- **Utils**: camelCase (e.g. `formatStats.ts`)

---

## 3. Shared Component Separation

- `shared/components/ui/`: Contains atomic, presentation-only primitives of the Design System (e.g. `Button/Button.tsx`, `Input/Input.tsx`, `Spinner/Spinner.tsx`). They must not have business logic or complex state.
- `shared/components/` (outside `ui/`): Contains technical, business-agnostic helper components (e.g. `ErrorBoundary/ErrorBoundary.tsx`, `FileUploader/FileUploader.tsx`, `Form/Form.tsx`).

---

## 4. Routing Strategy Guidelines

Read `ai-settings.json` at the project root to detect the active `"routing"` strategy (`"explicit"`, `"vite-plugin-pages"`, or `"framework"`):

- **For `"explicit"`**: Manually register new pages in `src/router.tsx` using named component imports.
- **For `"vite-plugin-pages"`**: Create pages in `src/pages/` (they will be auto-scanned).
- **For `"framework"`**: Register pages in `src/routes.ts` and ensure default exports.

To maintain cross-strategy compatibility, all components (pages and layouts) should export both **named** and **default** exports.

---

## 5. Automation & Validation Scripts

### Scaffolding Scripts:
* **Generate a complete new Feature:**
  ```bash
  python3 skills/react-architecture/scripts/generate-feature.py <feature-name>
  ```
* **Generate a new Component inside a folder:**
  ```bash
  python3 skills/react-architecture/scripts/generate-component.py <ComponentName> <TargetDirectory> [--scss]
  ```

### Architecture Checker:
Run the bundled checker from the repository root to validate layer boundaries:
```bash
node skills/react-architecture/scripts/check-architecture.mjs
```
*(The checker parses imports, checks layer boundaries, and reports component naming or JSX inline style violations).*

---

## 6. Review Checklist

- Pages, routes, or app components import features through feature indexes only.
- Features do not import sibling features.
- Shared code does not import app, layouts, pages, or features.
- Shared code is business-agnostic or used by at least two features.
- Feature indexes define the public feature component; they are not barrel files.
- Components live at `components/Foo/Foo.tsx` (or `shared/components/ui/Bar/Bar.tsx`), matching the PascalCase file name.
- A private feature component must not act as the feature composer by importing sibling components and feature hooks; move that composition to `features/<name>/index.tsx`.
- Pages and layouts export both named and default components when the repo supports multiple routing strategies.
