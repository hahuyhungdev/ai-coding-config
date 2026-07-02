---
name: backend-pattern
description: Backend architecture patterns, API design, database optimization, and server-side best practices for Node.js, Express, and Next.js API routes.
---

# Backend Development & API Design Patterns

Conventions and best practices for designing consistent, developer-friendly REST APIs and writing scalable, high-performance server-side code.

## 1. REST API Design & Contracts

### URL Structure & Naming
- **Nouns, Plural, Lowercase, kebab-case:** multi-word resources must use kebab-case.
  - `GET /api/v1/team-members` (Good)
  - `GET /api/v1/team_members` or `GET /api/v1/getTeamMembers` (Bad)
- **Sub-resources for ownership relationships:**
  - `GET /api/v1/users/:id/orders`
- **Avoid verbs in CRUD paths:** Use HTTP methods semantically instead.

### HTTP Methods & Status Codes
- **GET:** Retrieve resources (Safe, Idempotent).
- **POST:** Create resources, trigger actions (Not Safe, Not Idempotent). Status: `201 Created` (include `Location` header).
- **PUT:** Full replacement of a resource (Idempotent). Status: `200 OK` or `204 No Content`.
- **PATCH:** Partial update of a resource (Not Safe, Not Idempotent by default).
- **DELETE:** Remove a resource (Idempotent). Status: `204 No Content`.
- **Client Errors:** `400 Bad Request` (validation), `401 Unauthorized` (missing auth), `403 Forbidden` (lack of permissions), `404 Not Found`, `422 Unprocessable Entity` (semantically invalid).
- **Server Errors:** `500 Internal Server Error` (unexpected failures; never leak database or stack details to the user).

### Success & Error JSON Format
- **Success Wrapper:**
  ```json
  {
    "data": {
      "id": "abc-123",
      "email": "alice@example.com"
    }
  }
  ```
- **Error Format:**
  ```json
  {
    "error": {
      "code": "validation_error",
      "message": "Request validation failed",
      "details": [
        { "field": "email", "message": "Must be valid email" }
      ]
    }
  }
  ```

### Pagination Patterns
- **Offset-Based:** `GET /api/v1/users?page=2&per_page=20` (use for admin panels, small datasets <10K).
- **Cursor-Based:** `GET /api/v1/users?cursor=eyJpZCI6MTI1fQ&limit=20` (use for infinite scroll, large feeds, or high-concurrency public APIs).

---

## 2. Server Architecture Patterns

### Repository Pattern (Data Access Abstraction)
```typescript
interface UserRepository {
  findById(id: string): Promise<User | null>;
  create(data: CreateUserDto): Promise<User>;
}
```

### Service Layer Pattern (Business Logic Isolation)
```typescript
class UserService {
  constructor(private userRepo: UserRepository) {}
  async registerUser(dto: CreateUserDto) {
    // business validation, hashing...
    return this.userRepo.create(dto);
  }
}
```

### Middleware Pipeline
Verify authentication/authorization, parsing, and logging inside clean middleware chains:
```typescript
export function withAuth(handler: NextApiHandler): NextApiHandler {
  return async (req, res) => {
    const token = req.headers.authorization?.replace('Bearer ', '');
    if (!token) return res.status(401).json({ error: 'Unauthorized' });
    try {
      req.user = await verifyToken(token);
      return handler(req, res);
    } catch {
      return res.status(401).json({ error: 'Invalid token' });
    }
  };
}
```

---

## 3. Database & Caching Optimization

### Prevent N+1 Query Problems
- Batch fetch relations instead of querying inside a loop:
```typescript
// GOOD: Batch query (1 database query)
const creatorIds = markets.map(m => m.creator_id);
const creators = await getUsers(creatorIds);
```

### SQL Transactions
- Use clean database transaction functions or Supabase RPC function calls to roll back automatically on failures:
```sql
BEGIN
  INSERT INTO markets VALUES (market_data);
  INSERT INTO positions VALUES (position_data);
EXCEPTION WHEN OTHERS THEN
  -- Rollback happens automatically
  RAISE;
END;
```

### Cache-Aside Caching (Redis)
- Query Redis cache first; fetch from database on cache miss, and populate cache with TTL (e.g. 300 seconds):
```typescript
const cached = await redis.get(`market:${id}`);
if (cached) return JSON.parse(cached);
const market = await db.markets.findUnique({ where: { id } });
if (market) await redis.setex(`market:${id}`, 300, JSON.stringify(market));
```

---

## 4. Server-Side Operations

### Role-Based Access Control (RBAC)
```typescript
const rolePermissions = {
  admin: ['read', 'write', 'delete'],
  user: ['read', 'write']
};
```

### Shared Rate-Limiting Stores
- Always use a shared backend store like Redis (never in-memory process counters) to track limits in load-balanced or serverless environments.

### Structured Logging (JSON)
- Output logs as JSON objects to standard output (never run log files locally). This ensures compatibility with centralized logging aggregation tools:
  ```json
  {"timestamp":"2026-07-02T06:50:00Z","level":"info","message":"Fetching users","requestId":"uuid-123"}
  ```
