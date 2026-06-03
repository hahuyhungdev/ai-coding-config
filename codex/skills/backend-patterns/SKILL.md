---
name: backend-patterns
description: Backend architecture patterns — layered architecture, database optimization, caching, error handling, auth, rate limiting, background jobs. Use when designing API endpoints, optimizing queries, or building server-side logic.
---

# Backend Patterns

## Layered Architecture

```
Route/Controller → Service → Repository → Database
```

- Route: validate input, call service, return response
- Service: business logic, orchestration
- Repository: data access abstraction

## Middleware Pattern

```typescript
function withAuth(handler: Function) {
  return async (req: NextRequest) => {
    const token = req.headers.get('authorization')?.split(' ')[1]
    if (!token) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    const user = await verifyToken(token)
    return handler(req, user)
  }
}
```

## Database Patterns

### Query Optimization
```typescript
// ✅ Select only needed columns
const { data } = await db.select().from(items).columns(['id', 'name'])

// ❌ Select everything
const { data } = await db.select().from(items)
```

### N+1 Prevention
```typescript
// ✅ Batch fetch
const orders = await db.select().from(orderItems).where(inArray(orderItems.orderId, orderIds))
const ordersByOrder = new Map(orders.map(o => [o.orderId, o]))

// ❌ N+1
for (const order of orderList) {
  order.items = await db.select().from(orderItems).where(eq(orderItems.orderId, order.id))
}
```

## Caching

```typescript
const cacheKey = `user:${userId}`
const cached = await redis.get(cacheKey)
if (cached) return JSON.parse(cached)

const user = await db.select().from(users).where(eq(users.id, userId))
await redis.setex(cacheKey, 300, JSON.stringify(user))
return user
```

## Error Handling

```typescript
class ApiError extends Error {
  constructor(public statusCode: number, message: string, public details?: any) {
    super(message)
  }
}

// Centralized handler
function handleError(error: unknown) {
  if (error instanceof ApiError) return NextResponse.json({ error: { code: error.name, message: error.message, details: error.details } }, { status: error.statusCode })
  if (error instanceof z.ZodError) return NextResponse.json({ error: { code: 'VALIDATION', details: error.errors } }, { status: 400 })
  return NextResponse.json({ error: { code: 'INTERNAL', message: 'Internal error' } }, { status: 500 })
}
```

## Rate Limiting

```typescript
const rateLimit = new Map<string, { count: number; reset: number }>()

function checkRateLimit(ip: string, limit = 100, windowMs = 900000): boolean {
  const now = Date.now()
  const entry = rateLimit.get(ip)
  if (!entry || now > entry.reset) { rateLimit.set(ip, { count: 1, reset: now + windowMs }); return true }
  if (entry.count >= limit) return false
  entry.count++; return true
}
```

## Background Jobs

```typescript
const jobQueue: Array<() => Promise<void>> = []

async function processJobs() {
  while (jobQueue.length > 0) {
    const job = jobQueue.shift()!
    try { await job() } catch (e) { console.error('Job failed:', e) }
  }
}

function enqueueJob(job: () => Promise<void>) {
  jobQueue.push(job)
  if (jobQueue.length === 1) processJobs()
}
```

## Logging

```typescript
function log(level: string, message: string, meta?: object) {
  console.log(JSON.stringify({ timestamp: new Date().toISOString(), level, message, ...meta }))
}
```
