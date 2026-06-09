# Graphify FAQ

**Last Updated:** 2026-06-09
**Covers:** Frequently asked questions about Graphify usage

---

## 📚 Table of Contents

1. [Basic Usage](#basic-usage)
2. [Query Types](#query-types)
3. [Quota & Limits](#quota--limits)
4. [Performance](#performance)
5. [Troubleshooting](#troubleshooting)
6. [Advanced Usage](#advanced-usage)

---

## Basic Usage

### Q: What is Graphify?

**A:** Graphify is a knowledge graph system that indexes your codebase and allows you to query it using natural language. Instead of reading files one by one, you can ask questions and get structured answers.

**Example:**
```bash
rtk graphify query "what is the main architecture of this project?"
```

---

### Q: How do I install Graphify?

**A:** Run the installer with graphify flag:

```bash
python3 install.py --claude --project /path/to/your/project
```

This will:
1. Generate graphify-out/ directory
2. Create graph.json with codebase structure
3. Configure hooks for Claude Code
4. Set up CLAUDE.md with graphify rules

---

### Q: What can I ask Graphify?

**A:** You can ask about:

1. **Architecture:**
   ```bash
   rtk graphify query "project structure and main components"
   ```

2. **Dependencies:**
   ```bash
   rtk graphify query "how do libraries depend on each other?"
   ```

3. **Data flow:**
   ```bash
   rtk graphify query "trace authentication flow from login to API"
   ```

4. **Specific code:**
   ```bash
   rtk graphify query "TradingBot class and its methods"
   ```

5. **Boundaries:**
   ```bash
   rtk graphify query "what are the architectural boundaries?"
   ```

---

### Q: How is Graphify different from grep/find?

**A:** 

| Feature | grep/find | Graphify |
|---------|-----------|----------|
| **Output** | Raw text matches | Structured knowledge |
| **Context** | Line-by-line | Full codebase understanding |
| **Relationships** | None | Dependency graphs |
| **Architecture** | None | High-level overview |
| **Token usage** | High | Low (35-45% savings) |

**Example:**

```bash
# grep: Returns matching lines
grep "class TradingBot" *.py

# Graphify: Returns full class structure
rtk graphify query "TradingBot class and its methods"
```

---

## Query Types

### Q: What's the difference between query, explain, and path?

**A:**

| Command | Purpose | Use case |
|---------|---------|----------|
| `query` | General questions | "What is the architecture?" |
| `explain` | Deep dive into concept | "Explain the tag system" |
| `path` | Find relationships | "Path from A to B" |

**Examples:**

```bash
# Query: General question
rtk graphify query "main components"

# Explain: Deep dive
rtk graphify explain "TradingBot workflow"

# Path: Relationships
rtk graphify path "front-office" "fe-shared"
```

---

### Q: When should I use query vs explain?

**A:**

**Use `query` when:**
- Asking about structure
- Finding components
- Understanding organization
- General architecture questions

**Use `explain` when:**
- Deep diving into specific concept
- Understanding detailed workflow
- Learning how something works
- Need step-by-step explanation

**Example:**

```bash
# Query: Find components
rtk graphify query "authentication components"

# Explain: Understand flow
rtk graphify explain "authentication flow"
```

---

### Q: How do I find relationships between files?

**A:** Use `path` command:

```bash
# Find path between two components
rtk graphify path "front-office" "fe-shared"

# Find all dependencies
rtk graphify path "TradingBot" "RuntimeDB"
```

**Output shows:**
- Direct connections
- Intermediate nodes
- Relationship types (calls, imports, contains)

---

## Quota & Limits

### Q: Why am I blocked after 3 queries?

**A:** Graphify has a per-session quota of 3 discovery calls to prevent abuse and optimize token usage.

**Quota breakdown:**
- 1 initial query (required)
- 2 follow-up queries (optional)
- 3rd query: BLOCKED

**Solutions:**

1. **Start new session:**
   ```bash
   claude  # New session resets quota
   ```

2. **Use bypass (temporary):**
   ```bash
   GRAPHIFY_BYPASS=1 claude -p "your question"
   ```

3. **Synthesize from available context:**
   - Review previous results
   - Use GRAPH_REPORT.md
   - Read specific files

---

### Q: How do I reset the quota?

**A:** 

1. **Automatic reset:** Start new Claude session
2. **Manual reset:** Delete quota file
   ```bash
   rm -f /tmp/ai-coding-config-graphify-*.count
   ```
3. **Bypass:** Use GRAPHIFY_BYPASS=1

---

### Q: Can I increase the quota?

**A:** Currently, quota is fixed at 3 per session. This is by design to:
- Prevent token waste
- Encourage focused queries
- Optimize cost

**Workarounds:**
1. Use more specific queries
2. Start new sessions for new topics
3. Use GRAPHIFY_BYPASS=1 when needed

---

## Performance

### Q: Why is Graphify slow?

**A:** Possible causes:

1. **Large codebase:**
   ```bash
   # Check graph size
   ls -lh graphify-out/graph.json
   ```

2. **Complex query:**
   ```bash
   # Use simpler query
   rtk graphify query "main components" --depth=1
   ```

3. **Cache miss:**
   ```bash
   # Regenerate graph
   graphify update .
   ```

---

### Q: How do I speed up queries?

**A:**

1. **Use scoped queries:**
   ```bash
   rtk graphify query "auth module" --scope="libs/auth"
   ```

2. **Limit depth:**
   ```bash
   rtk graphify query "main components" --depth=1
   ```

3. **Use specific terms:**
   ```bash
   # Slow
   rtk graphify query "everything about the project"
   
   # Fast
   rtk graphify query "TradingBot class methods"
   ```

---

### Q: How much tokens does Graphify save?

**A:** Based on testing:

| Metric | Without Graphify | With Graphify | Savings |
|--------|------------------|---------------|---------|
| **Input tokens** | ~100k | ~60k | **40%** |
| **API turns** | 20-30 | 5-10 | **60%** |
| **Cost** | $0.80-1.00 | $0.40-0.50 | **50%** |

**Real test results (nx-monorepo-workspace):**
- 5 test cases completed
- Average token savings: 37%
- Average turn reduction: 50%
- Accuracy: 100%

---

## Troubleshooting

### Q: Graphify query returns no results

**A:** Check:

1. **Graph exists:**
   ```bash
   ls -la graphify-out/graph.json
   ```

2. **Graph is up to date:**
   ```bash
   graphify update .
   ```

3. **Query is specific enough:**
   ```bash
   # Too broad
   rtk graphify query "code"
   
   # Better
   rtk graphify query "authentication module"
   ```

---

### Q: Graphify returns wrong results

**A:** Possible causes:

1. **Graph outdated:**
   ```bash
   graphify update .
   ```

2. **Query ambiguous:**
   ```bash
   # Ambiguous
   rtk graphify query "auth"
   
   # Specific
   rtk graphify query "authentication flow from login to API"
   ```

3. **Graph corrupted:**
   ```bash
   rm -rf graphify-out/
   graphify update .
   ```

---

### Q: Hook blocks Graphify commands

**A:** This shouldn't happen. If it does:

1. **Check settings:**
   ```bash
   cat .claude/settings.json | grep graphify
   ```

2. **Debug hook:**
   ```bash
   GRAPHIFY_DEBUG=1 rtk graphify query "test"
   ```

3. **Reinstall:**
   ```bash
   python3 install.py --claude --force
   ```

---

## Advanced Usage

### Q: How do I query specific file types?

**A:** Use context_filter:

```bash
# Only Python files
rtk graphify query "authentication" --context-filter="py"

# Only TypeScript files
rtk graphify query "components" --context-filter="ts"

# Only test files
rtk graphify query "test coverage" --context-filter="test"
```

---

### Q: How do I find all callers of a function?

**A:** Use path command:

```bash
# Find what calls TradingBot
rtk graphify path "*" "TradingBot"

# Find what TradingBot calls
rtk graphify path "TradingBot" "*"
```

---

### Q: How do I understand complex workflows?

**A:** Combine query and explain:

```bash
# Step 1: Get overview
rtk graphify query "authentication components"

# Step 2: Deep dive
rtk graphify explain "authentication flow"

# Step 3: Find relationships
rtk graphify path "login" "API"
```

---

### Q: How do I use Graphify with Claude Code?

**A:** Claude Code automatically uses Graphify when:

1. **Asking architecture questions:**
   ```
   User: "What is the main architecture?"
   Claude: Uses graphify query internally
   ```

2. **Exploring codebase:**
   ```
   User: "How does authentication work?"
   Claude: Uses graphify explain internally
   ```

3. **Finding relationships:**
   ```
   User: "What depends on fe-shared?"
   Claude: Uses graphify path internally
   ```

**No manual intervention needed!**

---

### Q: Can I use Graphify outside Claude Code?

**A:** Yes! Use CLI directly:

```bash
# Basic query
rtk graphify query "your question"

# With options
rtk graphify query "your question" --depth=2 --scope="libs"

# Generate report
rtk graphify report > GRAPH_REPORT.md
```

---

## 📚 Related Documentation

- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions
- [Hook Improvements](../HOOK_IMPROVEMENTS.md) - Hook system changes
- [README](../README.md#graphify) - Graphify documentation
- [Improvement Plan](../IMPROVEMENT_PLAN.md) - Overall roadmap

---

**Last Updated:** 2026-06-09
**Maintainer:** AI Assistant