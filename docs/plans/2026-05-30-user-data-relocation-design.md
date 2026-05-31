# Design: Relocate User Data Out of the Plugin Install Path

**Date:** 2026-05-30
**Status:** Design pending user review
**Project:** prose-craft (Claude Code plugin) + dotfiles-claude (sync mechanism)
**References:**
- Companion sync infrastructure: `~/dotfiles-claude/` (private snapshot repo)
- Prior design (out of scope here): `2026-05-28-skillopt-learning-loop-design.md`

---

## 1. Problem

The prose-craft plugin currently mixes plugin code (skills, agents, scripts) and per-user data (registers, learning artifacts) inside a single install directory. Claude Code installs plugins to `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/` and overwrites that directory on update.

Result: any marketplace update destroys personal registers and accumulated learning data. The two coping strategies available today are both unsatisfying:

- **Skip marketplace updates.** Plugin improvements never reach the install.
- **Install prose-craft as a local plugin and sync everything from dotfiles.** Plugin code and user data ride the same sync channel. Plugin improvements only reach the install when the user manually refreshes the dotfiles snapshot from the canonical machine — which is the same friction that motivated this design.

The current setup also conflates two distinct concerns: "what the plugin does" (code, shareable, public) and "what the plugin knows about me" (registers, learning artifacts, personal). They have different lifecycles, different audiences, and different right answers for the question "who owns this file?".

## 2. Goals and non-goals

**Goals**
- Personal data lives at a stable filesystem location that is invariant under plugin updates.
- Marketplace install delivers only plugin code; user data is never touched by install or update.
- The dotfiles-claude repo can sync only the personal data layer across machines (Mac, Windows).
- Cross-platform: `~/` must resolve correctly on Mac, Linux, and Windows.
- Non-destructive migration for existing personal data on both machines.

**Non-goals**
- Reworking the extraction and learning processes themselves (planned for a separate session).
- Supporting multi-user installs on the same machine.
- Building any kind of UI around register management.
- Generalizing the data-relocation pattern to other plugins in this design (the pattern is reusable, but only prose-craft is migrating now).

## 3. Architecture

User data moves to a new canonical location outside the plugin install path:

```
~/.claude/data/prose-craft/
  registers/
    <user's voice profiles>.md    # YAML frontmatter declares triggers; see §4.5
    register-template.md          # reference template, shipped from plugin on first run
  learning/
    accumulator.md
    splits.md
    ablation-log.md
    bootstrap-run.md
    judge-agreement.md
    snapshots/
      <piece>-<timestamp>-<stage>.md
      manifest.json
    extraction-artifacts/         # pass-1/pass-2 outputs from each register's creation run
      <register-name>/
        pass-1-output.md
        pass-2-output.md
```

`extraction-artifacts/` lives under `learning/` (not under `registers/`) because its contents are by-products of the extraction *process*, not the registers themselves. The dotfiles repo's current snapshot puts them under `registers/`; the migration in §6 moves them to the new location.

**Why `~/.claude/data/<plugin>/`:**

- Mirrors the rest of Claude Code's filesystem convention (everything user-level lives under `.claude/`); discoverable for debugging.
- `~/.claude/` already exists on every Claude Code machine; no new top-level directory needs to be introduced.
- `~` is resolved correctly on all platforms by Claude Code's tool layer and by shells (Bash, zsh, PowerShell with proper expansion).
- `data/` cleanly distinguishes durable user content from `cache/` (transient), `plugins/` (code), `sessions/` (per-conversation), `projects/` (per-project).
- The pattern `~/.claude/data/<plugin-name>/` extends naturally to other plugins later, without further architectural work.

XDG-style paths (`~/.config/`, `~/.local/share/`) were considered and rejected: Windows does not have native XDG directories, and forcing the split between "config" (registers) and "state" (learning) buys nothing here.

## 4. prose-craft repo changes

### 4.1 Path rewrites

Every reference to `${CLAUDE_PLUGIN_ROOT}/registers/` and `${CLAUDE_PLUGIN_ROOT}/learning/` inside the plugin updates to the new path. The references are:

| File | Count | Pattern |
|---|---|---|
| `skills/prose-craft/SKILL.md` | 1 | `${CLAUDE_PLUGIN_ROOT}/registers/[name].md` |
| `skills/prose-craft-learn/SKILL.md` | 14 | mix of registers/, learning/snapshots/, learning/accumulator.md, learning/splits.md, learning/judge-agreement.md, learning/ablation-log.md |
| `setup/extraction-guide.md` | 3 | `${CLAUDE_PLUGIN_ROOT}/registers/...` |

Total: ~18 substitutions across 3 files. Each `${CLAUDE_PLUGIN_ROOT}/registers/` becomes `~/.claude/data/prose-craft/registers/`; each `${CLAUDE_PLUGIN_ROOT}/learning/` becomes `~/.claude/data/prose-craft/learning/`.

**Also rewrite the hardcoded dual-write target in `skills/prose-craft-learn/SKILL.md` (currently lines 220-225 of main).** The existing language tells the learning loop to apply each accepted edit to both:

- `~/.claude/plugins/cache/local/prose-craft/2.0.0/{target-path}`
- `prose-craft/{target-path}` (the source repo)

In the new architecture this is wrong on both halves. Replace with target-aware routing:

| Target type | New write location |
|---|---|
| Register file (`registers/<name>.md`) | `~/.claude/data/prose-craft/registers/<name>.md` |
| `accumulator.md` | `~/.claude/data/prose-craft/learning/accumulator.md` |
| Other learning artifacts (`splits.md`, `ablation-log.md`, `judge-agreement.md`) | `~/.claude/data/prose-craft/learning/<name>` |
| Plugin-code file (agent body, skill body, scripts) | **Do not apply locally.** Record the proposed edit in `~/.claude/data/prose-craft/learning/pending-upstream.md` for review and possible upstreaming via PR to the prose-craft repo. |

