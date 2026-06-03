---
name: coding-standards
description: Baseline cross-project coding conventions — naming, readability, immutability, KISS/DRY/YAGNI, TypeScript patterns, React patterns, API design. Use for new projects, code review, refactoring, onboarding.
---

# Coding Standards

Baseline conventions applicable across projects.
Use `frontend-patterns` for React-specific, `backend-patterns` for API-specific patterns.

## Core Principles

### Readability First
- Code is read more than written
- Clear variable and function names
- Self-documenting code preferred over comments

### KISS
- Simplest solution that works
- Avoid over-engineering
- Easy to understand > clever code

### DRY
- Extract common logic into functions
- Create reusable components
- Avoid copy-paste

### YAGNI
- Don't build features before they're needed
- Start simple, refactor when needed

## TypeScript Standards

### Naming
```typescript
// ✅ Descriptive names
const marketSearchQuery = 'election'
const isUserAuthenticated = true

// ❌ Unclear names
const q = 'election'
const flag = true
```

### Functions
```typescript
// ✅ Verb-noun pattern
async function fetchMarketData(id: string) { }
function isValidEmail(email: string): boolean { }

// ❌ Unclear
async function market(id: string) { }
function email(e) { }
```

### Immutability (CRITICAL)
```typescript
// ✅ Spread operator
const updatedUser = { ...user, name: 'New Name' }
const updatedArray = [...items, newItem]

// ❌ Never mutate
user.name = 'New Name'
items.push(newItem)
```

### Error Handling
```typescript
// ✅ Comprehensive
async function fetchData(url: string) {
  try {
    const response = await fetch(url)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    return await response.json()
  } catch (error) {
    console.error('Fetch failed:', error)
    throw new Error('Failed to fetch data')
  }
}
```

### Async/Await
```typescript
// ✅ Parallel when possible
const [users, markets] = await Promise.all([fetchUsers(), fetchMarkets()])

// ❌ Sequential when unnecessary
const users = await fetchUsers()
const markets = await fetchMarkets()
```

### Type Safety
```typescript
// ✅ Proper types
interface Market { id: string; name: string; status: 'active' | 'resolved' }
function getMarket(id: string): Promise<Market> { }

// ❌ Using any
function getMarket(id: any): Promise<any> { }
```

## React Patterns

### Component Structure
```typescript
interface ButtonProps {
  children: React.ReactNode
  onClick: () => void
  variant?: 'primary' | 'secondary'
}

export function Button({ children, onClick, variant = 'primary' }: ButtonProps) {
  return <button onClick={onClick} className={`btn btn-${variant}`}>{children}</button>
}
```

### State Updates
```typescript
// ✅ Functional update
setCount(prev => prev + 1)

// ❌ Can be stale
setCount(count + 1)
```

### Conditional Rendering
```typescript
// ✅ Clear
{isLoading && <Spinner />}
{error && <ErrorMessage error={error} />}

// ❌ Ternary hell
{isLoading ? <Spinner /> : error ? <ErrorMessage /> : data ? <Data /> : null}
```

## File Organization

- Components: PascalCase (`Button.tsx`)
- Hooks: camelCase with `use` prefix (`useAuth.ts`)
- Utils: camelCase (`formatDate.ts`)
- Types: camelCase with `.types` suffix

## Code Smells

### Long Functions (>50 lines)
Split into smaller functions.

### Deep Nesting (>4 levels)
Use early returns:
```typescript
if (!user) return
if (!user.isAdmin) return
// Do something
```

### Magic Numbers
```typescript
// ❌
if (retryCount > 3) { }

// ✅
const MAX_RETRIES = 3
if (retryCount > MAX_RETRIES) { }
```

## Comments

Explain WHY, not WHAT:
```typescript
// ✅ Explain reasoning
// Use exponential backoff to avoid overwhelming the API during outages
const delay = Math.min(1000 * Math.pow(2, retryCount), 30000)

// ❌ State the obvious
// Increment counter by 1
count++
```
