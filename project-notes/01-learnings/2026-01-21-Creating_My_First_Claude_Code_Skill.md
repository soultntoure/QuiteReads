# Creating My First Claude Code Skill
![Claude Code Skill Problem](../images/claude_skill_problem.png)
## The Problem

I was manually documenting Python modules (like `app/api/schemas/`) and realized I kept following the same structure over and over:

1. Module overview
2. Component tables (3 columns: Component | Purpose | Key Details)
3. Per-file breakdowns
4. Usage examples
5. Significance section

Every time I asked Claude to document a module, I had to:
- Re-explain the structure I wanted
- Fix inconsistencies
- Add missing sections
- Standardize the format

**This was annoying and repetitive.** I needed a way to teach Claude my documentation style once and have it apply automatically across all my projects.

---

## Skills vs Subagents: Why I Chose Skills

I had two options to solve this:

### Option 1: Custom Skill
A portable markdown file that lives in `~/.claude/skills/` and gets auto-discovered when I ask for documentation.

### Option 2: Custom Subagent
A full-blown agent built with the Claude Agent SDK that runs independently.

### The Decision Matrix

| Factor | Skill | Subagent | Winner |
|--------|-------|----------|--------|
| **Simplicity** | Edit markdown file | Write TypeScript/Python code | **Skill** |
| **Portability** | Copy folder → works | SDK setup on every machine | **Skill** |
| **Hot reload** | Edit → use immediately | Rebuild agent | **Skill** |
| **Context** | Shares with main Claude | Isolated context | **Skill** |
| **Parallelization** | One doc at a time | Can do 10 modules at once | Subagent |
| **Maintenance** | Update markdown | Code changes + rebuild | **Skill** |

**I chose Skill** because:
- I'm documenting one module at a time (not 100 modules in parallel)
- I want to share it across projects easily
- I don't need complex multi-phase logic
- Template-driven task fits Skills perfectly

> **Real-world analogy:** Skill = recipe card you keep in the kitchen. Subagent = hiring a full-time chef. I just need a recipe card for my weeknight dinners.

![Skills vs Subagents Comparison](../images/skills_vs_subagents_comparison.png)
---

## How I Created the Skill

### Step 1: Directory Structure

Created the skill in my global Claude Code skills folder:

```bash
mkdir -p ~/.claude/skills/module-readme-standard/{templates,examples}
```

This makes it available across **all my projects**, not just this one.

### Step 2: Main Skill File

Created `skill.md` with **YAML frontmatter** (critical for discovery):

```markdown
---
description: Generates standardized README.md documentation for Python code modules following clean architecture and SOLID principles
---

# Module README Generator

## When to Use
- User requests "document this module"
- User asks to "create README for [folder-name]"
...
```

**The frontmatter is key!** Without it, Claude won't discover the skill.

### Step 3: Smart Template Logic

The skill detects **three folder types**:

#### 1. Leaf Folders (Only .py files)
Example: `app/api/schemas/`
- Full technical documentation
- Detailed component tables
- Usage examples for each file

#### 2. Hybrid Folders (.py files + subdirectories)
Example: `app/api/` (has `main.py` + `routes/`, `schemas/`)
- Full details for Python files in current folder
- High-level overview for subdirectories
- References to subdirectory READMEs

#### 3. Pure Parent Folders (Only subdirectories)
Example: `app/` (only `core/`, `api/`, `infrastructure/`)
- Architectural overview only
- Directory table
- References to child READMEs

> **Key insight:** The more subfolders a directory has, the higher-level its README should be. Technical depth lives in leaf-level READMEs.

### Step 4: Templates + Examples

```
module-readme-standard/
├── skill.md                           # Main instructions
├── templates/
│   ├── leaf-folder-template.md       # Full technical docs
│   └── hybrid-folder-template.md     # Mixed approach
└── examples/
    └── leaf-example-api-schemas.md   # Real example from my project
```

I copied my existing `app/api/schemas/README.md` as an example so Claude has a reference.

---

## What the Skill Does

When I ask:
```
"Document the app/api/routes module"
```

The skill automatically:

