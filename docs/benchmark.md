# RTK + Graphify Benchmark

50 cases across 5 categories. Compared **RTK+Graphify** (graphify-out included) vs **Raw commands** (graphify-out excluded). Both exclude `node_modules/` and `dist/`.

## Results

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

## When to Use Graphify

**Use graphify query** for broad topics (>5 matching files):
- `security`, `server`, `API`, `state`, `component`, `form`, `build`, `package`
- Saves up to **97%** tokens when raw grep matches many files

**Use raw grep** for narrow topics (<5 matching files):
- `CORS`, `nginx`, `JWT`, `animation`, `mock`, `fixture`, `assertion`
- Graphify query overhead exceeds raw grep savings

**Rule of thumb:** If a topic has <5 file matches in the codebase, skip graphify and grep directly.

## Top Savings

| Case | RTK(tk) | Raw(tk) | Save% |
|------|---------|---------|-------|
| Security patterns | 2,311 | 109,117 | 97% |
| Server setup | 3,390 | 61,888 | 94% |
| Unit test patterns | 535 | 9,361 | 94% |
| Package management | 2,102 | 28,859 | 92% |
| API design | 3,302 | 15,970 | 79% |

## Worst Cases (RTK uses more)

| Case | RTK(tk) | Raw(tk) | Waste% |
|------|---------|---------|--------|
| CORS policy | 2,981 | 821 | -263% |
| Nginx config | 2,811 | 875 | -221% |
| Monitoring setup | 2,571 | 956 | -168% |

## Key Takeaway

RTK + Graphify saves **76% tokens on average** but costs ~170ms extra per query. The time cost is negligible compared to token savings — especially when context window is limited to 200k tokens.
