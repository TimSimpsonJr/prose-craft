# User Data Relocation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move per-user data (registers, learning artifacts) out of the prose-craft plugin install path to `~/.claude/data/prose-craft/`, restructure the dotfiles-claude repo to sync that personal layer across machines, and complete the Mac migration. Windows migration is documented for execution when the user is home.

**Architecture:** Plugin code stays at the marketplace-managed install path (`~/.claude/plugins/cache/prose-craft/prose-craft/<ver>/`); user data moves to `~/.claude/data/prose-craft/` which is invariant under plugin updates. Register discovery shifts from inline-edited HTML comments in `prose-craft` SKILL.md to per-register YAML frontmatter. A new `/prose-craft-init` skill bootstraps the data directory and walks the user through extraction. Dotfiles ships only the personal data layer (not plugin code).

**Tech Stack:** Markdown (skill / agent prompts), Python 3 + pytest (`scripts/discipline_check.py`, unchanged), Bash (dotfiles install/snapshot scripts), `gh` CLI (PR), git.

**Source design:** [`docs/plans/2026-05-30-user-data-relocation-design.md`](2026-05-30-user-data-relocation-design.md) — approved by Codex after 3 rounds of review. Every section/rule referenced here as "§N.N" refers to that document.

**Repos touched:**
- `~/Documents/Projects/prose-craft/` (this repo) — the bulk of the work, lands as a single PR.
- `~/dotfiles-claude/` — direct-push restructure to add the data layer and update sync scripts.

---

## Phase A — prose-craft repo restructure (feature branch + PR)

### Task A1: Create feature branch and template-data/ structure

**Files:**
- Create: `template-data/registers/register-template.md` (moved from `registers/`)
- Create: `template-data/learning/accumulator.md` (moved from `learning/`)
- Delete: `registers/` (entire directory)
- Delete: `learning/` (entire directory)

- [ ] **Step 1: Create the feature branch.**

```bash
cd ~/Documents/Projects/prose-craft
git checkout main
git pull --ff-only
git checkout -b feat/user-data-relocation
```

- [ ] **Step 2: Move register-template into template-data/.**

```bash
mkdir -p template-data/registers template-data/learning
git mv registers/register-template.md template-data/registers/register-template.md
git mv learning/accumulator.md template-data/learning/accumulator.md
```

- [ ] **Step 3: Add `triggers:` frontmatter placeholder to register-template.md.**

Prepend a YAML frontmatter block. The current file starts with `# Register Template` (or similar — read it first to confirm). After this step the top of the file becomes:

```yaml
---
# Replace the placeholder array below with the writing contexts that should
# activate this register. The prose-craft skill matches the user's current
# writing task against these phrases. Examples: "advocacy writing",
# "personal essays", "technical documentation".
triggers:
  - placeholder context 1
  - placeholder context 2
---

# Register Template
```

Read the existing `template-data/registers/register-template.md` first; preserve everything below the existing first heading.

- [ ] **Step 4: Remove the now-empty repo-root registers/ and learning/ directories.**

```bash
# registers/ should now be empty (register-template.md was the only file)
rmdir registers
# learning/ should now be empty (accumulator.md was the only file)
rmdir learning
```

If either `rmdir` fails because of unexpected content, stop and inspect — the design assumes those directories contain only the templates we just moved.

- [ ] **Step 5: Verify and commit.**

```bash
# Sanity-check the new tree
ls template-data/registers/  # → register-template.md
ls template-data/learning/   # → accumulator.md
test ! -d registers && echo "registers/ removed OK"
test ! -d learning && echo "learning/ removed OK"

# Confirm template gained frontmatter
head -10 template-data/registers/register-template.md

git add -A
git commit -m "refactor: move registers/ and learning/ starters into template-data/

Repo no longer ships registers/ or learning/ at root; the user-data layer
lives at \$HOME/.claude/data/prose-craft/ (see design §3, §4.2).
template-data/ holds the read-only starter content the init skill copies
into the user-data path on first run.

register-template.md gains a triggers: frontmatter placeholder so
generated registers can declare their activation contexts (§4.5)."
```

---

### Task A2: Path rewrites + first-run check + frontmatter discovery in `skills/prose-craft/SKILL.md`

**Files:**
- Modify: `skills/prose-craft/SKILL.md`

This task replaces three sections of the file: the existing "Register Detection" block (currently lines 10-31), inserts a new first-run-check section at the top of the skill body, and rewrites the one `${CLAUDE_PLUGIN_ROOT}/registers/` reference.

- [ ] **Step 1: Read the current SKILL.md fully** so you understand which content stays put. The frontmatter (`name:`, `description:`) is unchanged; everything after the Register Detection section (Source Material, formatting rules, etc.) is unchanged.

- [ ] **Step 2: Insert the first-run check.** Immediately after the H1 heading (`# Prose Craft`) and the opening sentence ("You are writing for a human audience..."), insert:

```markdown
## First-run setup

Before generating anything, verify the user-data directory is ready:

1. Check whether `~/.claude/data/prose-craft/registers/` contains at least one register file other than `register-template.md`.
2. If yes, proceed with normal generation (skip the rest of this section).
3. If no register files exist (or the directory is missing), tell the user: "prose-craft isn't initialized on this machine yet. Run `/prose-craft-init` to create your first register." Stop — do not attempt generation.

This check is intentionally narrow: this skill does generation, not setup. Anything that touches the data directory or walks the user through extraction lives in `/prose-craft-init`.
```

- [ ] **Step 3: Replace the Register Detection block.** Delete the entire existing `## Register Detection` section (the H2 heading, the on-invocation paragraph, the HTML-comment block, and the "Ambiguous:" line) and replace with:

````markdown
## Register Detection

On invocation, determine which register to use from context by reading the per-register frontmatter at the user-data path:

