# 🧪 10 Test Cases for the Refined Configuration Guidelines

This document contains 10 structured test cases to verify the performance, constraints, and behavior of the updated instructions (`ANTIGRAVITY.md` / `CLAUDE.md` / `AGENTS.md`) in a fresh session of the **Antigravity CLI (`agy`)** or other AI assistants.

---

## Test Cases Index
1. [Test 1: Skill Discovery & Dynamic Loading](#test-1-skill-discovery--dynamic-loading)
2. [Test 2: Rejection of "AI Slop" Aesthetics](#test-2-rejection-of-ai-slop-aesthetics)
3. [Test 3: Theme-Driven UI Layouts](#test-3-theme-driven-ui-layouts)
4. [Test 4: Softer TDD for Non-Functional Changes](#test-4-softer-tdd-for-non-functional-changes)
5. [Test 5: Strict TDD for Behavioral Logic Changes](#test-5-strict-tdd-for-behavioral-logic-changes)
6. [Test 6: Conditional MCP Server Detection](#test-6-conditional-mcp-server-detection)
7. [Test 7: Dynamic MCP Toggling via CLI](#test-7-dynamic-mcp-toggling-via-cli)
8. [Test 8: Graphify-First Exploration Rules](#test-8-graphify-first-exploration-rules)
9. [Test 9: Targeted Raw Reads Post-Discovery](#test-9-targeted-raw-reads-post-discovery)
10. [Test 10: Milestone-Based Strategic Compaction](#test-10-milestone-based-strategic-compaction)

---

### Test 1: Skill Discovery & Dynamic Loading
* **Goal:** Verify the agent inspects the `skills/` directory first rather than guessing skill names or pre-loading everything.
* **Initial Prompt:** 
  > "I need to design a clean typography layout for our pricing page. Check what guidelines or skills we have in this repository first, and list them before giving your design recommendations."
* **Follow-up Prompt:**
  > "Based on what you found, load the most specific skill and apply its exact rules to write a sample HTML structure."
* **Requirements & Expected Behavior:**
  * The agent must NOT guess the skill names; it must run `list_dir` on `skills/` or a search query to discover what skills are available.
  * It must list the discovered skills (e.g. `frontend-design`, `design-system`).
  * It must explicitly read the `frontend-design/SKILL.md` file before generating code.

---

### Test 2: Rejection of "AI Slop" Aesthetics
* **Goal:** Verify the agent actively refuses generic gradients, Roboto/Inter font stacks, and glassmorphic cards.
* **Initial Prompt:**
  > "Build a dashboard card component displaying user session statistics. Make it look modern and sleek."
* **Follow-up Prompt:**
  > "Can we add a nice purple-to-blue gradient background and a glassmorphism blur effect to make it look futuristic?"
* **Requirements & Expected Behavior:**
  * The initial layout must avoid Inter/Roboto font stacks and generic gradients.
  * In response to the follow-up, the agent **must politely decline** the purple gradient and glassmorphism defaults, explaining that they represent generic "AI slop" aesthetics.
  * It must propose a more distinct design (e.g. high-contrast solid borders, monochromatic minimal styling, or a retro-futuristic monospace theme).

---

### Test 3: Theme-Driven UI Layouts
* **Goal:** Verify that the agent can choose and execute a bold, intentional design direction.
* **Initial Prompt:**
  > "I need to build a landing page hero section for a local coffee roaster. Pick a distinctive, non-generic design theme and write the HTML/CSS code."
* **Follow-up Prompt:**
  > "Now explain your color choices, layout choices, and typography pairing decisions in detail."
* **Requirements & Expected Behavior:**
  * The agent must explicitly commit to a specific theme (e.g. *Brutalist Raw*, *Minimal Editorial*, or *Pastel/Organic*).
  * It must pair a distinctive display font (e.g., a serif like Playfair Display or a bold sans-serif like Syne) with a highly readable body font.
  * It must use CSS custom properties for color tokens.
  * It must avoid default Tailwind/Bootstrap look-alikes.

---

### Test 4: Softer TDD for Non-Functional Changes
* **Goal:** Verify the agent does not force unit tests for pure configuration, documentation, or styling changes.
* **Initial Prompt:**
  > "We need to update our project README.md file with a new troubleshooting section for visual glitches. Walk me through your implementation plan."
* **Follow-up Prompt:**
  > "Do we need to write a unit test suite before making this edit? How will you verify correctness?"
* **Requirements & Expected Behavior:**
  * The agent must recognize that a documentation update is non-functional.
  * It should state that strict TDD (writing tests first) is not necessary for this task.
  * It should propose verification via syntax checks, visual checks, or a simple markdown lint, rather than test runners.

---

### Test 5: Strict TDD for Behavioral Logic Changes
* **Goal:** Verify that the agent strictly enforces TDD when adding new functional behavior or refactoring risky code.
* **Initial Prompt:**
  > "We need to add a new `calculate_discount(price, coupon)` utility function that handles coupon expiration and caps discounts at 50%. How will you implement this?"
* **Follow-up Prompt:**
  > "Can you just write the function code directly so we can save time?"
* **Requirements & Expected Behavior:**
  * The agent must decline to write the production code first.
  * It must insist on writing failing unit test cases (RED phase) first.
  * It must outline the test cases (e.g. coupon expired, price <= 0, discount > 50% cap) before writing the utility code.

---

### Test 6: Conditional MCP Server Detection
* **Goal:** Verify the agent checks for MCP server availability instead of assuming they exist.
* **Initial Prompt:**
  > "I want to review our SQLite database schemas to check if the user tables are properly indexed. What tools or MCP servers will you use?"
* **Follow-up Prompt:**
  > "If the SQLite MCP server is disabled, what is your fallback strategy?"
* **Requirements & Expected Behavior:**
  * The agent must state that optional MCP servers (like `sqlite`) are disabled by default.
  * It must propose checking the active MCP configurations first.
  * For the fallback, it must recommend running standard shell commands (e.g., `sqlite3 database.db ".schema"`) to inspect the database, rather than trying to call sqlite MCP tools.

---

### Test 7: Dynamic MCP Toggling via CLI
* **Goal:** Verify the agent knows how to interact with the repository's `mcp-toggle.py` script.
* **Initial Prompt:**
  > "I need to run an automated container audit on our active Docker services. How can you enable the docker MCP server so you can use its native tools?"
* **Follow-up Prompt:**
  > "Run the necessary commands to list the servers and enable the docker server."
* **Requirements & Expected Behavior:**
  * The agent must locate and mention `scripts/mcp-toggle.py` or the `ai-config` wrapper.
  * It must outline the command: `python3 scripts/mcp-toggle.py enable docker`.
  * It must warn the user that they need to restart their CLI session to pick up the newly enabled server.

---

### Test 8: Graphify-First Exploration Rules
* **Goal:** Verify the agent queries the knowledge graph before falling back to `grep`, `find`, or raw file reads.
* **Initial Prompt:**
  > "How is the authentication logic structured in this project? What files should we look at?"
* **Follow-up Prompt:**
  > "Can you grep the codebase for `login` to find all occurrences?"
* **Requirements & Expected Behavior:**
  * The agent must state that it should use Graphify first to answer codebase questions.
  * The first tool call must be a Graphify query: `rtk graphify query "authentication logic"`.
  * The agent must decline to start with a raw `grep` or `find` on source files, explaining that it respects the Graphify-first policy.

---

### Test 9: Targeted Raw Reads Post-Discovery
* **Goal:** Verify the agent allows targeted reads for config review, debugging, or editing *after* discovery.
* **Initial Prompt:**
  > "Run a Graphify query to locate where our project settings are defined. After you find the file, read its exact structure."
* **Follow-up Prompt:**
  > "Are you allowed to read this file directly?"
* **Requirements & Expected Behavior:**
  * The agent must first query Graphify to locate the settings file (e.g., `settings.json`).
  * Once identified, the agent must use `view_file` or a python script to read it.
  * It should explain that targeted raw reads are fully permitted for editing, debugging, config review, and precise verification after Graphify discovery has narrowed down the files.

---

### Test 10: Milestone-Based Strategic Compaction
* **Goal:** Verify the agent suggests strategic compaction only at logical milestones during long-running tasks.
* **Initial Prompt:**
  > "We have a large refactoring task: we need to replace all instances of deprecated CSS classes, update the design system tokens, write visual tests, and refactor the header layout. Let's start step-by-step."
* **Follow-up Prompt:**
  > "We just finished updating the CSS classes and tokens. What should we do with our context window before moving to visual tests?"
* **Requirements & Expected Behavior:**
  * The agent must not call compaction on simple tasks, but recognize that this multi-phase task is long-running.
  * After completing the first major phase, the agent should propose running `/compact` (or calling the compaction skill) to summarize progress and clean up the context window before starting the next phase.
