---
name: react-pattern
description: Unified guidelines for React component composition, state management, React 19 APIs, and performance optimization.
origin: ECC
---

# Unified Frontend Development & Composition Guide

This guide compiles modern React composition patterns, state management strategies, performance guidelines, and React 19 updates into a single cohesive reference.

## When to Activate

- Designing React component APIs or building reusable component libraries
- Refactoring components suffering from boolean prop proliferation
- Implementing state management (Context, Zustand, useReducer)
- Applying performance optimizations (Memoization, virtualization, code splitting)
- Migrating to or writing code using React 19 features
- Working with forms, animations, and accessibility patterns

---

## 1. Component Architecture & Composition (HIGH)

### Composition Over Inheritance
Avoid deep inheritance. Compose components by nesting children to build flexible layouts.

```typescript
// PASS: GOOD: Component composition
interface CardProps {
  children: React.ReactNode
  variant?: 'default' | 'outlined'
}

export function Card({ children, variant = 'default' }: CardProps) {
  return <div className={`card card-${variant}`}>{children}</div>
}

export function CardHeader({ children }: { children: React.ReactNode }) {
  return <div className="card-header">{children}</div>
}

export function CardBody({ children }: { children: React.ReactNode }) {
  return <div className="card-body">{children}</div>
}

// Usage
<Card>
  <CardHeader>Title</CardHeader>
  <CardBody>Content</CardBody>
</Card>
```

### Avoid Boolean Prop Proliferation & Create Explicit Variants (`architecture-avoid-boolean-props`)
Do not use boolean flags (e.g., `isThread`, `isEditing`, `isDM`) to control UI layout. Each flag doubles the possible state paths and creates unmaintainable conditional logic. Instead, compose dedicated variants that share internals.

**Incorrect (monolithic component with exponential complexity):**
```tsx
function Composer({
  onSubmit,
  isThread,
  channelId,
  isDMThread,
  dmId,
  isEditing,
  isForwarding,
}: Props) {
  return (
    <form>
      <Header />
      <Input />
      {isDMThread ? (
        <AlsoSendToDMField id={dmId} />
      ) : isThread ? (
        <AlsoSendToChannelField id={channelId} />
      ) : null}
      {isEditing ? (
        <EditActions />
      ) : isForwarding ? (
        <ForwardActions />
      ) : (
        <DefaultActions />
      )}
      <Footer onSubmit={onSubmit} />
    </form>
  )
}
```

**Correct (explicit variants compose exactly what they need):**
```tsx
// Channel composer
function ChannelComposer() {
  return (
    <Composer.Frame>
      <Composer.Header />
      <Composer.Input />
      <Composer.Footer>
        <Composer.Attachments />
        <Composer.Formatting />
        <Composer.Emojis />
        <Composer.Submit />
      </Composer.Footer>
    </Composer.Frame>
  )
}

// Thread composer - adds "also send to channel" field
function ThreadComposer({ channelId }: { channelId: string }) {
  return (
    <Composer.Frame>
      <Composer.Header />
      <Composer.Input />
      <AlsoSendToChannelField id={channelId} />
      <Composer.Footer>
        <Composer.Formatting />
        <Composer.Emojis />
        <Composer.Submit />
      </Composer.Footer>
    </Composer.Frame>
  )
}
```

### Compound Components Pattern (`architecture-compound-components`)
Structure complex features with a shared context. Subcomponents access shared state via context rather than receiving drilling props.

```tsx
const ComposerContext = React.createContext<ComposerContextValue | null>(null)

export function ComposerProvider({ children, state, actions, meta }: ProviderProps) {
  return (
    <ComposerContext.Provider value={{ state, actions, meta }}>
      {children}
    </ComposerContext.Provider>
  )
}

export function ComposerFrame({ children }: { children: React.ReactNode }) {
  return <form>{children}</form>
}

export function ComposerInput() {
  const context = React.useContext(ComposerContext)
  if (!context) throw new Error('ComposerInput must be inside ComposerProvider')
  return (
    <TextInput
      ref={context.meta.inputRef}
      value={context.state.input}
      onChangeText={(text) => context.actions.update((s) => ({ ...s, input: text }))}
    />
  )
}

// Export compound object
export const Composer = {
  Provider: ComposerProvider,
  Frame: ComposerFrame,
  Input: ComposerInput,
}
```