1. Glob `~/.claude/data/prose-craft/registers/*.md`, excluding `register-template.md`.
2. For each file, read the YAML frontmatter block at the top. If a file has no frontmatter or no `triggers` field, skip it (it's not a configured register).
3. Match the current writing context against each register's `triggers` list. If exactly one register matches, use it. If multiple match, ask the user which. If none match — **including registers whose `triggers:` array is empty** — ask the user which register to use, listing all registers found in the directory so partially-configured registers are still selectable. If no register files are configured at all, tell the user to run `/prose-craft-init`.
4. Read the chosen register's body (everything after the closing `---` of the frontmatter) — that's the voice feature description.

The register's name is the filename without the `.md` extension (so `~/.claude/data/prose-craft/registers/personal.md` is the `personal` register).

**Ambiguous:** Ask the user which register to use.

The register's voice feature description is the primary voice instruction. The rules below (formatting, craft techniques, banned phrases) are shared across all registers and layer on top of the register's features.
````

- [ ] **Step 4: Verify no `${CLAUDE_PLUGIN_ROOT}/registers/` references remain in this file.**

```bash
grep -n 'CLAUDE_PLUGIN_ROOT.*registers' skills/prose-craft/SKILL.md
# Expected output: nothing (the old reference was inside the deleted HTML block)
```

If anything turns up, rewrite each remaining occurrence to `~/.claude/data/prose-craft/registers/`.

- [ ] **Step 5: Commit.**

```bash
git add skills/prose-craft/SKILL.md
git commit -m "feat(prose-craft): frontmatter-based register discovery + first-run check

- Drop the inline HTML-comment register list (broken under marketplace
  install where every plugin update would overwrite SKILL.md per §4.5).
- Registers self-describe via YAML frontmatter declaring their triggers;
  the skill globs ~/.claude/data/prose-craft/registers/*.md and picks
  based on those.
- Adds a first-run check that refuses generation until /prose-craft-init
  has populated at least one register (§4.4)."
```

---

### Task A3: Path rewrites + target-aware routing in `skills/prose-craft-learn/SKILL.md`

**Files:**
- Modify: `skills/prose-craft-learn/SKILL.md`

This task does two things: rewrites every `${CLAUDE_PLUGIN_ROOT}/registers/` and `${CLAUDE_PLUGIN_ROOT}/learning/` reference (14 occurrences per design §4.1), and replaces the hardcoded "apply edits to both locations" block (currently around lines 220-225) with target-aware routing including a new `pending-upstream.md` queue.

- [ ] **Step 1: List every reference that will change.**

```bash
grep -n 'CLAUDE_PLUGIN_ROOT' skills/prose-craft-learn/SKILL.md
```

Note line numbers — you'll touch each one.

- [ ] **Step 2: Run a single sed pass to do the bulk rewrite.**

```bash
sed -i.bak \
  -e 's|\${CLAUDE_PLUGIN_ROOT}/registers/|~/.claude/data/prose-craft/registers/|g' \
  -e 's|\${CLAUDE_PLUGIN_ROOT}/learning/|~/.claude/data/prose-craft/learning/|g' \
  skills/prose-craft-learn/SKILL.md
diff -u skills/prose-craft-learn/SKILL.md.bak skills/prose-craft-learn/SKILL.md | head -50
rm skills/prose-craft-learn/SKILL.md.bak
```

Visually confirm the diff shows only the expected `${CLAUDE_PLUGIN_ROOT}/registers/...` and `${CLAUDE_PLUGIN_ROOT}/learning/...` → `~/.claude/data/prose-craft/...` substitutions. If anything else changed, restore from the `.bak` and investigate.

- [ ] **Step 3: Verify zero `${CLAUDE_PLUGIN_ROOT}/registers/` and `${CLAUDE_PLUGIN_ROOT}/learning/` references remain.**

```bash
grep -n 'CLAUDE_PLUGIN_ROOT/registers\|CLAUDE_PLUGIN_ROOT/learning' skills/prose-craft-learn/SKILL.md
# Expected: empty
```

If anything turns up (e.g., a reference with a typo or unusual spacing the sed missed), rewrite it manually.

- [ ] **Step 3.5: Fix bare relative paths the `${CLAUDE_PLUGIN_ROOT}/`-only sed didn't catch.**

There are three known spots in `skills/prose-craft-learn/SKILL.md` (line numbers from main as of this writing) that reference `registers/...` or `learning/...` *without* the `${CLAUDE_PLUGIN_ROOT}/` prefix — because they sit inside a bulleted list whose lead-in sentence supplies that prefix once at the top ("Read these from `${CLAUDE_PLUGIN_ROOT}/:`"). After our rewrite, the lead-in sentence's prefix changes but the bare list items don't follow along. Plus a bare ablation-log reference.

```bash
grep -n '\bregisters/{register\|\blearning/splits\|\blearning/ablation-log' skills/prose-craft-learn/SKILL.md
# Expected hits around lines 135, 139, 371 (line numbers may shift after earlier edits)
```

For each hit, rewrite the bare `registers/...` or `learning/...` path to its absolute form at `~/.claude/data/prose-craft/...`:

- `` `registers/{register}.md` `` → `` `~/.claude/data/prose-craft/registers/{register}.md` ``
- `` `learning/splits.md` `` → `` `~/.claude/data/prose-craft/learning/splits.md` ``
- `` `learning/ablation-log.md` `` → `` `~/.claude/data/prose-craft/learning/ablation-log.md` ``

Use `sed -i.bak` for each, then diff and remove the `.bak`:

```bash
sed -i.bak \
  -e 's|`registers/{register}\.md`|`~/.claude/data/prose-craft/registers/{register}.md`|g' \
  -e 's|`learning/splits\.md`|`~/.claude/data/prose-craft/learning/splits.md`|g' \
  -e 's|`learning/ablation-log\.md`|`~/.claude/data/prose-craft/learning/ablation-log.md`|g' \
  skills/prose-craft-learn/SKILL.md
diff -u skills/prose-craft-learn/SKILL.md.bak skills/prose-craft-learn/SKILL.md
rm skills/prose-craft-learn/SKILL.md.bak
```

Also update the lead-in sentence at line ~131 ("Read these from `${CLAUDE_PLUGIN_ROOT}/:`") — strip the now-misleading prefix mention since each list item now carries its own absolute path. The sentence becomes "Read these:" (or similar).

- [ ] **Step 4: Find and replace the hardcoded dual-write block.**

The current text (around lines 220-225, matched by content) says:

```markdown
For each edit the gate **accepted**, apply the text edit to the target file in BOTH locations:
- **Installed plugin copy:** `~/.claude/plugins/cache/local/prose-craft/2.0.0/{target-path}`
- **Source repo copy:** `prose-craft/{target-path}` (relative to the current working directory)

If the source repo copy doesn't exist at the expected path, skip it silently (the user may not be working from the source repo).
```

Replace that entire passage (from "For each edit the gate" through "...working from the source repo).") with:

```markdown
For each edit the gate **accepted**, route the write by target type:

| Target type | Write to |
|---|---|
| Register file (`registers/<name>.md`) | `~/.claude/data/prose-craft/registers/<name>.md` |
| `accumulator.md` | `~/.claude/data/prose-craft/learning/accumulator.md` |
| Other learning artifacts (`splits.md`, `ablation-log.md`, `judge-agreement.md`, etc.) | `~/.claude/data/prose-craft/learning/<filename>` |
| Plugin-code file (agent body, skill body, scripts) | **Do not write to the install path.** Append a proposal to `~/.claude/data/prose-craft/learning/pending-upstream.md` for review and upstream PR. |

The marketplace install path is owned by plugin updates — any local write there gets clobbered on next update. The `pending-upstream.md` queue keeps plugin-code edits visible without silently mutating disposable state.

**`pending-upstream.md` append format** (newest-first):

```markdown
## <ISO-8601 timestamp> · <target-path-relative-to-plugin-root>

- **Source candidate:** `<learn-review proposal id or short label>`
- **Rationale:** <one-paragraph summary of the gate evidence supporting this edit>

\```diff
<unified diff of the proposed change>
\```
```

The richer UX (e.g., a `/prose-craft-pending` skill that surfaces queued edits) is out of scope; lands in the planned extraction/learning rework.
```

(The `\```diff` and trailing `\```` are how the inner fenced block is encoded in markdown when included verbatim inside another fenced block.)

- [ ] **Step 4.5: Reroute the other plugin-code-edit instructions in the same file.**

The Mode 2 Step 10 dual-write block (Step 4 above) is not the only place this file directs writes at plugin-code files. Two more sites need the same treatment:

1. **Mode 3 (evaluator mode) — step 4** around line ~348 currently reads:

   > "Apply approved evaluator edits to `agents/prose-review.md` / `agents/craft-review.md` in both locations (repo + installed), as in Mode 2 Step 10."

   Replace that step with:

   > "Approved evaluator edits route per the same table in Mode 2 Step 10. `agents/prose-review.md` and `agents/craft-review.md` are plugin-code files — append the proposed edit to `~/.claude/data/prose-craft/learning/pending-upstream.md` for upstream PR. Do not write to the marketplace install path."

