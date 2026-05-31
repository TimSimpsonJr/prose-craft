---
name: prose-craft-init
description: Initialize prose-craft on this machine and extract a voice register. Creates the user data directory, copies templates, and walks you through the extraction process to create your first register. Also use this to add a new register later. Invoke via /prose-craft-init.
---

# Prose Craft Init

This skill bootstraps the prose-craft user-data directory and walks you through extracting a voice register. It's idempotent — running it again is how you add a new register or refresh templates after a plugin update.

## Phase 1: Bootstrap the data directory

1. **Always** ensure the required subdirectories exist. `mkdir -p` is idempotent — these calls are safe to run on every invocation, and they protect against partial-init states (e.g., the root exists but `registers/` was deleted, or the data root was created by a prior plugin version without all its subdirs):

   ```bash
   mkdir -p ~/.claude/data/prose-craft/registers
   mkdir -p ~/.claude/data/prose-craft/learning/snapshots
   ```

2. For every file under `${CLAUDE_PLUGIN_ROOT}/template-data/`, check whether the corresponding target under `~/.claude/data/prose-craft/` exists. If the target is missing, copy the template file there. **Never overwrite a file that already exists at the target.** This pattern lets plugin updates ship new template files (which appear at the data path on next init invocation) without ever touching existing user data.

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
