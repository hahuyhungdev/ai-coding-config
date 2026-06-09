# Refactoring Plan

**Created:** 2026-06-09
**Goal:** Refactor install.py into smaller, maintainable modules

---

## 📊 Current State

**File:** install.py
**Lines:** 619
**Functions:** 15+

**Issues:**
- File too large (619 lines)
- Too many responsibilities
- Hard to test individual components
- Difficult to maintain

---

## 🎯 Refactoring Strategy

### Module 1: `cli.py` - CLI Utilities
**Functions:**
- info(msg)
- ok(msg)
- warn(msg)
- error(msg)
- run_script(script, *args)
- run_node_script(script, *args)

**Lines:** ~60
**Purpose:** CLI output and script execution

---

### Module 2: `file_ops.py` - File Operations
**Functions:**
- merge_json(source, target)
- copy_config(source, target, force)
- install_local_config(source, target, force)
- count_files(directory, pattern)
- count_dirs(directory)

**Lines:** ~120
**Purpose:** File and directory operations

---

### Module 3: `setup.py` - Setup Functions
**Functions:**
- setup_claude(force)
- setup_codex(force)
- setup_agy(force)
- configure_project_assistants(project_dir, assistants)

**Lines:** ~180
**Purpose:** Setup different AI coding assistants

---

### Module 4: `mcp.py` - MCP Configuration
**Functions:**
- update_mcp_configs(install_claude, install_agy)
- sync_mcp_disabled()

**Lines:** ~50
**Purpose:** MCP server configuration

---

### Module 5: `agents.py` - Agent Compilation
**Functions:**
- compile_agents(install_claude, install_codex, install_agy)

**Lines:** ~40
**Purpose:** Agent compilation

---

### Module 6: `install.py` - Main Entry Point
**Functions:**
- main()

**Lines:** ~100
**Purpose:** Main entry point and argument parsing

---

## 📋 Implementation Steps

### Step 1: Create module structure
- [ ] Create `installer/` directory
- [ ] Create `__init__.py`
- [ ] Create module files

### Step 2: Extract functions
- [ ] Move CLI utilities to `cli.py`
- [ ] Move file operations to `file_ops.py`
- [ ] Move setup functions to `setup.py`
- [ ] Move MCP functions to `mcp.py`
- [ ] Move agent compilation to `agents.py`

### Step 3: Update imports
- [ ] Update `install.py` to import from modules
- [ ] Update all internal imports
- [ ] Test all functionality

### Step 4: Verify
- [ ] Run tests
- [ ] Check all functionality works
- [ ] Update documentation

---

## 🎯 Expected Benefits

1. **Maintainability:** Each module has single responsibility
2. **Testability:** Modules can be tested independently
3. **Readability:** Smaller files are easier to understand
4. **Reusability:** Modules can be reused in other projects
5. **Collaboration:** Multiple developers can work on different modules

---

## 📊 Metrics

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Largest file | 619 lines | ~180 lines | **71% reduction** |
| Total modules | 1 | 6 | **Better organization** |
| Functions per file | 15+ | 3-5 | **Single responsibility** |
| Testability | Hard | Easy | **∞ improvement** |

---

**Status:** Ready to implement
**Timeline:** 2-3 hours