1. **Analyzes folder structure**
   - Lists all `.py` files
   - Checks for subdirectories
   - Determines folder type (leaf/hybrid/parent)

2. **Reads Python files**
   - Extracts classes, functions, enums
   - Identifies Pydantic models
   - Maps components

3. **Chooses template**
   - Leaf → full technical docs
   - Hybrid → mixed approach
   - Pure parent → high-level only

4. **Generates README**
   - Module overview
   - Component tables (3 columns)
   - Per-file sections with usage examples
   - Significance table

5. **Writes file**
   - Creates `README.md` in target folder
   - Uses proper markdown formatting
   - Adds relative links to subdirectory READMEs

---

## How to Invoke It

### Natural Language (Auto-discovery)

Just ask naturally:
```
"Document the app/infrastructure/repositories module"
"Create a README for app/utils"
"Generate documentation for the app/core folder"
```

Claude automatically discovers and uses the skill.

### Explicit (If needed)

If auto-discovery doesn't work:
```
"Use the module-readme-standard skill to document app/api"
```

---

## Benefits I Get

### 1. Consistency Across Projects
Same documentation structure everywhere. No more "wait, did I use 2 or 3 columns in that table?"

### 2. Hot Reload (Claude Code 2.1.0+)
Edit the skill → changes apply immediately. No restart needed.

```bash
vim ~/.claude/skills/module-readme-standard/skill.md
# Use immediately
```

### 3. Portable
Share with team:
```bash
cp -r ~/.claude/skills/module-readme-standard teammate/.claude/skills/
```

### 4. Version Controlled
I can git track my skills folder:
```bash
cd ~/.claude/skills
git init
git add .
git commit -m "Add module README standard skill"
```

### 5. DRY (Don't Repeat Yourself)
Define the template **once**, use it **everywhere**.

---

## Quality Standards Built-In

The skill enforces:
- ✓ Consistent 3-column table format
- ✓ Concrete usage examples (not just descriptions)
- ✓ Clear architectural context
- ✓ SOLID principles adherence
- ✓ No duplication between parent/child READMEs
- ✓ Proper markdown linking with relative paths

---

## Testing It

After creating the skill, I tested on different folder types:

### Test 1: Leaf Folder
```
"Document app/api/schemas"
```
✓ Generated full technical README with component tables and examples

### Test 2: Hybrid Folder
```
"Document app/api"
```
✓ Documented Python files + referenced subdirectories

### Test 3: Pure Parent
```
"Document app/"
```
✓ High-level architectural overview only

---

## What I Learned

### 1. Frontmatter is Critical
Without the YAML frontmatter, Claude won't discover the skill:
```yaml
---
description: Your skill description here
---
```

### 2. Skills Share Context
Skills see the main conversation context (CLAUDE.md, project structure), so they don't need to rediscover patterns.

### 3. Hot Reload is Game-Changing
Edit skill → test immediately. No restart workflow is amazing for iteration.

### 4. Examples Help
Including `examples/` with real READMEs helps Claude understand the expected output quality.

### 5. Skills > Subagents for Templates
Template-driven tasks don't need the complexity of full agents.

---

## When Would I Use a Subagent Instead?

I'd graduate to a subagent if I needed:

1. **Parallel execution** (document 50 modules simultaneously)
2. **Background tasks** (generate docs while I keep coding)
3. **Multi-phase workflows** (analyze → diagram → doc → validate → PR)
4. **Independent permissions** (different tool access)

For now, Skill is perfect.

---

## Quick Reference

### Check Available Skills
```bash
# In Claude Code
/help skills
```

### Skill Location
```
~/.claude/skills/module-readme-standard/
```

### Edit Skill
```bash
vim ~/.claude/skills/module-readme-standard/skill.md
```

### Add Examples
```bash
cp new-example.md ~/.claude/skills/module-readme-standard/examples/
```

---

## The Win

**Before:** Manually explaining structure every time → inconsistent docs

**After:** "Document this module" → perfect README every time

**Time saved:** ~10-15 minutes per module

**Consistency gained:** 100%

**Portability:** Works across all my Python projects

> Skills are like teaching Claude a reusable recipe. Once taught, it applies automatically. This is the power of custom skills.
