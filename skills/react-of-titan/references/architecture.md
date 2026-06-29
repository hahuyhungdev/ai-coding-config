# React of Titan Architecture Reference

Read this file when adding a feature, reviewing a React repo, or resolving placement decisions.

## Directory Map

```text
src/
├── main.tsx
├── App.tsx
├── providers.tsx
├── router.tsx
├── pages/
├── features/
├── shared/
├── layouts/
└── styles/
```

## Placement Decisions

Use this order:

1. Used by two or more features: `shared/`.
2. A route-level screen: `pages/`.
3. A layout shell such as sidebar/header/outlet: `layouts/`.
4. Tied to one business capability: `features/<feature-name>/`.
5. Global app composition: root app shell files.

Some projects use a flat shared layer instead of a `shared/` folder:

```text
src/components/
src/hooks/
src/utils/
src/types.ts
```

When local instructions define this shape, treat those folders/files as the shared layer. Do not force a `src/shared/` migration unless the user explicitly asks for a broader restructuring.

Provider rule: implement a provider inside the owning feature when it depends on feature internals, export the provider from the feature index, and compose it in `providers.tsx`.

## Import Rules

Allowed imports:

| From | May import |
| --- | --- |
| `shared/` | external packages, `shared/` |
| `features/<name>/` | external packages, `shared/`, same-feature files |
| `pages/` | external packages, `shared/`, `layouts/`, feature public indexes |
| `layouts/` | external packages, `shared/` |
| app shell | everything |

Use `@/` for cross-layer imports:

```tsx
import { Button } from "@/shared/components/ui/Button";
import { ProductsSection } from "@/features/products";
```

Use relative paths inside a feature:

```tsx
import { ProductList } from "./components/ProductList";
import { useProducts } from "./hooks/useProducts";
```

If the target repo does not configure `@/`, follow its established relative-import style while preserving the same dependency direction.

## Naming

| Item | Pattern | Example |
| --- | --- | --- |
| Feature folder | kebab-case | `dashboard-stats` |
| Public feature component | PascalCase domain name | `DashboardStatsSection` |
| Internal component | Folder + `index.tsx` | `StatsCard/index.tsx` |
| Hook | `use` + PascalCase/camelCase domain | `useDashboardStats` |
| API file | camelCase + `Api` | `statsApi.ts` |
| Type file | kebab + `.types.ts` | `stats.types.ts` |
| Constants | `constants/index.ts` | `constants/index.ts` |
| Utils | camelCase | `formatStats.ts` |

Component implementation files must use the folder-index convention: `components/Foo/index.tsx`. Flag `components/Foo/Foo.tsx` as a structure mismatch.

## Feature Index Pattern

The feature index is a compound component and public API:

```tsx
import { StatsCard } from "./components/StatsCard";
import { useStats } from "./hooks/useStats";

export function StatsSection() {
  const { stats, isLoading, error } = useStats();

  if (isLoading) return <div className="page-loading">Loading stats...</div>;
  if (error) return <div role="alert">{error}</div>;

  return (
    <section aria-label="Key metrics">
      <StatsCard label="Total Users" value={stats.totalUsers} />
    </section>
  );
}

export default StatsSection;
```

Avoid `export { StatsSection } from "./components/StatsSection"` in a feature index. That turns the index into a barrel and hides the feature composition boundary.
Avoid exporting private internals unless there is a deliberate app-shell integration point, such as a feature-owned provider.

Do not create a feature-sized private component that owns the full screen composition:

```tsx
// Bad: features/conversations/components/ConversationViewer/index.tsx
import { useConversations } from "../../hooks/useConversations";
import { ChatView } from "../ChatView";
import { TokenStats } from "../TokenStats";
import { WorkspaceView } from "../WorkspaceView";
```

Move those imports to `features/conversations/index.tsx`. Keep `ChatView`, `TokenStats`, and `WorkspaceView` as private leaf components.

## Page Pattern

Pages compose features and stay thin:

```tsx
import { StatsSection } from "@/features/dashboard-stats";
import { ActivitySection } from "@/features/dashboard-activity";

export function DashboardPage() {
  return (
    <div className="page dashboard-page">
      <h1>Dashboard</h1>
      <StatsSection />
      <ActivitySection />
    </div>
  );
}

export default DashboardPage;
```

For tab-based SPAs without `pages/`, keep `App.tsx` as the composition boundary and still import only feature public indexes.

## Styling

- Prefer existing design tokens and local style system.
- Use CSS Modules or existing utility classes for component styles.
- Avoid JSX inline style props for normal UI styling; use class variants such as `status-open`, `priority-high`, or `is-selected`.
- Keep reusable primitives in `shared/components/ui/`.
- Keep business-specific components inside the feature.

## Testing

- Feature behavior: test the public feature component in `features/<feature>/__tests__/`.
- Shared utilities/hooks: colocate unit tests next to the source file.
- API/network behavior: prefer MSW to stubbing request clients.
- Critical flows: use E2E tests if the target repo already has them.

Minimum useful feature test:

```tsx
import { render, screen } from "@testing-library/react";
import { ProductsSection } from "@/features/products";

test("renders products", async () => {
  render(<ProductsSection />);
  expect(screen.getByText("Loading products...")).toBeInTheDocument();
  expect(await screen.findByRole("list", { name: /products/i })).toBeInTheDocument();
});
```

## Common Fixes

- Page imports `@/features/x/components/Y`: move that composition into `features/x/index.tsx` and import `@/features/x`.
- Feature imports sibling feature: move shared logic to `shared/` if truly reused, otherwise duplicate until reuse is real.
- Shared component contains business copy or API calls: move it into the owning feature.
- Route provider imports feature internals: export the provider from the feature index and import that public provider at app shell level.
- Inline style props: move static styles to CSS Modules or utility classes and express dynamic state through class names.
