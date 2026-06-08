# RTK + Graphify Benchmark

## Real Session Data (28 Claude Sessions)

Tested on a medium-sized Next.js codebase. Compared **Graphify queries** vs **Raw grep + file reads** across 28 independent Claude sessions.

### Overall Results

| Metric | With Graphify | Without (Raw) | Savings |
|--------|--------------|---------------|---------|
| Total output tokens | 1,359 | ~400,000 | **99.7%** |
| Avg tokens/query | 18 | ~8,000 | 7,982 |
| Avg tokens/session | 48 | ~14,000 | 13,952 |
| Total graphify calls | 74 | — | — |

### Per-Query Comparison

| Approach | Tokens/query | What happens |
|----------|-------------|--------------|
| **Graphify** | ~18 | `graphify query` → scoped subgraph JSON |
| **Raw** | ~8,000 | `grep -r` → list 5-20 files → `Read` each → summarize |

### Session Highlights

| Session | Graphify calls | Graphify tokens | Raw estimate | Savings |
|---------|---------------|-----------------|--------------|---------|
| Architecture overview | 6 | ~200 | ~48,000 | 99.6% |
| Directory structure | 6 | ~150 | ~48,000 | 99.7% |
| Auth flow trace | 9 | ~300 | ~72,000 | 99.6% |
| Feature deep-dive | 11 | ~123 | ~88,000 | 99.9% |

### Token Cost Breakdown

```
Graphify query command:     ~18 tokens (input)
Graphify subgraph result:   ~50-200 tokens (output)
Total per query:            ~70-220 tokens

Raw grep command:           ~18 tokens (input)
Grep output (20 matches):   ~500-2,500 tokens (output)
Read file 1:                ~750-2,000 tokens
Read file 2:                ~750-2,000 tokens
... (5-20 files)
Total per query:            ~5,000-50,000 tokens
```

---

## Synthetic Benchmark (50 Cases)

Controlled test across 5 categories. Compared **RTK+Graphify** (graphify-out included) vs **Raw commands** (graphify-out excluded). Both exclude `node_modules/` and `dist/`.

### Results

| Metric | RTK+Graphify | Raw | Savings |
|--------|--------------|-----|---------|
| Total tokens | 85,649 | 361,073 | **275,424 (76%)** |
| Avg tokens/case | 1,712 | 7,221 | 5,509 |
| Avg time/case | 221ms | 49ms | -172ms |

### By Category

| Category | RTK(tk) | Raw(tk) | Save% |
|----------|---------|---------|-------|
| Frontend | 15,888 | 40,343 | 60% |
| Backend | 23,310 | 113,505 | 79% |
| Security | 18,160 | 133,017 | 86% |
| DevOps | 16,971 | 51,336 | 66% |
| Testing | 11,320 | 22,872 | 50% |

### Top Savings

| Case | RTK(tk) | Raw(tk) | Save% |
|------|---------|---------|-------|
| Security patterns | 2,311 | 109,117 | 97% |
| Server setup | 3,390 | 61,888 | 94% |
| Unit test patterns | 535 | 9,361 | 94% |
| Package management | 2,102 | 28,859 | 92% |
| API design | 3,302 | 15,970 | 79% |

### Worst Cases (RTK uses more)

| Case | RTK(tk) | Raw(tk) | Waste% |
|------|---------|---------|--------|
| CORS policy | 2,981 | 821 | -263% |
| Nginx config | 2,811 | 875 | -221% |
| Monitoring setup | 2,571 | 956 | -168% |

---

## Key Takeaways

1. **Graphify saves ~99% tokens** on broad codebase queries (architecture, features, cross-file relationships)
2. **Raw grep is better** for narrow lookups (<5 matching files) — graphify overhead exceeds savings
3. **Rule of thumb:** Topic spans >5 files → use graphify. Otherwise → grep directly.
4. **RTK compounds savings** by compacting raw command output before it reaches the model

### When to Use What

```
Query type              → Approach         → Tokens
─────────────────────────────────────────────────────
"architecture overview" → graphify query   → ~200
"feature modules"       → graphify query   → ~150
"auth flow"             → graphify query   → ~300
"where is CORS config"  → grep + read      → ~2,000
"fix this function"     → read raw file    → ~500
```