The plugin-code case is the load-bearing change: marketplace updates own the install path, so any local write would be clobbered on next plugin update. Auto-applying to a co-located source repo (the old behavior) is also fragile (assumes the user has cloned the source, that it's at a known path, that they want learning-loop output written to their working tree). Deferring those edits to an explicit upstream queue keeps the learning loop's authority over plugin code visible rather than silent.

**`pending-upstream.md` format (defined now so the file doesn't degenerate into an unstructured dump):**

Each accepted plugin-code edit appends one entry of the form:

```markdown
## <ISO-8601 timestamp> · <target-path>

- **Source candidate:** `<learn-review proposal id or short label>`
- **Rationale:** <one-paragraph summary of the gate evidence supporting this edit>

```diff
<unified diff: old vs. new at target-path>
```

```

Entries append newest-first (most recent at top) so the most actionable upstream candidates are visible without scrolling. The richer UX of surfacing these to the user (e.g., a `/prose-craft-pending` skill) is out of scope here and lands in the planned extraction/learning rework — but the on-disk structure is committed now so the rework has a clean substrate to read from.

`scripts/discipline_check.py` does not reference user data paths — it takes paths as CLI args and only resolves one file (`banned_phrases.txt`) relative to itself. No change needed.

### 4.2 Directory restructuring

The plugin repo's own `registers/` and `learning/` directories disappear from the repo root. Their reference content moves to `template-data/`. A new `skills/prose-craft-init/` skill takes over setup and extraction:

```
prose-craft/
  template-data/                  # NEW — shipped, read-only starter content
    registers/
      register-template.md        # was registers/register-template.md
    learning/
      accumulator.md              # was learning/accumulator.md (the empty starter)
  skills/
    prose-craft/SKILL.md          # paths rewritten per §4.1; first-run check per §4.4
    prose-craft-learn/SKILL.md    # paths rewritten per §4.1
    prose-craft-init/SKILL.md     # NEW — see §4.3
  registers/                      # REMOVED
  learning/                       # REMOVED
  agents/                         # unchanged structurally
  scripts/                        # unchanged
  setup/                          # unchanged (still contains pass-1/pass-2/brief-stripping/sample-collection prompts referenced by the init skill)
```

`template-data/` is documented in the README as "starter content; the init skill copies these into `~/.claude/data/prose-craft/` on first run. Do not edit your active registers here — edit them at the user-data path."

### 4.3 The init skill (`/prose-craft-init`)

A new skill at `skills/prose-craft-init/SKILL.md` consolidates the work that today is spread across the five `setup/*.md` documents (which require the user to drive the process manually with Sonnet). The init skill is invocable as `/prose-craft-init`.

**Frontmatter:**

```yaml
---
name: prose-craft-init
description: Initialize prose-craft on this machine and extract a voice register. Creates the user data directory, copies templates, and walks you through the extraction process to create your first register. Also use this to add a new register later. Invoke via /prose-craft-init.
---
```

**Responsibilities:**

1. **Bootstrap the data directory** (idempotent, safe to re-run):
   - If `~/.claude/data/prose-craft/` doesn't exist, create `registers/` and `learning/snapshots/` underneath it.
   - Copy every file under `${CLAUDE_PLUGIN_ROOT}/template-data/` into the matching location under `~/.claude/data/prose-craft/`, only when the target file doesn't already exist. This means subsequent plugin updates can add new template files without ever overwriting user data.

2. **Detect state and route:**
   - **Fresh install** (no registers besides `register-template.md`): walk through first-time extraction (step 3).
   - **Existing setup** (at least one populated register): ask whether the user wants to add a new register or re-extract an existing one. Default to "add new."

3. **Extraction walkthrough** (current process — to be replaced by the planned extraction/learning rework, but works as-is until then):
   1. Ask the user what kind of writing this register is for; derive a register name (e.g., `advocacy`, `personal`).
   2. Reference `${CLAUDE_PLUGIN_ROOT}/setup/sample-collection.md`: ask the user for 10-20 samples of their own writing in this register, plus 10 baseline samples (Claude-default outputs on similar topics) — guide them through how to generate the baseline batch if they don't already have it.
   3. Dispatch a Sonnet agent with the prompt at `${CLAUDE_PLUGIN_ROOT}/setup/pass-1-prompt.md`, filling in P1 (baselines) and P2 (user samples). Save the output to a scratch location inside `~/.claude/data/prose-craft/learning/extraction-artifacts/<register>/pass-1-output.md`.
   4. Dispatch a second Sonnet agent with `${CLAUDE_PLUGIN_ROOT}/setup/pass-2-prompt.md` over the pass-1 output. Save to `pass-2-output.md` in the same scratch location.
   5. Convert the pass-2 output into a register file using the structure in `${CLAUDE_PLUGIN_ROOT}/template-data/registers/register-template.md`, and save to `~/.claude/data/prose-craft/registers/<register>.md`.
   6. If the user wants brief-stripping support, walk through `${CLAUDE_PLUGIN_ROOT}/setup/brief-stripping-guide.md`.

4. **Confirm and exit:** tell the user the register is ready and how to use it (`/prose-craft` will detect the new register on next invocation).

The legacy `setup/extraction-guide.md` becomes redundant once the init skill exists — the skill *is* the guide, executable. We'll keep `extraction-guide.md` as a static reference (for users who want to read the process top-down before running it) but it stops being the primary entry point. The other four `setup/*.md` documents (pass-1, pass-2, brief-stripping, sample-collection) remain as prompts/guides that the init skill reads at runtime.

**Note on future rework:** the user has flagged that the extraction and learning processes will be reworked in a follow-on session. The init skill's bootstrap responsibility (§4.3.1) is stable; the extraction walkthrough (§4.3.3) will likely be replaced wholesale by the new process. The skill structure provides a stable insertion point for whatever the new process becomes.

### 4.4 First-run check inside `skills/prose-craft/SKILL.md`

At the top of `skills/prose-craft/SKILL.md`, before any generation logic, add a small guard:

> **Verify setup.** Before doing anything else:
>
> 1. Check whether `~/.claude/data/prose-craft/registers/` contains at least one register file other than `register-template.md`. If yes, proceed with normal generation.
> 2. If no register files exist, tell the user: "prose-craft isn't initialized on this machine yet. Run `/prose-craft-init` to create your first register." Stop.

The guard is intentionally narrow: the `prose-craft` skill does generation, not setup. Anything that touches the data directory or walks the user through extraction lives in `/prose-craft-init`. This keeps the two skills cleanly separated by responsibility.

### 4.5 Register discovery via per-register frontmatter

Today `skills/prose-craft/SKILL.md` configures registers in an inline HTML-comment block users are expected to edit after extraction (current lines 10-31). Under a marketplace install that's broken — every plugin update overwrites SKILL.md, wiping the user's register config.

The new architecture moves register declarations into each register file itself as YAML frontmatter. Each register is self-describing:

```yaml
---
triggers:
  - personal essays
  - blog posts
  - reflective writing
---

# Personal Register

[voice feature description...]
```

The register's *name* is the filename minus `.md` (so `~/.claude/data/prose-craft/registers/personal.md` is the `personal` register). The frontmatter's `triggers` array lists the writing contexts that activate this register.

**Discovery flow in `skills/prose-craft/SKILL.md`** (replacing the current Register Detection section):

> ## Register Detection
>
> On invocation, determine which register to use from context:
>
> 1. Glob `~/.claude/data/prose-craft/registers/*.md`, excluding `register-template.md`.
> 2. For each file, read the YAML frontmatter. If a file has no frontmatter or no `triggers` field, skip it (it's not a configured register).
> 3. Match the current writing context against each register's triggers. If exactly one register matches, use it. If multiple match, ask the user which. If none match, ask the user which register to use (or to run `/prose-craft-init` if none configured).
> 4. Read the chosen register's body (everything after the frontmatter) — that's the voice feature description.

**Init skill responsibility** (§4.3 step 5 extended): when the init skill creates a register file, it asks the user for the trigger contexts (drawing from the user's answer to step 1 about what kind of writing this register is for) and writes them as `triggers:` in the new register file's frontmatter.

**Template update:** `template-data/registers/register-template.md` gains a frontmatter block at the top with placeholder `triggers:` showing the format. The init skill copies the template, then rewrites the frontmatter with the user's actual triggers.

**Migration of existing registers** (handled in §6 step 2): the user's existing dotfiles registers (`advocacy.md`, `personal.md`, `dystopian-fiction.md`) don't have `triggers:` frontmatter yet. The natural source — the inline register-detection block in `skills/prose-craft/SKILL.md` — is empty in the current repo (it still holds only the template HTML comment), so triggers can't be extracted from there. Migration prompts the user interactively for triggers per register instead. If the user declines a register, write `triggers: []` and let the discovery flow's ambiguity fallback handle it (the user gets asked per invocation until they populate triggers).

### 4.6 Documentation updates

The current repo has documentation files that describe the old architecture explicitly. These must be updated as part of this PR — leaving them stale would leave dangerous misinformation pointing at the soon-to-be-empty install path.

**Required updates:**

- **`MANIFEST.md`** — multiple sections need rewriting:
  - The `registers/` line (currently `Template + installed-only live data`) becomes `Template only; live registers at ~/.claude/data/prose-craft/registers/`.
  - The `learning/accumulator.md` line (currently `Clean/empty in the repo; the live accumulator is installed-only`) becomes `Empty template at template-data/; live accumulator at ~/.claude/data/prose-craft/learning/accumulator.md`.
  - The "Dual location (critical)" key-relationship block needs the most significant rewrite: drop the `~/.claude/plugins/cache/local/prose-craft/<ver>/` references, drop the "Never full-reinstall (it clobbers live data)" warning (no longer accurate), and replace with: "Plugin install at `~/.claude/plugins/cache/prose-craft/prose-craft/<ver>/` is owned by marketplace updates and disposable. Live data lives at `~/.claude/data/prose-craft/` and is invariant under plugin updates."
- **`README.md`** — update any user-facing setup language that refers to the old install layout. Specifically the "register configuration" instructions, if present, should point at `/prose-craft-init` rather than at editing SKILL.md inline.
- **`setup/extraction-guide.md`** — already in §4.1's path rewrites; also update step 5 (the "edit SKILL.md to add your register" instruction) to reflect the frontmatter-based discovery (§4.5) instead.

The MANIFEST update is the highest-priority of the three: it currently warns "Never full-reinstall (it clobbers live data)" and that warning becomes actively dangerous after migration (full reinstall is the *expected* update flow now). MANIFEST regeneration is mandatory before the PR merges (per the user's repo-maintenance convention).

### 4.7 Tuning to upstream

Alongside this restructure, sync legitimate plugin-code improvements that exist only in the user's local install today:

| File | Change | Source |
|---|---|---|
| `agents/prose-review.md` | Add 3 new advisory rules (Caps overuse, Performed Specificity, Hollow Anadiplosis) + full §25 Performed Specificity reference section | Cherry-pick from dotfiles install at `~/.claude/plugins/cache/local/prose-craft/2.0.0/agents/prose-review.md` |
| `.claude-plugin/plugin.json` | Add `"author": {"name": "Tim Simpson"}` field | Trivial |
| `agents/craft-review.md` | **No change.** The only diff between local and main is personal author refs (Doctorow, Housel, Urban, Thompson) which are explicitly out of scope for upstreaming. The banned-pattern self-check work (commit bed14dd) is already in main. | — |

## 5. dotfiles-claude repo changes

### 5.1 Directory restructure

The dotfiles repo replaces its prose-craft-as-local-plugin tree with a personal-data tree:

```
dotfiles-claude/claude/
  data/                                  # NEW
    prose-craft/
      registers/
        advocacy.md                      # YAML frontmatter with triggers (§4.5)
        dystopian-fiction.md             # YAML frontmatter with triggers (§4.5)
        personal.md                      # YAML frontmatter with triggers (§4.5)
      learning/
        accumulator.md
        ablation-log.md
        bootstrap-run.md
        splits.md
        judge-agreement.md               # if present
        snapshots/
        extraction-artifacts/            # moved from registers/ (per §3); per-register subdirs
  local-plugins/
    prose-craft/                         # REMOVED entirely
    seo-toolkit/                         # unchanged
```

The contents of `claude/local-plugins/prose-craft/2.0.0/{registers,learning}/` move to `claude/data/prose-craft/{registers,learning}/`, with two structural adjustments: (1) `extraction-artifacts/` moves from under `registers/` to under `learning/` (per §3); (2) each register file gains a YAML frontmatter block with its `triggers:` array (per §4.5). The rest of `claude/local-plugins/prose-craft/` (plugin code, `.claude-plugin/`, `skills/`, `agents/`, `scripts/`, `setup/`) is deleted — the marketplace install owns that content now.

### 5.2 Script changes

**`scripts/install-mac.sh`:** keep the existing `Copying local plugins` loop (still needed for `seo-toolkit` and any future local plugins). Once `claude/local-plugins/prose-craft/` is removed from the repo it stops iterating over prose-craft naturally — no explicit skip needed. Add a new step before or after:

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

**`scripts/snapshot-from-windows.sh`:** this is the more dangerous edit. The script starts with a destructive cleanup at line 30:

```bash
find "$CLAUDE_DST" -mindepth 1 ! -name '.gitkeep' -exec rm -rf {} + 2>/dev/null || true
```

That cleanup wipes everything under `claude/` in the dotfiles repo before rebuilding from Windows sources. After our restructure, `claude/data/prose-craft/` will live in dotfiles as the canonical Mac-derived personal data layer. If the snapshot script runs on Windows during the interim — when Windows has no `~/.claude/data/prose-craft/` yet — the destructive cleanup deletes `claude/data/prose-craft/` from the repo working tree, and nothing repopulates it (the local-plugins skip means prose-craft doesn't come back via that path either). One accidental snapshot run would erase Mac's accumulated personal data from dotfiles.

A "skip + no-op" guard is not sufficient. We need a **hard pre-flight check** that aborts the snapshot before the destructive cleanup if any expected source dir is missing on this machine. Concretely, add at the very top of the script (before the cleanup):

```bash
# Pre-flight: refuse to snapshot if expected sources are missing.
# Prevents the destructive cleanup below from blowing away dotfiles content
# that this machine can't reconstruct.

declare -a missing=()
declare -a expected=(
  "$CLAUDE_SRC/data/prose-craft"      # add a line per durable per-plugin data tree
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

The `expected` list grows over time as new durable data layers are added. The check fails closed — better to abort and tell the user than to silently delete their canonical state.

Then, modify the existing local-plugins block at lines 70-77 to **skip prose-craft permanently** — once prose-craft moves to `data/`, it should never round-trip back into `local-plugins/` even if a stale `cache/local/prose-craft/` lingers on Windows:

```bash
for plugin_dir in "$CLAUDE_SRC/plugins/cache/local"/*/; do
  plugin_name="$(basename "$plugin_dir")"
  if [[ "$plugin_name" == "prose-craft" ]]; then continue; fi   # data now lives in claude/data/prose-craft/
  ...
done
```

Add a parallel block for the data layer:

```bash
mkdir -p "$CLAUDE_DST/data"
for data_dir in "$CLAUDE_SRC/data"/*/; do
  [[ -d "$data_dir" ]] || continue
  plugin_name="$(basename "$data_dir")"
  mkdir -p "$CLAUDE_DST/data/$plugin_name"
  cp -r "$data_dir." "$CLAUDE_DST/data/$plugin_name/"
done
```

The pre-flight check is the load-bearing addition. The local-plugins skip and the new data block are mechanical add-ons.

## 6. Migration sequence

The rollout is **two phases**. Phase 1 happens now on Mac, while the user is away from Windows. Phase 2 happens when the user is home again. During the interim between phases, both machines remain operational: Mac on the new architecture; Windows on the legacy local-plugin setup. Mac is the canonical source for personal data during the interim.

Personal data is copied (not moved) at every step. The old `cache/local/prose-craft/` is only deleted after the new install is verified, so a rollback path exists at each transition.

### Phase 1 — Mac migration + repo restructure (this session)

**Step 1 — Update the prose-craft repo.**
- All §4 changes on a feature branch: path rewrites (§4.1, including the prose-craft-learn hardcoded paths), directory restructure (§4.2), new init skill (§4.3), first-run check in `prose-craft` SKILL.md (§4.4), register discovery via frontmatter (§4.5), documentation updates to MANIFEST/README/extraction-guide (§4.6), prose-review.md tuning + plugin.json author field (§4.7).
- Regenerate `MANIFEST.md` to reflect the new structure per §4.6 — include in the same PR. (Maintaining MANIFEST through PRs is a standing convention; calling it out here because the current MANIFEST contains an actively dangerous warning that would survive otherwise.)
- Verify with a clean test install (fresh dir or scratch machine): marketplace install creates `template-data/` at the install root, no `registers/` or `learning/`, and `/prose-craft-init` successfully creates `~/.claude/data/prose-craft/`, writes a register with the correct frontmatter `triggers:` block, and `/prose-craft` then discovers it.
- Open PR; codex-impl-review runs at the PR gate per autonomous mode.
- Merge to `main`. Bump plugin version to **2.1.0**.

**Step 2 — Mac: migrate personal data to the new location.**

```bash
SRC=~/.claude/plugins/cache/local/prose-craft/2.0.0
DST=~/.claude/data/prose-craft
mkdir -p $DST/{registers,learning}

# Register .md files (just the markdown, not the extraction-artifacts subdir)
cp -R $SRC/registers/*.md $DST/registers/

# Everything under learning/, verbatim
cp -R $SRC/learning/. $DST/learning/

# extraction-artifacts moves from registers/ (old location) to learning/ (new location, per §3)
if [[ -d $SRC/registers/extraction-artifacts ]]; then
  cp -R $SRC/registers/extraction-artifacts $DST/learning/
fi
```

Verify: file count under `$DST/registers/` matches the count of `$SRC/registers/*.md`, file count under `$DST/learning/` matches the count of `$SRC/learning/*` plus the extraction-artifacts subtree.

Then add YAML frontmatter to each migrated register file (per §4.5). **Triggers are not extractable from the current `skills/prose-craft/SKILL.md`** — that file still holds only the placeholder HTML comment, so there's no inline register-detection block to mine. Prompt the user instead: for each register file (`advocacy.md`, `personal.md`, `dystopian-fiction.md`, plus any others present), ask "What writing contexts should activate this register?" and write the response into the file's frontmatter. Example for `personal.md`:

```yaml
---
triggers:
  - personal essays
  - blog posts
  - reflective writing
---
```

If the user declines to specify triggers for a register, write an empty `triggers: []` block; prose-craft will then always ask the user which register to use until that register's triggers get populated later. Don't silently invent triggers from filenames — better to surface the configuration gap.

**Step 3 — Mac: switch from local install to marketplace install.**
- `~/.claude/settings.json`: remove or set `prose-craft@local: false`; ensure `prose-craft@prose-craft: true`.
- `~/.claude/plugins/installed_plugins.json`: delete the `prose-craft@local` entry. Claude Code will recreate the `prose-craft@prose-craft` entry on next launch if the marketplace is registered.
- `~/.claude/plugins/known_marketplaces.json`: re-add the `prose-craft` marketplace pointing at `https://github.com/TimSimpsonJr/prose-craft.git`.
- Restart Claude Code; verify `/prose-craft`, `/prose-craft-init`, and `/prose-craft-learn` all resolve from the marketplace install at `~/.claude/plugins/cache/prose-craft/prose-craft/2.1.0/`.
- Delete `~/.claude/plugins/cache/local/prose-craft/` (the old local install).

**Step 4 — dotfiles-claude: restructure to ship the personal data layer.**
- On the dotfiles repo, on a branch:
  - Create `claude/data/prose-craft/` populated from the now-canonical Mac state: `cp -R ~/.claude/data/prose-craft/. claude/data/prose-craft/`.
  - Delete `claude/local-plugins/prose-craft/` (Windows will pull from `claude/data/` when it migrates in Phase 2; the legacy local-plugin tree is no longer needed and would cause confusion if kept).
  - Update `scripts/install-mac.sh` and `scripts/snapshot-from-windows.sh` per §5.2 (add data block to both; add the prose-craft skip in snapshot's local-plugins loop).
  - Update the README's "What's in here" section: prose-craft is no longer listed under "two local plugins"; it's now described as "one local plugin (seo-toolkit), plus per-plugin user data under `claude/data/`."
- Commit and push the dotfiles branch; merge to main.

**Phase 1 exit criteria:**
- `/prose-craft` works on Mac, sourcing data from `~/.claude/data/prose-craft/`.
- Dotfiles repo's `main` branch contains the canonical personal data layer at `claude/data/prose-craft/` and no longer contains `claude/local-plugins/prose-craft/`.
- Windows is untouched; its `~/.claude/plugins/cache/local/prose-craft/` continues to function locally (the user is not actively syncing it to dotfiles during this interim).

### Phase 2 — Windows migration (when user is home)

Windows currently runs prose-craft as a local plugin at `~/.claude/plugins/cache/local/prose-craft/2.0.0/`, with personal data embedded inside. The migration mirrors Mac's Phase 1 steps 2-3 but pulls the personal data layer from dotfiles (which has Mac's accumulated state) rather than from the local install (which is now stale relative to whatever was changed on Mac during the interim).

**Step W1 — Pull dotfiles to get the latest data layer.**
```
cd %USERPROFILE%\dotfiles-claude  (or wherever the clone lives on Windows)
git pull
```
This brings down `claude/data/prose-craft/` reflecting whatever Mac has accumulated during the interim.

**Step W2 — Copy the personal data layer to the new location.**
```
xcopy /E /I dotfiles-claude\claude\data\prose-craft  %USERPROFILE%\.claude\data\prose-craft
```
(Or whatever the user's preferred Windows copy invocation is — install-mac.sh's logic could be ported to a `install-windows.ps1` later, but for this one-shot migration a manual copy is fine.)

**Step W3 — Switch from local install to marketplace install on Windows.**
- `%USERPROFILE%\.claude\settings.json`: remove `prose-craft@local: true`; ensure `prose-craft@prose-craft: true`.
- `%USERPROFILE%\.claude\plugins\installed_plugins.json`: delete the `prose-craft@local` entry.
- `%USERPROFILE%\.claude\plugins\known_marketplaces.json`: ensure the `prose-craft` marketplace is registered.
- Restart Claude Code; verify `/prose-craft`, `/prose-craft-init`, `/prose-craft-learn` resolve from the marketplace install.
- Delete `%USERPROFILE%\.claude\plugins\cache\local\prose-craft\`.

**Step W4 — Confirm bidirectional sync works.**
- Run `bash scripts/snapshot-from-windows.sh` on Windows; verify the dotfiles diff is empty (the data layer was just copied from dotfiles in step W2, so the snapshot should produce no changes).
- After this point, Windows is also a valid canonical source — both machines write to `claude/data/prose-craft/` in dotfiles.

**Phase 2 exit criteria:**
- `/prose-craft` works on Windows, sourcing data from `~/.claude/data/prose-craft/`.
- `snapshot-from-windows.sh` produces no spurious diffs.
- Both machines can be sync-canonical (whichever last ran the dotfiles round-trip wins).

## 7. Risks and mitigations

**Personal data loss during migration.** Each migration step copies; nothing is deleted until the new location is verified. Old `cache/local/prose-craft/` survives Phase 1 step 2 and only gets removed in step 3 after the marketplace install is confirmed working. The dotfiles repo holds a third copy at all times. Phase 2 on Windows similarly copies the data layer from dotfiles before any local cleanup.

**Marketplace install on a never-before-set-up machine.** The `/prose-craft-init` skill (§4.3) creates the directory tree and walks the user through extraction. The `prose-craft` skill itself refuses to generate until at least one register exists (§4.4).

**Future plugin updates introducing new template files.** New files added under `template-data/` reach users via the init skill's idempotent copy step. The "only copy if target doesn't exist" rule means user data is never overwritten — new template files just appear at the user-data path on next `/prose-craft-init` invocation, while existing user-edited files are left alone.

**`~` not resolving in some context.** Audited: every path reference is in markdown (read by Claude, which expands `~`) or shell scripts (which expand `~` natively). `discipline_check.py` doesn't reference user-data paths.

**Interim-state divergence between Mac and Windows.** During the gap between Phase 1 and Phase 2, Mac is the canonical source. Windows continues to operate on its legacy local install, with its own (now-stale) copy of personal data. Mitigations:
- The user is aware of this asymmetry and won't make meaningful register/learning changes on Windows during the interim.
- The snapshot script's permanent skip for prose-craft in the local-plugins loop (§5.2) prevents Windows from accidentally syncing a stale view of the data back into dotfiles if the script is run during the interim.
- Phase 2 step W2 pulls the personal data layer from dotfiles (which reflects Mac's state), explicitly *not* from Windows' stale cache/local copy. The Windows cache/local copy serves only as a safety net until Step W3 confirms the marketplace install works.

**Snapshot script writing to the wrong place after Windows pulls the new repo.** The two snapshot blocks (local-plugins with prose-craft skip, and data) operate on different source paths. The first run on Windows post-migration should produce no diffs — if it does, halt and inspect before committing.

**Marketplace install picking up the wrong version mid-restructure.** The plugin bump to 2.1.0 ensures any old `prose-craft@prose-craft` install (still at 2.0.0) reinstalls cleanly. Claude Code recognizes the version bump and refreshes from the marketplace clone on next launch.

## 8. Out of scope (future work)

- **Extraction and learning process rework** — planned for a separate session immediately after this design lands. The init skill (§4.3) is designed as a stable insertion point: its bootstrap responsibilities are independent of which extraction process it runs, so swapping `setup/pass-1-prompt.md` + `setup/pass-2-prompt.md` for the new approach is a localized change inside the skill body when the time comes.
- Whether `craft-review.md` should ship a "personal style examples" extension point (so the Doctorow/Housel-style references could live in a register-like personal layer rather than the agent body). Deferred to the extraction/learning rework.
- Applying the `~/.claude/data/<plugin>/` pattern to other plugins (e.g., seo-toolkit). The pattern is reusable, but only prose-craft is migrating in this design.
- A native `install-windows.ps1` script in the dotfiles repo. The Phase 2 Windows migration in §6 uses a manual `xcopy` because it's a one-shot operation; if the user later wants a repeatable Windows install path, that's a small follow-on.