2. **Ablation operation — "Initial sweep targets"** around lines ~366-368 currently reads (in the prose-review #25 / #26 bullet):

   > "(present in the installed `agents/prose-review.md`; the repo copy lags, so the sweep operates on the installed copy)."

   This language assumes a co-located source repo + locally-modifiable install. Replace with:

   > "(reference target is `agents/prose-review.md` in the marketplace install at `~/.claude/plugins/cache/prose-craft/prose-craft/<ver>/agents/prose-review.md` — read-only. Any rule drop that survives the gate is a plugin-code edit and routes to `~/.claude/data/prose-craft/learning/pending-upstream.md` for upstream PR per Mode 2 Step 10.)"

   And the "Record each as a keep/remove decision + score delta in `learning/ablation-log.md`" line at ~371 already got its path absolutized in Step 3.5 above; verify it now reads `~/.claude/data/prose-craft/learning/ablation-log.md`.

- [ ] **Step 5: Commit.**

```bash
git add skills/prose-craft-learn/SKILL.md
git commit -m "feat(prose-craft-learn): retarget writes for the new data layout

- All 14 \${CLAUDE_PLUGIN_ROOT}/{registers,learning}/ references now point
  at ~/.claude/data/prose-craft/{registers,learning}/.
- Replaces the hardcoded dual-write block (\"apply edits to BOTH locations:
  installed plugin copy + source repo copy\") with target-aware routing:
  registers/accumulator/learning artifacts go to the data path; plugin-
  code edits queue to ~/.claude/data/prose-craft/learning/pending-upstream.md
  for review and upstream PR rather than touching the disposable
  marketplace install path (design §4.1)."
```

---

### Task A4: Path rewrites in `setup/extraction-guide.md`

**Files:**
- Modify: `setup/extraction-guide.md`

Three `${CLAUDE_PLUGIN_ROOT}/registers/` references and a step-5 instruction that tells the user to edit SKILL.md inline. All updates land here.

- [ ] **Step 1: Rewrite the registers/ references.**

```bash
sed -i.bak \
  -e 's|\${CLAUDE_PLUGIN_ROOT}/registers/|~/.claude/data/prose-craft/registers/|g' \
  setup/extraction-guide.md
diff -u setup/extraction-guide.md.bak setup/extraction-guide.md
rm setup/extraction-guide.md.bak
grep -n 'CLAUDE_PLUGIN_ROOT' setup/extraction-guide.md
# Expected: empty
```

- [ ] **Step 2: Locate the step that tells the user to edit SKILL.md.** It currently reads (around line 40):

```
Copy `registers/register-template.md` to `registers/[your-register-name].md`...
```

Replace the entire setup-via-SKILL.md instruction (the step that says copy template + paste content + edit SKILL.md to add a trigger entry) with:

```markdown
Use `/prose-craft-init` to create a new register interactively. The init skill walks you through extracting your voice from samples (via Sonnet) and writes the resulting register file (with its `triggers:` frontmatter declaring activation contexts) to `~/.claude/data/prose-craft/registers/<your-register-name>.md`.

If you prefer the manual path, copy `~/.claude/data/prose-craft/registers/register-template.md` to `~/.claude/data/prose-craft/registers/<your-register-name>.md`, paste your pass-2 output into the body, and add a `triggers:` frontmatter array listing the writing contexts that should activate this register. The `prose-craft` skill discovers registers by globbing this directory and reading frontmatter — no SKILL.md edits required.
```

- [ ] **Step 3: Commit.**

```bash
git add setup/extraction-guide.md
git commit -m "docs(setup): point extraction-guide at /prose-craft-init and the data path

User-facing setup no longer instructs editing SKILL.md inline. The init
skill creates registers at ~/.claude/data/prose-craft/registers/; manual
register creation is still documented as an alternative."
```

---

### Task A5: Create the init skill at `skills/prose-craft-init/SKILL.md`

**Files:**
- Create: `skills/prose-craft-init/SKILL.md`

This is the largest single new artifact. The skill consolidates the work currently spread across five `setup/*.md` documents.

- [ ] **Step 1: Create the directory.**

```bash
mkdir -p skills/prose-craft-init
```

- [ ] **Step 2: Write the skill file** with this exact content:

````markdown
---
name: prose-craft-init
description: Initialize prose-craft on this machine and extract a voice register. Creates the user data directory, copies templates, and walks you through the extraction process to create your first register. Also use this to add a new register later. Invoke via /prose-craft-init.
---

# Prose Craft Init

This skill bootstraps the prose-craft user-data directory and walks you through extracting a voice register. It's idempotent — running it again is how you add a new register or refresh templates after a plugin update.

## Phase 1: Bootstrap the data directory

1. Check whether `~/.claude/data/prose-craft/` exists.
2. If not, create it along with `registers/` and `learning/snapshots/` underneath:

   ```bash
   mkdir -p ~/.claude/data/prose-craft/registers
   mkdir -p ~/.claude/data/prose-craft/learning/snapshots
   ```

3. For every file under `${CLAUDE_PLUGIN_ROOT}/template-data/`, check whether the corresponding target under `~/.claude/data/prose-craft/` exists. If the target is missing, copy the template file there. **Never overwrite a file that already exists at the target.** This pattern lets plugin updates ship new template files (which appear at the data path on next init invocation) without ever touching existing user data.

## Phase 2: Detect state and route

After Phase 1, list `~/.claude/data/prose-craft/registers/` excluding `register-template.md`.

- **Fresh install (zero populated registers):** continue to Phase 3 — first-time extraction walkthrough.
- **At least one populated register:** ask the user "You already have these registers: [list]. Do you want to (1) add a new register, or (2) re-extract an existing register?" Default to (1). If (2), prompt for which register; treat it as a fresh extraction that will overwrite the chosen register file when complete.

## Phase 3: Extraction walkthrough

The current process follows the existing `setup/` reference documents. (The user has flagged that this entire phase will be replaced by the planned extraction/learning rework; the bootstrap in Phases 1-2 is the stable structural piece.)

### Step 3.1: Identify the register

Ask the user what kind of writing this register is for (e.g., advocacy, personal essays, technical documentation, dystopian fiction). Derive a short kebab-case name (e.g., `advocacy`, `personal`, `tech-docs`, `dystopian-fiction`) that becomes the register's filename. Confirm with the user.

Also ask: "What writing contexts should activate this register?" Capture the list — it becomes the `triggers:` array in the register's frontmatter.

### Step 3.2: Collect samples

Reference `${CLAUDE_PLUGIN_ROOT}/setup/sample-collection.md` for the format requirements. Ask the user for 10-20 samples of their own writing in this register, plus 10 baseline samples (Claude-default outputs on similar topics).

If the user doesn't have baselines ready, walk them through generating a batch: open a fresh Claude conversation (no system prompt, no special instructions), ask it to write 10 short pieces (150-300 words each) on topics similar to their writing samples using prompts like "Write a short comment about [topic]." Save the outputs as the baseline (P1) corpus.

### Step 3.3: Pass-1 extraction

Read the prompt at `${CLAUDE_PLUGIN_ROOT}/setup/pass-1-prompt.md`. Dispatch a Sonnet agent with that prompt as system context, filling in:
- the P1 section with the user's baseline samples
- the P2 section with the user's own writing samples

Save the agent's output to `~/.claude/data/prose-craft/learning/extraction-artifacts/<register-name>/pass-1-output.md` (create the directory if needed).

### Step 3.4: Pass-2 extraction

Read the prompt at `${CLAUDE_PLUGIN_ROOT}/setup/pass-2-prompt.md`. Dispatch a second Sonnet agent with that prompt, passing the pass-1 output from Step 3.3. Save the result to `~/.claude/data/prose-craft/learning/extraction-artifacts/<register-name>/pass-2-output.md`.

### Step 3.5: Write the register file

Convert the pass-2 output into a register file using the structure in `${CLAUDE_PLUGIN_ROOT}/template-data/registers/register-template.md`. Important:

1. Write YAML frontmatter at the top with the `triggers:` array from Step 3.1.
2. Place the pass-2 voice feature description (Vocabulary / Sentence Structure / Rhetorical Techniques / Voice Qualities sections) in the body, following the template's section order.
3. Save the result to `~/.claude/data/prose-craft/registers/<register-name>.md`.

Example finished register frontmatter:

```yaml
---
triggers:
  - personal essays
  - blog posts
  - reflective writing
---

# Personal Register
...
```

### Step 3.6: Optional — brief-stripping setup

Ask the user whether they want brief-stripping support for this register. If yes, walk through `${CLAUDE_PLUGIN_ROOT}/setup/brief-stripping-guide.md`. (This is optional; skip if the user is unsure.)

## Phase 4: Confirm and exit

Tell the user:

> Register `<register-name>` is ready at `~/.claude/data/prose-craft/registers/<register-name>.md` with these triggers: [list]. Try it now: invoke `/prose-craft` with writing that matches one of the trigger contexts.

Stop. Generation belongs to `/prose-craft`; this skill's job is done.

## Re-running

This skill is idempotent. Re-invocation:
- Phase 1 re-checks the data directory; missing template files are restored, existing files left alone.
- Phase 2 routes based on what's already configured.
- Phase 3 produces a new register (or overwrites an existing one if the user chose re-extraction).

Nothing in this skill writes to the plugin install path. All persistent state lives at `~/.claude/data/prose-craft/`.
````

- [ ] **Step 3: Verify the file is well-formed.**

```bash
test -f skills/prose-craft-init/SKILL.md
head -5 skills/prose-craft-init/SKILL.md
# Expected: opens with --- and the name/description block
```

- [ ] **Step 4: Commit.**

```bash
git add skills/prose-craft-init/SKILL.md
git commit -m "feat(prose-craft-init): new skill — bootstrap + extraction walkthrough

/prose-craft-init consolidates work previously spread across five
setup/*.md guides. Idempotent: Phase 1 creates the data directory and
copies templates (never overwriting existing files); Phase 2 routes
based on existing state; Phase 3 walks the user through the current
extraction process (pass-1 + pass-2 Sonnet dispatch, brief-stripping
optional); Phase 4 confirms.

The bootstrap responsibility is stable across the planned extraction/
learning rework. Phase 3 will be replaced wholesale by the new process
when the time comes (design §4.3, §8)."
```

---

### Task A6: Update `.claude-plugin/plugin.json`

**Files:**
- Modify: `.claude-plugin/plugin.json`

- [ ] **Step 1: Read the current manifest** to confirm the version field is `"2.0.0"` and the author field is absent.

```bash
cat .claude-plugin/plugin.json
```

- [ ] **Step 2: Bump the version and add the author field.** Final content:

```json
{
  "name": "prose-craft",
  "version": "2.1.0",
  "description": "Voice-driven prose quality system with modular registers, architectural craft rules, a dual review gate for AI pattern detection and craft depth, and a learning loop that sharpens rules from your edits.",
  "author": {
    "name": "Tim Simpson"
  }
}
```

- [ ] **Step 3: Validate the JSON parses.**

```bash
python3 -c "import json; json.load(open('.claude-plugin/plugin.json'))" && echo "JSON OK"
```

- [ ] **Step 4: Commit.**

```bash
git add .claude-plugin/plugin.json
git commit -m "chore(plugin): bump to 2.1.0 and add author field

Version bump accompanies the user-data relocation (design §4.7).
Marketplace clients on 2.0.0 will fetch 2.1.0 on next update."
```

---

### Task A7: Upstream prose-review.md tuning (3 new advisory rules + §25 reference section)

**Files:**
- Modify: `agents/prose-review.md`

The dotfiles version of this file (currently installed at `~/.claude/plugins/cache/local/prose-craft/2.0.0/agents/prose-review.md`) has 3 new advisory rules and a full §25 reference section absent from main. Cherry-pick them here.

- [ ] **Step 1: Read the current main version** to find the insertion points.

```bash
cat agents/prose-review.md | head -150
```

- [ ] **Step 2: Locate the existing Rule #6 ("Conclusion symmetry").** After Rule #6 in the advisory-patterns table (around line 126 of the dotfiles version), insert these three new rules verbatim:

```markdown
**7. Caps overuse.** All-caps on single words for emphasis is an endorsed advocacy technique. Do NOT flag single-word caps on quantifiers, absolutes, or scope words (ANY, NO, ZERO, EXACTLY, etc.) when used sparingly. DO flag: caps on phrases (2+ words), caps on neutral adjectives, or more than 1 caps instance per section.

**8. Performed specificity.** Concrete details (numbers, named items, day-of-week) that look grounded but don't refer to anything irreplaceable. Test: can you swap each specific for a different specific of the same shape without changing the meaning? If yes, flag it. Example: "what used to take three systems and a Friday spreadsheet" — swap to "five tools and a Monday dashboard" and the meaning is unchanged. Often shows up in compressed callbacks where a vivid earlier detail gets reduced to a verbal token in a later paragraph, stripping the load-bearing part. Distinct from #5 (vague attributions about WHO is speaking) and #4 (promotional vocabulary). This is structural — about the relationship between specifics and the underlying claim.

**9. Hollow anadiplosis.** Word-echo (last word of one clause becomes the first word of the next) used to create rhetorical shape, where the second clause asserts a tautological implication of the first instead of developing it. Real anadiplosis develops each link (Yoda: "fear leads to anger, anger leads to hate, hate leads to suffering" — each step adds a new concept). Hollow anadiplosis just restates. Example: "The operational sprawl becomes readable, and readable sprawl is the kind that gets fixed" — the second clause asserts readability implies fixability, which the first clause already implied. Adjacent to #24 (generic positive conclusions) but more specific: that one is about empty upbeat endings; this is about device-without-substance using word-echo structure.
```

- [ ] **Step 3: Locate the existing §24 ("Generic Positive Conclusions") reference section.** After it (around line 333 of the dotfiles version), insert the full §25 section:

```markdown
### 25. Performed Specificity

**Problem:** Concrete details (numbers, named items, day-of-week, etc.) that have the texture of grounded writing but don't refer to anything irreplaceable. The detail performs specificity without committing to a particular case.

**Test:** Can you swap each specific for a different specific of the same shape without changing the meaning? If yes, the detail is decorative.

**AI-tic example:** "what used to take three systems and a Friday spreadsheet to track" — swap to "five tools and a Monday dashboard" and the meaning is unchanged. The "three," the "Friday," and the "spreadsheet" are arbitrary tokens dressed as grounding detail.

**Real-specificity contrast:** "Allstate processed 22 million claims in 2024" — changing any of those words changes what's being claimed. Solnit's "Evan Snow, a thirtysomething user experience design professional" — each detail narrows the claim to one specific person.

Distinct from #5 (vague attributions, about WHO speaks) and #4 (promotional vocabulary). This is structural — about the relationship between the specifics and the underlying claim. Often shows up in compressed callbacks: a vivid detail in paragraph A gets reduced to a verbal token in paragraph B, stripping the load-bearing part.
```

- [ ] **Step 4: Verify the file structure is still well-formed.**

```bash
grep -c '^**[0-9]' agents/prose-review.md  # advisory rule count
# Was 6, should now be 9 (rules 7, 8, 9 added)
grep -c '^### [0-9]' agents/prose-review.md  # reference section count
# Was N, should now be N+1
```

Visually scan the diff:

```bash
git diff agents/prose-review.md | head -100
```

- [ ] **Step 5: Run tests** to confirm nothing broke (the changes are markdown, but pytest runs on the discipline_check module which references files indirectly).

```bash
python3 -m pytest tests/test_discipline_check.py -v
# Expected: all tests pass (no changes to the script or banned_phrases.txt)
```

- [ ] **Step 6: Commit.**

```bash
git add agents/prose-review.md
git commit -m "feat(prose-review): add Caps overuse, Performed Specificity, Hollow Anadiplosis

Upstreams three advisory rules + full Performed Specificity reference
section that have been running in the user's local install but never
made it back to main. Per design §4.7.

The author-reference diff in craft-review.md is intentionally NOT
upstreamed — those are personal style examples that stay in the
dotfiles personal layer."
```

---

### Task A8: Regenerate `MANIFEST.md` to reflect the new architecture

**Files:**
- Modify: `MANIFEST.md`

The current MANIFEST contains language that becomes actively dangerous after migration — most notably "Never full-reinstall (it clobbers live data)." Regenerate the file end-to-end.

- [ ] **Step 1: Read the current MANIFEST** to preserve everything that's still accurate (stack, agent descriptions, scripts, tests, etc.).

```bash
cat MANIFEST.md
```

- [ ] **Step 2: Rewrite the affected sections.** The MANIFEST file-tree describes the **repository structure** — after Task A1 deletes `registers/` and `learning/` from the repo root, those entries can't stay in the file-tree (they'd be structurally false). All references to the live-data location belong in "Key Relationships," not in the file-tree.