### Prefer Composing Children Over Render Props (`patterns-children-over-render-props`)
Use `children` for layout and structural composition instead of `renderX` callback props. Children are more readable, compose naturally, and don't require understanding callback signatures.

**Incorrect (render props for structure is awkward and inflexible):**
```tsx
<Composer
  renderHeader={() => <CustomHeader />}
  renderFooter={() => <Formatting />}
  renderActions={() => <SubmitButton />}
/>
```

**Correct (compound components with children is flexible):**
```tsx
<Composer.Frame>
  <CustomHeader />
  <Composer.Input />
  <Composer.Footer>
    <Composer.Formatting />
    <SubmitButton />
  </Composer.Footer>
</Composer.Frame>
```

**Exception: When render props are appropriate:**
Render props are necessary and correct when a parent component must pass dynamic runtime data back to a child (such as list item renderers or lazy data loaders).
```tsx
// DataLoader passing fetched data back
<DataLoader<Market[]> url="/api/markets">
  {(markets, loading, error) => {
    if (loading) return <Spinner />
    if (error) return <Error error={error} />
    return <MarketList markets={markets!} />
  }}
</DataLoader>
```

---

## 2. State Management & Decoupling (MEDIUM)

### Decouple State Management from UI (`state-decouple-implementation`)
The provider component should be the only place that knows how state is managed. UI components consume the context interface—they don't know if state comes from local `useState`, global `Zustand`, or a server database sync.

```tsx
// UI component only knows about the context interface
function ChannelComposer() {
  return (
    <Composer.Frame>
      <Composer.Header />
      <Composer.Input />
      <Composer.Footer>
        <Composer.Submit />
      </Composer.Footer>
    </Composer.Frame>
  )
}

// Provider handles all state management details
function ChannelProvider({ channelId, children }: { channelId: string; children: React.ReactNode }) {
  const { state, update, submit } = useGlobalChannel(channelId)
  const inputRef = useRef(null)

  return (
    <Composer.Provider state={state} actions={{ update, submit }} meta={{ inputRef }}>
      {children}
    </Composer.Provider>
  )
}
```

### Generic Context Interfaces (`state-context-interface`)
Structure context values using three distinct keys: `state`, `actions`, and `meta`. This allows easy swapping of state providers without rewriting components.

```typescript
interface ComposerContextValue {
  state: {
    input: string
    isSubmitting: boolean
  }
  actions: {
    update: (updater: (s: ComposerState) => ComposerState) => void
    submit: () => void
  }
  meta: {
    inputRef: React.RefObject<HTMLInputElement>
  }
}
```

### Lift State to Providers (`state-lift-state`)
Keep state in dedicated Provider components so siblings and external UI elements can access it without prop drilling or using unstable ref hacks.

```tsx
function ForwardMessageDialog() {
  return (
    <ForwardMessageProvider>
      <Dialog>
        <Composer.Frame>
          <Composer.Input />
        </Composer.Frame>
        
        {/* Custom preview component lives outside Composer.Frame but inside Provider */}
        <MessagePreview />
      </Dialog>
    </ForwardMessageProvider>
  )
}
```

### Context + Reducer Pattern
For complex state logic, use a React Reducer to implement the `actions` interface.

```typescript
interface State {
  markets: Market[]
  loading: boolean
}

type Action =
  | { type: 'SET_MARKETS'; payload: Market[] }
  | { type: 'SET_LOADING'; payload: boolean }

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'SET_MARKETS':
      return { ...state, markets: action.payload }
    case 'SET_LOADING':
      return { ...state, loading: action.payload }
    default:
      return state
  }
}
```

---

## 3. React 19 API Migrations (MEDIUM)

> **⚠️ React 19+ only.** Skip this section if using React 18 or earlier.

### No `forwardRef` Wrapper (`react19-no-forwardref`)
In React 19, `ref` is passed as a regular prop. Do not wrap components in `forwardRef`.

**Incorrect (React 18 style):**
```tsx
const ComposerInput = forwardRef<TextInput, Props>((props, ref) => {
  return <TextInput ref={ref} {...props} />
})
```

**Correct (React 19 style):**
```tsx
function ComposerInput({ ref, ...props }: Props & { ref?: React.Ref<TextInput> }) {
  return <TextInput ref={ref} {...props} />
}
```

