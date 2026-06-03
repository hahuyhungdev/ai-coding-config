---
name: api-design
description: REST API design conventions — resource naming, HTTP methods, status codes, pagination, filtering, auth, rate limiting, versioning. Use when designing endpoints, reviewing API contracts, or building public APIs.
---

# API Design Patterns

## Resource Design

- Resources are nouns, plural, lowercase, kebab-case
- Sub-resources express relationships: `/users/:id/orders`
- Verbs sparingly for non-CRUD: `/orders/:id/cancel`

## HTTP Methods

| Method | Idempotent | Safe | Use |
|--------|-----------|------|-----|
| GET | Yes | Yes | Read |
| POST | No | No | Create |
| PUT | Yes | No | Full replace |
| PATCH | No | No | Partial update |
| DELETE | Yes | No | Remove |

## Status Codes

- 200 OK, 201 Created, 204 No Content
- 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 409 Conflict, 422 Unprocessable, 429 Too Many Requests
- 500 Internal, 502 Bad Gateway, 503 Service Unavailable

Never return 200 for everything.

## Response Format

```json
// Success
{ "data": { ... } }

// Error
{ "error": { "code": "VALIDATION_ERROR", "message": "...", "details": [...] } }

// Paginated
{ "data": [...], "meta": { "total": 100, "page": 1, "limit": 10 }, "links": { "next": "...", "prev": "..." } }
```

## Pagination

**Offset-based** — simple, supports jump-to-page:
```
GET /items?offset=20&limit=10
```

**Cursor-based** — scalable, stable for large datasets:
```
GET /items?cursor=abc123&limit=10
```

Use cursor for >10k records, offset for smaller datasets.

## Filtering & Sorting

```
GET /items?status=active&price[gte]=100
GET /items?sort=-created_at,name
GET /items?fields=id,name,status
```

## Rate Limiting Headers

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

Tiers: anonymous 30/min, authenticated 1000/min, internal 10000/min.

## Versioning

URL path: `/api/v1/`
Max 2 active versions. Use `Sunset` header for deprecation.
Non-breaking changes (adding fields/endpoints) don't need version bump.

## Pre-Ship Checklist

- [ ] Resource naming correct
- [ ] Semantic status codes
- [ ] Input validation (Zod)
- [ ] Consistent error format
- [ ] Pagination on lists
- [ ] Auth on protected endpoints
- [ ] Rate limiting
- [ ] No sensitive data in responses