**File-tree changes ("Structure" section):**

- **Remove** the entire `registers/` block (currently 3 lines: `registers/` heading + `register-template.md` + the trailing description about installed-only live data). It does not exist in the repo anymore.
- **Remove** the `learning/accumulator.md` line. It does not exist in the repo anymore either.
- **Add** a new top-level `template-data/` entry:

  ```
  template-data/                Read-only starter content the /prose-craft-init skill copies into
    registers/                  ~/.claude/data/prose-craft/ on first run. Includes the register
      register-template.md      template (with triggers: frontmatter) and the empty accumulator
    learning/                   starter. New template files added in future plugin releases reach
      accumulator.md            users via /prose-craft-init's idempotent copy step.
  ```

- **Add** to the `skills/` block: `prose-craft-init/SKILL.md   Bootstrap + extraction walkthrough; creates ~/.claude/data/prose-craft/ and writes the first register.`

**Key Relationships changes:**

Find the "Dual location (critical)" bullet (the one that currently warns "Never full-reinstall (it clobbers live data)"). Replace it wholesale with:

> **Plugin install vs. user data.** Plugin code lives at `~/.claude/plugins/cache/prose-craft/prose-craft/<ver>/` and is owned by marketplace updates — fully disposable. Personal data lives at `~/.claude/data/prose-craft/` (registers with `triggers:` frontmatter, accumulator, snapshots, ablation log, judge-agreement log, extraction artifacts, pending-upstream queue) and is invariant under plugin updates. Full plugin reinstall is safe; it never touches user data. The `/prose-craft-init` skill bootstraps the data layer on first run by copying anything missing from `template-data/` — existing files are never overwritten.