### Use `use()` Hook instead of `useContext()` (`react19-use-hook`)
The `use()` hook replaces `useContext()` and can be called conditionally within loops or branches.

**Incorrect:**
```tsx
const value = useContext(ComposerContext)
```

**Correct:**
```tsx
const value = use(ComposerContext)
```

---

## 4. Performance & Advanced Patterns (MEDIUM)

### Memoization
Use memoization selectively to prevent unnecessary renders in heavy components.

```typescript
// useMemo for calculations
const sortedMarkets = useMemo(() => {
  return markets.sort((a, b) => b.volume - a.volume)
}, [markets])

// useCallback for callbacks passed to memoized children
const handleSearch = useCallback((query: string) => {
  setSearchQuery(query)
}, [])
```

### Code Splitting & Lazy Loading
Split bundles by lazy loading large components.

```typescript
import { lazy, Suspense } from 'react'
const HeavyChart = lazy(() => import('./HeavyChart'))

export function Dashboard() {
  return (
    <Suspense fallback={<Spinner />}>
      <HeavyChart />
    </Suspense>
  )
}
```

### Virtualization
Virtualize lists exceeding 100 items to keep the DOM footprint small.

```typescript
import { useVirtualizer } from '@tanstack/react-virtual'

export function VirtualMarketList({ markets }: { markets: Market[] }) {
  const parentRef = useRef<HTMLDivElement>(null)
  const virtualizer = useVirtualizer({
    count: markets.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 100,
  })

  return (
    <div ref={parentRef} style={{ height: '600px', overflow: 'auto' }}>
      <div style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative' }}>
        {virtualizer.getVirtualItems().map(virtualRow => (
          <div
            key={virtualRow.index}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: `${virtualRow.size}px`,
              transform: `translateY(${virtualRow.start}px)`
            }}
          >
            <MarketCard market={markets[virtualRow.index]} />
          </div>
        ))}
      </div>
    </div>
  )
}
```

### Custom Hooks Patterns
Create specialized hooks for isolated, testable state behaviors.

```typescript
export function useToggle(initialValue = false): [boolean, () => void] {
  const [value, setValue] = useState(initialValue)
  const toggle = useCallback(() => setValue(v => !v), [])
  return [value, toggle]
}

export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)
  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay)
    return () => clearTimeout(handler)
  }, [value, delay])
  return debouncedValue
}
```

### Form Handling Patterns
Use controlled forms combined with synchronous validation patterns.

```typescript
export function CreateMarketForm() {
  const [formData, setFormData] = useState({ name: '' })
  const [errors, setErrors] = useState<Record<string, string>>({})

  const validate = () => {
    const newErrors: Record<string, string> = {}
    if (!formData.name.trim()) newErrors.name = 'Name is required'
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (validate()) {
      // submit data
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <input value={formData.name} onChange={e => setFormData({ name: e.target.value })} />
      {errors.name && <span className="error">{errors.name}</span>}
      <button type="submit">Submit</button>
    </form>
  )
}
```

### Error Boundary Pattern
Isolate component tree crashes via a React Class ErrorBoundary component.

```typescript
export class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error: Error | null }
> {
  state = { hasError: false, error: null }
  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }
  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error boundary:', error, errorInfo)
  }
  render() {
    if (this.state.hasError) {
      return <div>Something went wrong: {this.state.error?.message}</div>
    }
    return this.props.children
  }
}
```

### Animation Patterns (Framer Motion)
```typescript
import { motion, AnimatePresence } from 'framer-motion'

export function FadeIn({ children }: { children: React.ReactNode }) {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      {children}
    </motion.div>
  )
}
```

### Accessibility Patterns
Use keyboard navigation hooks and focus management on modals.

```typescript
export function Modal({ isOpen, onClose, children }: ModalProps) {
  const modalRef = useRef<HTMLDivElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (isOpen) {
      previousFocusRef.current = document.activeElement as HTMLElement
      modalRef.current?.focus()
    } else {
      previousFocusRef.current?.focus()
    }
  }, [isOpen])

  return isOpen ? (
    <div ref={modalRef} role="dialog" aria-modal="true" tabIndex={-1}>
      {children}
    </div>
  ) : null
}
```
