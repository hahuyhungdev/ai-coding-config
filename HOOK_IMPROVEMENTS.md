# Hook System Improvements

**Created:** 2026-06-09
**Status:** In Progress
**Goal:** Make hooks less aggressive, more debuggable, and user-friendly

---

## 🐛 Current Problems

### Problem 1: Too Aggressive Blocking
**Symptom:** Hook blocks legitimate operations like:
- Reading IMPROVEMENT_PLAN.md for editing
- Finding hook files for debugging
- Running claude CLI commands

**Root Cause:** Hook checks file extensions (.py, .ts, .md) without context

### Problem 2: Poor Error Messages
**Symptom:** Generic message "BLOCKED by graphify hook" without actionable guidance

**Root Cause:** No context about WHY something was blocked or HOW to fix it

### Problem 3: No Debug Mode
**Symptom:** Can't see what hook is checking or why it blocked

**Root Cause:** No verbose logging option

### Problem 4: No Bypass Mechanism
**Symptom:** Hook blocks everything, even when user explicitly wants to override

**Root Cause:** No escape hatch for power users

---

## ✅ Proposed Solutions

### Solution 1: Context-Aware Blocking
**Approach:** Check if read is for "exploration" vs "editing/debugging"

**Implementation:**
- Allow reads when file is being modified (Edit tool context)
- Allow reads when debugging (error messages, test failures)
- Block only pure exploration reads

### Solution 2: Actionable Error Messages
**Approach:** Provide specific guidance based on what was blocked

**Implementation:**
```
❌ BLOCKED: Reading source files for exploration
✅ ALTERNATIVE: Use `graphify query "your question"` for architecture questions
💡 TIP: If you need to edit this file, use Edit tool directly
```

### Solution 3: Verbose Logging Mode
**Approach:** Add debug flag to see hook decisions

**Implementation:**
- Add `GRAPHIFY_DEBUG=1` environment variable
- Log hook decisions to stderr
- Show what was checked and why

### Solution 4: Temporary Bypass
**Approach:** Allow users to temporarily disable hooks

**Implementation:**
- Add `--no-hooks` flag to claude CLI
- Add `GRAPHIFY_BYPASS=1` environment variable
- Document bypass in error messages

---

## 📋 Implementation Tasks

### Task 1.1: Improve Error Messages [2 hours]
- [ ] Analyze current error message patterns
- [ ] Design new message format with alternatives
- [ ] Implement context detection (exploration vs editing)
- [ ] Test with common blocked scenarios

### Task 1.2: Add Verbose Logging [3 hours]
- [ ] Add debug flag to hook script
- [ ] Log hook decisions (what was checked, why blocked)
- [ ] Add timing information
- [ ] Test with various scenarios

### Task 1.3: Implement Bypass Mechanism [2 hours]
- [ ] Add environment variable check
- [ ] Document bypass in README
- [ ] Add safety warnings
- [ ] Test bypass functionality

### Task 1.4: Context-Aware Blocking [4 hours]
- [ ] Analyze Edit tool context
- [ ] Detect debugging scenarios
- [ ] Implement context checks
- [ ] Test with real workflows

### Task 1.5: Create Debugging Guide [2 hours]
- [ ] Document common hook issues
- [ ] Add troubleshooting steps
- [ ] Create examples
- [ ] Test with users

---

## 🧪 Test Cases

### Test 1: Read for Editing
**Before:** BLOCKED
**After:** ALLOWED (with context)

### Test 2: Read for Exploration
**Before:** BLOCKED
**After:** BLOCKED (with helpful message)

### Test 3: Find Hook Files
**Before:** BLOCKED
**After:** ALLOWED (with context)

### Test 4: Run Claude CLI
**Before:** BLOCKED (randomly)
**After:** ALLOWED (always)

### Test 5: Debug Mode
**Before:** No visibility
**After:** Full logging

---

## 📊 Success Metrics

| Metric | Before | Target | Measurement |
|--------|--------|--------|-------------|
| False positive blocks | ~30% | <5% | Count blocked legitimate operations |
| User frustration | High | Low | User feedback |
| Debug time | 10+ min | <2 min | Time to diagnose hook issues |
| Bypass usage | N/A | <10% | Track bypass frequency |

---

## 🎯 Priority Order

1. **Error Messages** (Quick win, high impact)
2. **Verbose Logging** (Enables debugging)
3. **Bypass Mechanism** (Power user escape hatch)
4. **Context-Aware Blocking** (Most complex, highest impact)

---

## 📝 Notes

- Start with error messages (easiest, highest impact)
- Test each improvement thoroughly
- Document changes clearly
- Gather user feedback early

---

**Next Action:** Implement improved error messages