Preserve everything else (Stack section, agent descriptions, Review gate bullet, Learning loop bullet, PROTECTED field bullet, Splits drive the gate bullet).

- [ ] **Step 3: Verify the file is still well-formed markdown.**

```bash
# Sanity check: counts shouldn't drop precipitously, no malformed sections
wc -l MANIFEST.md
grep -c '^##' MANIFEST.md
```

- [ ] **Step 4: Commit.**

```bash
git add MANIFEST.md
git commit -m "docs: regenerate MANIFEST.md for user-data relocation

The prior \"Never full-reinstall (it clobbers live data)\" warning
becomes actively dangerous after this change — full reinstall is now
the expected update flow. Rewrites the structural map for the new
template-data/ + ~/.claude/data/prose-craft/ split and adds the
prose-craft-init skill (design §4.6)."
```

---

### Task A9: Update `README.md` to reference `/prose-craft-init`

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Read the current README** to find any sections that describe register configuration or first-time setup.

```bash
cat README.md
```

- [ ] **Step 2: Update setup language** so it directs the user to `/prose-craft-init` rather than to manually editing SKILL.md. Specifically, anywhere README references:
- "configure registers in SKILL.md"
- "edit the Register Detection block"
- the `${CLAUDE_PLUGIN_ROOT}/registers/...` path

— replace with prose pointing at `/prose-craft-init` and the `~/.claude/data/prose-craft/` user-data path. The exact wording is at the implementer's discretion; the load-bearing points are:

1. First-time setup runs `/prose-craft-init`.
2. User data lives at `~/.claude/data/prose-craft/`.
3. Plugin updates do not touch user data.

- [ ] **Step 3: Commit.**

```bash
git add README.md
git commit -m "docs(README): point setup at /prose-craft-init and the data path"
```

---

### Task A10: Sanity-check the branch and open the PR

**Files:**
- (No file changes — operational task.)

- [ ] **Step 1: Run the test suite** to confirm nothing regressed.

```bash
python3 -m pytest tests/ -v
# Expected: all tests pass
```

- [ ] **Step 2: Grep for any stale references** the rewrites might have missed.

