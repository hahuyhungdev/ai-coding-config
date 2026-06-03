# Security Guidelines

## Mandatory Checks Before ANY Commit

- [ ] No hardcoded secrets (API keys, passwords, tokens)
- [ ] All user inputs validated
- [ ] SQL injection prevention (Drizzle parameterized queries)
- [ ] XSS prevention (React auto-escapes, but check `dangerouslySetInnerHTML`)
- [ ] Error messages don't leak sensitive data
- [ ] Rate limiting on API endpoints that call external services

## Secret Management

- NEVER hardcode secrets in source code
- ALWAYS use environment variables via `.env.local`
- Validate that required secrets are present at startup
- Rotate any secrets that may have been exposed

## This Project's Secrets

- `DATABASE_URL` — PostgreSQL connection
- `DEEPSEEK_API_KEY` — AI feedback
- `GOOGLE_TTS_API_KEY` — Text-to-speech
- `SUPADATA_API_KEY` — YouTube transcript

## Security Response Protocol

If security issue found:
1. STOP immediately
2. Use **security-reviewer** agent
3. Fix CRITICAL issues before continuing
4. Rotate any exposed secrets
5. Review entire codebase for similar issues
