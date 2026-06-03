---
name: security-review
description: Comprehensive security review covering 10 domains — secrets, input validation, SQL injection, auth, XSS, CSRF, rate limiting, data exposure, dependencies. Use for auth, user input, API endpoints, payments, sensitive data.
---

# Security Review

Activate for: authentication, user input handling, API endpoints, secret management, payment features, third-party integrations.

## 10 Security Domains

### 1. Secrets Management
- NEVER hardcode API keys or passwords
- Use environment variables exclusively
- `.env.local` in `.gitignore`
- No secrets in git history

### 2. Input Validation
- Use Zod schemas for type-safe validation
- File uploads: check size, MIME type, extension (whitelist)
- Prefer whitelist validation over blacklist

### 3. SQL Injection Prevention
- NEVER concatenate SQL
- Always use parameterized queries or ORM
- Drizzle handles this automatically

### 4. Authentication & Authorization
- Tokens in httpOnly cookies (not localStorage — vulnerable to XSS)
- Authorization checks before sensitive operations
- Enable Row Level Security on all tables

### 5. XSS Prevention
- Sanitize user HTML with DOMPurify
- Configure CSP headers
- Avoid `dangerouslySetInnerHTML` unless sanitized

### 6. CSRF Protection
- CSRF tokens for state-changing operations
- `SameSite=Strict` on cookies

### 7. Rate Limiting
- General: 100 requests / 15 min
- Expensive ops (AI, search): 10 requests / min

### 8. Sensitive Data Exposure
- Never log passwords or payment details
- Redact sensitive data in logs
- Generic error messages for users, detailed only in server logs

### 9. Dependency Security
- Run `npm audit` regularly
- Commit lock files
- Use `npm ci` in CI/CD

### 10. Error Handling
- Generic errors for users
- Detailed errors only in server logs
- Never leak stack traces

## Pre-Deployment Checklist

- [ ] No hardcoded secrets
- [ ] All inputs validated (Zod)
- [ ] SQL injection prevented (parameterized queries)
- [ ] XSS prevented (sanitization)
- [ ] CSRF protection on state-changing forms
- [ ] Auth checks on sensitive endpoints
- [ ] Rate limiting on API endpoints
- [ ] HTTPS enforced
- [ ] Security headers configured
- [ ] Error messages don't leak internals
- [ ] Sensitive data not logged
- [ ] Dependencies audited
- [ ] RLS enabled on database tables
- [ ] CORS configured correctly
- [ ] File uploads validated

## Automated Test Patterns

```typescript
// Auth test
it('returns 401 without token', async () => {
  const res = await fetch('/api/protected')
  expect(res.status).toBe(401)
})

// Authorization test
it('returns 403 for non-admin', async () => {
  const res = await fetch('/api/admin', { headers: { Authorization: `Bearer ${userToken}` }})
  expect(res.status).toBe(403)
})

// Input validation test
it('returns 400 for invalid input', async () => {
  const res = await fetch('/api/items', { method: 'POST', body: '{}' })
  expect(res.status).toBe(400)
})

// Rate limit test
it('returns 429 after limit exceeded', async () => {
  for (let i = 0; i < 101; i++) await fetch('/api/search')
  const res = await fetch('/api/search')
  expect(res.status).toBe(429)
})
```