```bash
# (a) Old ${CLAUDE_PLUGIN_ROOT}-prefixed registers/learning paths
grep -rn '\${CLAUDE_PLUGIN_ROOT}/registers\|\${CLAUDE_PLUGIN_ROOT}/learning' skills/ agents/ setup/ template-data/ README.md MANIFEST.md
# Expected: empty

# (b) Old install path
grep -rn 'plugins/cache/local/prose-craft' skills/ agents/ setup/ README.md MANIFEST.md
# Expected: empty (the old install path should not appear in any user-facing doc)

# (c) Bare `registers/...` or `learning/...` in backticks — these are paths
#     the ${CLAUDE_PLUGIN_ROOT}-only sed wouldn't catch
grep -rn '`registers/[a-z{]\|`learning/[a-z]' skills/ agents/ setup/
# Expected: empty
# (Match characters after the slash to a-z or { so we don't false-positive on
# prose like "learning loop" that has nothing to do with paths. The ablation
# section's "registers/" intentional usage to mean "the registers directory"
# would show up — review case-by-case if hits appear.)

# (d) Anywhere still telling the user to edit SKILL.md inline for register config
grep -rn -i "edit SKILL.md\|edit the Register Detection\|configure your registers in SKILL.md" skills/ setup/ README.md MANIFEST.md
# Expected: empty
```

If any of (a)-(d) returns content, fix the references and amend the relevant commit (or add a new follow-up commit on the same branch).

- [ ] **Step 3: Visually walk the branch diff.**

```bash
git log --oneline main..HEAD
git diff main..HEAD --stat
```

Confirm the commits match Tasks A1-A9 and the file change distribution looks sane (template-data/ created, registers/ and learning/ removed, three SKILL.mds touched, one agent file touched, plugin.json bumped, README and MANIFEST updated).

- [ ] **Step 4: Push the branch.**

```bash
git push -u origin feat/user-data-relocation
```

- [ ] **Step 5: Open the PR.**

```bash
gh pr create \
  --title "feat: relocate user data outside plugin install path (v2.1.0)" \
  --body "$(cat <<'EOF'
## Summary

Implements the design in [`docs/plans/2026-05-30-user-data-relocation-design.md`](docs/plans/2026-05-30-user-data-relocation-design.md) (approved by Codex after 3 rounds of review).

- User data (registers, learning artifacts) moves to `~/.claude/data/prose-craft/`, invariant under plugin updates.
- Plugin install at `~/.claude/plugins/cache/prose-craft/prose-craft/<ver>/` is disposable.
- Register discovery shifts from inline SKILL.md HTML comments to per-register YAML frontmatter.
- New `/prose-craft-init` skill bootstraps the data directory and walks the user through extraction.
- prose-craft-learn no longer writes to the disposable install path; plugin-code edits queue at `~/.claude/data/prose-craft/learning/pending-upstream.md` for upstream PR.
- Three new advisory rules upstreamed to prose-review.md (Caps overuse, Performed Specificity, Hollow Anadiplosis).
- plugin.json bumped to 2.1.0 with author field.
- MANIFEST.md regenerated; the prior "Never full-reinstall" warning is no longer accurate (and was actively dangerous to leave).

## Test plan

- [ ] `python3 -m pytest tests/` passes
- [ ] Fresh-machine smoke test: install plugin via marketplace into a clean `~/.claude/` (or use a scratch user); confirm `/prose-craft-init` creates `~/.claude/data/prose-craft/{registers,learning/snapshots}/`, copies templates, and walks the extraction interactively
- [ ] `/prose-craft` correctly discovers a register via frontmatter triggers
- [ ] `/prose-craft` first-run check fires when no registers are configured

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 6: Note the PR number for the impl-review gate.**

The PR creation triggers `codex-impl-review` in autonomous mode. That gate runs on the PR diff and produces either approval or further revision findings.

---

## Phase B — Mac migration (after PR merge, plugin reinstalled at v2.1.0)

This phase executes on the user's Mac, after the PR from Phase A has merged and the v2.1.0 plugin is available from the marketplace. The current state on Mac is the local-plugin install at `~/.claude/plugins/cache/local/prose-craft/2.0.0/` (set up earlier this session); it remains the data source for the migration.

### Task B1: Migrate personal data to the new location

**Files:**
- (Operational — filesystem changes outside the repo.)

- [ ] **Step 1: Create the new data directory structure.**

```bash
mkdir -p ~/.claude/data/prose-craft/registers
mkdir -p ~/.claude/data/prose-craft/learning
```

- [ ] **Step 2: Copy the register markdown files, EXCLUDING the stale 2.0.0 register-template.md.**

The 2.0.0 template doesn't have the `triggers:` frontmatter block (that's a v2.1.0 addition). If we copied it here, the init skill's "only copy missing files" rule would never replace it, leaving the user-data path with a perpetually stale reference template. Exclude it now; Task B2 step 5 copies the v2.1.0 template from the marketplace install instead.

```bash
SRC=~/.claude/plugins/cache/local/prose-craft/2.0.0
DST=~/.claude/data/prose-craft
find "$SRC/registers" -maxdepth 1 -type f -name '*.md' ! -name 'register-template.md' \
  -exec cp {} "$DST/registers/" \;
ls $DST/registers/
# Expected: advocacy.md  dystopian-fiction.md  personal.md
# (register-template.md is intentionally absent; Task B2 step 5 will add the v2.1.0 version)
```

- [ ] **Step 3: Copy the learning subtree (verbatim).**

```bash
cp -R $SRC/learning/. $DST/learning/
ls $DST/learning/
# Expected: accumulator.md  ablation-log.md  bootstrap-run.md  splits.md  snapshots/  (judge-agreement.md if present)
```

- [ ] **Step 4: Move extraction-artifacts from registers/ (old location) to learning/ (new location per §3).**

```bash
if [[ -d $SRC/registers/extraction-artifacts ]]; then
  cp -R $SRC/registers/extraction-artifacts $DST/learning/
fi
ls $DST/learning/extraction-artifacts/ 2>/dev/null
# Expected (if it existed in source): per-register subdirectories
```

- [ ] **Step 5: Add `triggers:` frontmatter to each existing register file.**

For each register file in `~/.claude/data/prose-craft/registers/` (excluding `register-template.md`), prompt the user interactively:

> "What writing contexts should activate the `<register-name>` register?"

Take the user's response (a list of phrases) and prepend a frontmatter block to that register file:

```yaml
---
triggers:
  - <phrase 1>
  - <phrase 2>
  - ...
---
```

(Insert it before the existing first line of the file.)

If the user declines to specify triggers for a register, prepend an empty array instead:

```yaml
---
triggers: []
---
```

— `/prose-craft` will ask the user per invocation until those triggers get populated.

- [ ] **Step 6: Verify.**

```bash
# Every register file should now have a triggers: frontmatter block
for f in $DST/registers/*.md; do
  if [[ "$(basename $f)" == "register-template.md" ]]; then continue; fi
  head -5 "$f" | grep -q '^triggers:' && echo "$f: OK" || echo "$f: MISSING triggers"
done
```

All files except `register-template.md` should report `OK`.

---

### Task B2: Switch Mac install from local to marketplace

**Files:**
- Modify: `~/.claude/settings.json`
- Modify: `~/.claude/plugins/installed_plugins.json`
- Modify: `~/.claude/plugins/known_marketplaces.json`

- [ ] **Step 1: Update `~/.claude/settings.json`.** In the `enabledPlugins` block:
- Remove the `"prose-craft@local": true` entry (or set it to `false`).
- Add `"prose-craft@prose-craft": true`.

Use the Edit tool or a Python one-liner:

```bash
python3 << 'PY'
import json
from pathlib import Path
p = Path.home() / '.claude/settings.json'
data = json.loads(p.read_text())
data['enabledPlugins'].pop('prose-craft@local', None)
data['enabledPlugins']['prose-craft@prose-craft'] = True
p.write_text(json.dumps(data, indent=2) + '\n')
print("settings.json updated")
PY
```

- [ ] **Step 2: Update `~/.claude/plugins/installed_plugins.json`** — remove the `prose-craft@local` entry (if present from the earlier work this session) so Claude Code reinstalls fresh from the marketplace on next launch.

```bash
python3 << 'PY'
import json
from pathlib import Path
p = Path.home() / '.claude/plugins/installed_plugins.json'
data = json.loads(p.read_text())
removed = data['plugins'].pop('prose-craft@local', None)
print(f"installed_plugins.json: removed prose-craft@local entry: {bool(removed)}")
p.write_text(json.dumps(data, indent=4) + '\n')
PY
```

- [ ] **Step 3: Update `~/.claude/plugins/known_marketplaces.json`** — ensure the prose-craft marketplace is registered.

```bash
python3 << 'PY'
import json
from pathlib import Path
p = Path.home() / '.claude/plugins/known_marketplaces.json'
data = json.loads(p.read_text())
if 'prose-craft' not in data:
    data['prose-craft'] = {
        'source': {'source': 'git', 'url': 'https://github.com/TimSimpsonJr/prose-craft.git'},
        'installLocation': str(Path.home() / '.claude/plugins/marketplaces/prose-craft'),
    }
    p.write_text(json.dumps(data, indent=4) + '\n')
    print("known_marketplaces.json: added prose-craft entry")
else:
    print("known_marketplaces.json: prose-craft entry already present")
PY
```

- [ ] **Step 4: Restart Claude Code.** (User action.) On launch, Claude Code will:

1. Read settings.json and see `prose-craft@prose-craft` is enabled.
2. Notice no install record in installed_plugins.json.
3. Clone the marketplace at `~/.claude/plugins/marketplaces/prose-craft/` if absent.
4. Install plugin v2.1.0 to `~/.claude/plugins/cache/prose-craft/prose-craft/2.1.0/`.

- [ ] **Step 5: Refresh the v2.1.0 register template into the user-data path.**

Task B1 step 2 intentionally skipped copying the old 2.0.0 `register-template.md`. Now that the v2.1.0 install exists, copy the new template (with the `triggers:` frontmatter) directly into the user-data path so it's available for future `/prose-craft-init` invocations and any user who manually copies the template:

```bash
PLUGIN_DIR=~/.claude/plugins/cache/prose-craft/prose-craft/2.1.0
cp "$PLUGIN_DIR/template-data/registers/register-template.md" \
   ~/.claude/data/prose-craft/registers/register-template.md
head -10 ~/.claude/data/prose-craft/registers/register-template.md
# Expected: file starts with --- YAML frontmatter including triggers: block
```

- [ ] **Step 6: Verify after restart.**

```bash
# Marketplace install path exists
ls ~/.claude/plugins/cache/prose-craft/prose-craft/2.1.0/ | head -10
# Expected: .claude-plugin/, skills/, agents/, scripts/, setup/, template-data/, README.md, LICENSE (or similar)

# Old local install path is still there (deleted in Task B3)
ls ~/.claude/plugins/cache/local/prose-craft/2.0.0/.claude-plugin/plugin.json 2>/dev/null && echo "local install still present (expected)"

# Confirm skills resolve — try in a Claude Code session:
#   /prose-craft         → should fire (or report missing init if data dir is empty)
#   /prose-craft-init    → should fire
#   /prose-craft-learn   → should fire

# Confirm the data-path register-template has the new frontmatter
head -5 ~/.claude/data/prose-craft/registers/register-template.md
# Expected: starts with --- and contains "triggers:"
```

---

### Task B3: Clean up the old local install on Mac

**Files:**
- Delete: `~/.claude/plugins/cache/local/prose-craft/` (whole directory)

- [ ] **Step 1: Confirm marketplace install is working** before deleting the old copy. Both `/prose-craft` and `/prose-craft-init` should resolve from the marketplace path. Verify with a one-line interactive check in a Claude Code session.

- [ ] **Step 2: Delete the old local install.**

```bash
rm -rf ~/.claude/plugins/cache/local/prose-craft/
ls ~/.claude/plugins/cache/local/ 2>/dev/null
# Expected: empty, or only other local plugins (seo-toolkit etc.) if any exist
```

- [ ] **Step 3: Restart Claude Code one more time** to confirm the plugin still resolves from the marketplace path alone (no fallback to local).

---

## Phase C — dotfiles-claude restructure (direct push to main)

This phase happens in the user's dotfiles repo at `~/dotfiles-claude/`. Per the user's workflow choice, changes go directly to `main` (no PR).

### Task C1: Branch and stage the data layer

**Files:**
- Create: `~/dotfiles-claude/claude/data/prose-craft/...` (populated from Mac's `~/.claude/data/prose-craft/`)
- Delete: `~/dotfiles-claude/claude/local-plugins/prose-craft/` (entire directory)

- [ ] **Step 1: Pull latest dotfiles.**

```bash
cd ~/dotfiles-claude
git checkout main
git pull --ff-only
```

- [ ] **Step 2: Copy the personal data layer from Mac (now canonical).**

```bash
mkdir -p claude/data/prose-craft
cp -R ~/.claude/data/prose-craft/. claude/data/prose-craft/
ls claude/data/prose-craft/
# Expected: registers/  learning/
```

- [ ] **Step 3: Delete the legacy local-plugin tree for prose-craft.**

```bash
git rm -rf claude/local-plugins/prose-craft/
```

(The other local-plugins entries — seo-toolkit etc. — remain untouched.)

- [ ] **Step 4: Stage and verify.**

```bash
git status
# Expected:
#   deleted:    claude/local-plugins/prose-craft/...
#   new file:   claude/data/prose-craft/registers/...
#   new file:   claude/data/prose-craft/learning/...
```

---

### Task C2: Update `scripts/install-mac.sh` to handle the data layer

**Files:**
- Modify: `~/dotfiles-claude/scripts/install-mac.sh`

- [ ] **Step 1: Read the current script** to find the existing "Copying local plugins" loop.

```bash
cat ~/dotfiles-claude/scripts/install-mac.sh
```

- [ ] **Step 2: Add a new "Copying user data layers" block** after the existing "Copying local plugins" block in the `stage1()` function. Insert this verbatim:

```bash
echo "Copying user data layers..."
if [[ -d "$CLAUDE_SRC/data" ]]; then
  mkdir -p "$CLAUDE_DST/data"
  for data_dir in "$CLAUDE_SRC/data"/*/; do
    plugin_name="$(basename "$data_dir")"
    target="$CLAUDE_DST/data/$plugin_name"
    backup_if_exists "$target"
    mkdir -p "$target"
    cp -R "$data_dir." "$target/"
    echo "  -> $plugin_name"
  done
fi
```

(`$CLAUDE_SRC` and `$CLAUDE_DST` are the existing script-scope variables; `backup_if_exists` is the existing helper.)

The local-plugins loop above it stays as-is — it'll naturally no-op for prose-craft now that `claude/local-plugins/prose-craft/` is gone, but still handles seo-toolkit and any future local plugins.

- [ ] **Step 3: Syntax-check the script.**

```bash
bash -n scripts/install-mac.sh && echo "syntax OK"
```

- [ ] **Step 4: Stage.**

```bash
git add scripts/install-mac.sh
```

---

### Task C3: Update `scripts/snapshot-from-windows.sh` — add pre-flight guard, prose-craft skip, data sync block

**Files:**
- Modify: `~/dotfiles-claude/scripts/snapshot-from-windows.sh`

This is the highest-risk script edit. The pre-flight check is the load-bearing change — without it, an interim-state snapshot from Windows would erase Mac's canonical data layer from the dotfiles repo.

- [ ] **Step 1: Read the current script** to locate:
- the destructive cleanup line (currently around line 30: `find "$CLAUDE_DST" -mindepth 1 ! -name '.gitkeep' -exec rm -rf {} + 2>/dev/null || true`)
- the local-plugins block (currently lines 70-77)

```bash
cat ~/dotfiles-claude/scripts/snapshot-from-windows.sh
```

- [ ] **Step 2: Insert the pre-flight check.** Add this block at the very top of the script's main body (after `set -euo pipefail` and the `CLAUDE_SRC`/`CLAUDE_DST` variable definitions, but before the destructive cleanup):

```bash
# Pre-flight: refuse to snapshot if expected sources are missing on this
# machine. Prevents the destructive cleanup below from erasing dotfiles
# content that the running machine can't reconstruct.
declare -a missing=()
declare -a expected=(
  "$CLAUDE_SRC/data/prose-craft"  # add a line per durable per-plugin data tree
)
for path in "${expected[@]}"; do
  [[ -e "$path" ]] || missing+=("$path")
done
if (( ${#missing[@]} > 0 )); then
  echo "ABORT: expected source paths missing on this machine — refusing to snapshot." >&2
  printf '  - %s\n' "${missing[@]}" >&2
  echo "If a machine intentionally lacks these (e.g., not yet migrated), don't snapshot from it." >&2
  exit 1
fi
```

- [ ] **Step 3: Add a permanent prose-craft skip to the local-plugins loop.** Modify the existing loop body at lines 70-77; before the existing `mkdir -p` and `cp -r` calls, add a continue:

```bash
for plugin_dir in "$CLAUDE_SRC/plugins/cache/local"/*/; do
  plugin_name="$(basename "$plugin_dir")"
  if [[ "$plugin_name" == "prose-craft" ]]; then continue; fi   # data now lives in claude/data/prose-craft/
  # ... existing body
done
```

- [ ] **Step 4: Add a parallel data-sync block** after the local-plugins block:

```bash
mkdir -p "$CLAUDE_DST/data"
for data_dir in "$CLAUDE_SRC/data"/*/; do
  [[ -d "$data_dir" ]] || continue
  plugin_name="$(basename "$data_dir")"
  mkdir -p "$CLAUDE_DST/data/$plugin_name"
  cp -r "$data_dir." "$CLAUDE_DST/data/$plugin_name/"
done
```

- [ ] **Step 5: Syntax-check.**

```bash
bash -n scripts/snapshot-from-windows.sh && echo "syntax OK"
```

- [ ] **Step 6: Confirm the script won't run accidentally on Mac.** The pre-flight check expects `$CLAUDE_SRC/data/prose-craft` on the running machine. On Mac this exists (we just populated it in Task B1), so the script could in principle run on Mac. But this script's intended source is Windows. Document this in a script comment if not already obvious:

```bash
# This script snapshots a machine's ~/.claude/ state into the dotfiles repo.
# Typically run from Windows (the historical canonical machine), but the
# pre-flight check is machine-agnostic and will fail closed if any expected
# data layer is missing on the running machine.
```

Insert this comment near the top of the file (after the shebang and any existing header comment block).

- [ ] **Step 7: Stage.**

```bash
git add scripts/snapshot-from-windows.sh
```

---

### Task C4: Update `README.md` in the dotfiles repo

**Files:**
- Modify: `~/dotfiles-claude/README.md`

- [ ] **Step 1: Read the current README.**

```bash
cat ~/dotfiles-claude/README.md
```

- [ ] **Step 2: Update the "What's in here" section.** Find the line that says something like "two local plugins (`prose-craft`, `seo-toolkit`)" and update it to:

```
- **`claude/`** — sanitized snapshot of `~/.claude/` on the source machine. Includes `CLAUDE.md`, `settings.json`, `voice-dna.md`, hookify rules, user-level skills, one local plugin (`seo-toolkit`), per-plugin user data under `claude/data/` (currently `prose-craft`), and auto-memory files.
```

- [ ] **Step 3: Update the verification checklist** in the README (the section that says "Local plugins work: invoke /prose-craft...") so it reads correctly under the new architecture. `/prose-craft` should resolve from the marketplace install; `/prose-craft-init` is the new setup entry point.

- [ ] **Step 4: Stage.**

```bash
git add README.md
```

---

### Task C5: Commit and push the dotfiles changes

**Files:**
- (Operational — no further edits.)

- [ ] **Step 1: Review the full diff.**

```bash
cd ~/dotfiles-claude
git status
git diff --cached --stat
```

Expected:
- `claude/data/prose-craft/{registers,learning}/...` added (new files)
- `claude/local-plugins/prose-craft/...` deleted (many files)
- `scripts/install-mac.sh` modified
- `scripts/snapshot-from-windows.sh` modified
- `README.md` modified

- [ ] **Step 2: Commit.**

```bash
git commit -m "$(cat <<'EOF'
restructure: ship per-plugin user data under claude/data/

Moves prose-craft from claude/local-plugins/ (where it carried both
plugin code and user data) to claude/data/prose-craft/ (user data
only — plugin code now comes from the marketplace). Companion to the
prose-craft repo's v2.1.0 user-data-relocation work.

- claude/data/prose-craft/{registers,learning} populated from Mac's
  ~/.claude/data/prose-craft/ (now the canonical source).
- claude/local-plugins/prose-craft/ removed entirely.
- scripts/install-mac.sh: adds a per-plugin data-layer sync loop.
- scripts/snapshot-from-windows.sh: pre-flight check refuses to run
  if expected source data paths are missing on the running machine
  (prevents an interim-state snapshot from erasing canonical data);
  permanent prose-craft skip in the local-plugins loop; new data-
  layer block.
- README.md: updated "What's in here" + verification checklist.

Windows migration is deferred — when ready, pull this repo, run
install-mac.sh's equivalent flow on Windows (or manually xcopy the
data layer), then switch the install to marketplace.
EOF
)"
```

- [ ] **Step 3: Push.**

```bash
git push origin main
```

---

## Phase D — Windows migration (documentation only; user executes when home)

This phase lives in the design doc (§6 Phase 2) but is captured here as a checklist artifact so the user has it handy on Windows.

### Task D1: Save a Windows migration cheat-sheet to the dotfiles repo

**Files:**
- Create: `~/dotfiles-claude/docs/windows-migration.md`

- [ ] **Step 1: Create the docs directory if it doesn't exist.**

```bash
cd ~/dotfiles-claude
mkdir -p docs
```

- [ ] **Step 2: Write the cheat-sheet** to `docs/windows-migration.md`:

```markdown
# Windows migration — prose-craft v2.1.0

Run these steps when home with Windows.

## Prereqs

- Mac side migration (Phase A + Phase B + Phase C in `docs/plans/2026-05-30-user-data-relocation-implementation.md` of the prose-craft repo) is complete.
- This dotfiles repo's `main` branch contains `claude/data/prose-craft/` reflecting Mac's canonical state.

## Steps

1. **Pull the latest dotfiles on Windows.**

   ```cmd
   cd %USERPROFILE%\dotfiles-claude
   git pull
   ```

2. **Copy the personal data layer to its new home.**

   ```cmd
   xcopy /E /I claude\data\prose-craft %USERPROFILE%\.claude\data\prose-craft
   ```

3. **Switch the plugin from local to marketplace install** in `%USERPROFILE%\.claude\`:

   - `settings.json` (`enabledPlugins`): delete `"prose-craft@local"`, add or set `"prose-craft@prose-craft": true`.
   - `plugins\installed_plugins.json`: delete the `prose-craft@local` entry; Claude Code will create the `prose-craft@prose-craft` entry on next launch.
   - `plugins\known_marketplaces.json`: ensure a `prose-craft` entry pointing at `https://github.com/TimSimpsonJr/prose-craft.git` exists.

4. **Restart Claude Code** and verify `/prose-craft`, `/prose-craft-init`, `/prose-craft-learn` all resolve.

5. **Delete the old local install:**

   ```cmd
   rmdir /S /Q %USERPROFILE%\.claude\plugins\cache\local\prose-craft
   ```

6. **Confirm bidirectional sync works.** Run the snapshot script:

   ```cmd
   bash scripts/snapshot-from-windows.sh
   git status
   ```

   `git status` should show no changes (the data layer was just copied from dotfiles in step 2, so nothing should differ on snapshot).

## Exit criteria

- `/prose-craft` works on Windows, sourcing data from `~/.claude/data/prose-craft/`.
- `snapshot-from-windows.sh` produces no spurious diffs.
- Either machine can be the canonical source going forward (whichever last ran the dotfiles round-trip wins).
```

- [ ] **Step 3: Commit.**

```bash
git add docs/windows-migration.md
git commit -m "docs: Windows migration cheat-sheet for prose-craft v2.1.0"
git push origin main
```

---

## Self-review checklist

After completing all tasks, before declaring the work done:

- [ ] `python3 -m pytest tests/` passes in the prose-craft repo
- [ ] `bash -n scripts/install-mac.sh && bash -n scripts/snapshot-from-windows.sh` in dotfiles repo (syntax check)
- [ ] Grep across the prose-craft repo for `${CLAUDE_PLUGIN_ROOT}/registers\|${CLAUDE_PLUGIN_ROOT}/learning\|plugins/cache/local/prose-craft` — should be empty in skills/, agents/, setup/, README.md, MANIFEST.md
- [ ] `ls ~/.claude/data/prose-craft/registers/` shows every register file with `triggers:` frontmatter
- [ ] `/prose-craft` and `/prose-craft-init` resolve on Mac from the marketplace install path
- [ ] Mac's `~/.claude/plugins/cache/local/prose-craft/` is deleted
- [ ] dotfiles `main` has `claude/data/prose-craft/` populated and no `claude/local-plugins/prose-craft/`
- [ ] dotfiles `docs/windows-migration.md` exists for the Phase D execution later

When the user is next at Windows, they execute Phase D from the cheat-sheet.
