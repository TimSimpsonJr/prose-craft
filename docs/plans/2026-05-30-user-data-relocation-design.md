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
    <user's voice profiles>.md
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
```

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

`scripts/discipline_check.py` does not reference user data paths — it takes paths as CLI args and only resolves one file (`banned_phrases.txt`) relative to itself. No change needed.

### 4.2 Directory restructuring

The plugin repo's own `registers/` and `learning/` directories disappear from the repo root. Their reference content moves to `template-data/`:

```
prose-craft/
  template-data/                  # NEW — shipped, read-only starter content
    registers/
      register-template.md        # was registers/register-template.md
    learning/
      accumulator.md              # was learning/accumulator.md (the empty starter)
  registers/                      # REMOVED
  learning/                       # REMOVED
  skills/                         # unchanged (paths rewritten per §4.1)
  agents/                         # unchanged structurally
  scripts/                        # unchanged
  setup/                          # unchanged (paths rewritten per §4.1)
```

`template-data/` is documented in the README as "starter content; the plugin copies these into `~/.claude/data/prose-craft/` on first invocation. Do not edit your active registers here — edit them at the user-data path."

### 4.3 First-run init

At the top of `skills/prose-craft/SKILL.md`, before any generation logic, add:

> **First-run setup.** Before doing anything else:
>
> 1. Check whether `~/.claude/data/prose-craft/` exists. If yes, skip to step 5.
> 2. Create `~/.claude/data/prose-craft/registers/` and `~/.claude/data/prose-craft/learning/snapshots/`.
> 3. Copy every file under `${CLAUDE_PLUGIN_ROOT}/template-data/` into the corresponding location under `~/.claude/data/prose-craft/`. (Only copy files that don't already exist at the destination.)
> 4. Tell the user: "Initialized prose-craft data directory at `~/.claude/data/prose-craft/`. Before generating prose you need at least one register. Copy `~/.claude/data/prose-craft/registers/register-template.md` to e.g. `personal.md` and fill it in. See `${CLAUDE_PLUGIN_ROOT}/setup/extraction-guide.md` for guidance." Stop here.
> 5. List files in `~/.claude/data/prose-craft/registers/` excluding `register-template.md`. If empty, tell the user the same setup message as step 4 and stop.

The "only copy files that don't already exist" rule means subsequent plugin updates can add new template files without overwriting user data. The first-run check (`~/.claude/data/prose-craft/` exists) is a fast path so the init logic only fires once per machine.

The same template-copy pattern applies inside `skills/prose-craft-learn/SKILL.md` for any new learning-side files added in future template updates — though for now `accumulator.md` is the only one.

### 4.4 Tuning to upstream

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
        advocacy.md
        dystopian-fiction.md
        personal.md
        extraction-artifacts/
      learning/
        accumulator.md
        ablation-log.md
        bootstrap-run.md
        splits.md
        judge-agreement.md               # if present
        snapshots/
  local-plugins/
    prose-craft/                         # REMOVED entirely
    seo-toolkit/                         # unchanged
```

The contents of `claude/local-plugins/prose-craft/2.0.0/{registers,learning}/` move to `claude/data/prose-craft/{registers,learning}/`. The rest of `claude/local-plugins/prose-craft/` (plugin code, `.claude-plugin/`, `skills/`, `agents/`, `scripts/`, `setup/`) is deleted — the marketplace install owns that content now.

### 5.2 Script changes

**`scripts/install-mac.sh`:** keep the existing `Copying local plugins` loop (still needed for `seo-toolkit` and any future local plugins) but it will naturally no-op for prose-craft once `claude/local-plugins/prose-craft/` is gone. Add a new step before or after:

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

**`scripts/snapshot-from-windows.sh`:** the existing snapshot block at lines 70-77 reads `~/.claude/plugins/cache/local/*/` into `claude/local-plugins/`. Keep that block for non-prose-craft local plugins. Add a parallel block:

```bash
mkdir -p "$CLAUDE_DST/data"
for data_dir in "$CLAUDE_SRC/data"/*/; do
  [[ -d "$data_dir" ]] || continue
  plugin_name="$(basename "$data_dir")"
  mkdir -p "$CLAUDE_DST/data/$plugin_name"
  cp -r "$data_dir." "$CLAUDE_DST/data/$plugin_name/"
done
```

Both blocks become no-ops if their source path is empty, so they coexist without interfering.

## 6. Migration sequence

The order is chosen to keep a usable plugin installed at every step. Personal data is copied (not moved) until the new location is verified working.

**Step 1 — Update the prose-craft repo (one branch, one PR).**
- Path rewrites (§4.1), directory restructure (§4.2), first-run init (§4.3), prose-review.md tuning + plugin.json author field (§4.4).
- Verify with a clean test install (e.g., temporary fresh `~/.claude/` or a different machine): marketplace install creates the install path with `template-data/` present, no `registers/` or `learning/` at the install root, and first-run init successfully creates `~/.claude/data/prose-craft/`.
- Merge to main. Bump plugin version (suggest 2.1.0).

**Step 2 — Migrate personal data on each machine.**
On Mac:
```
cp -R ~/.claude/plugins/cache/local/prose-craft/2.0.0/registers ~/.claude/data/prose-craft/
cp -R ~/.claude/plugins/cache/local/prose-craft/2.0.0/learning  ~/.claude/data/prose-craft/
```
On Windows: the equivalent paths under the user's home directory.

Verify both directories are populated and the file count matches the source.

**Step 3 — Switch from local install to marketplace install.**
On each machine:
- `settings.json`: set `prose-craft@local: false` (or delete the key), set `prose-craft@prose-craft: true`.
- `installed_plugins.json`: delete the `prose-craft@local` entry, restore the `prose-craft@prose-craft` entry (Claude Code will recreate it on next launch if the marketplace entry is also intact).
- `known_marketplaces.json`: ensure the `prose-craft` marketplace is registered (re-add the entry pointing at `https://github.com/TimSimpsonJr/prose-craft.git` if missing).
- Restart Claude Code; verify `/prose-craft` and `/prose-craft-learn` resolve.
- Delete `~/.claude/plugins/cache/local/prose-craft/` (and its backup, if still present).

**Step 4 — Restructure the dotfiles-claude repo.**
- Branch off main: move `claude/local-plugins/prose-craft/2.0.0/{registers,learning}/` → `claude/data/prose-craft/{registers,learning}/`. Delete the rest of `claude/local-plugins/prose-craft/`.
- Update `scripts/install-mac.sh` and `scripts/snapshot-from-windows.sh` per §5.2.
- Re-run `snapshot-from-windows.sh` on Windows; verify it produces no spurious changes (data should already match what was migrated in step 2).
- Commit and push.

**Step 5 — Update the dotfiles-claude README** to reflect the new structure (the "What's in here" section currently lists prose-craft under "two local plugins"; update it to "one local plugin (seo-toolkit), and per-plugin user data under `claude/data/`").

## 7. Risks and mitigations

**Personal data loss during migration.** Each migration step copies; nothing is deleted until the new location is verified. Old `cache/local/prose-craft/` survives step 2 and only gets removed in step 3 after marketplace install is confirmed working. Both machines' personal data exists in dotfiles as a third copy at all times.

**Marketplace install on a never-before-set-up machine.** First-run init (§4.3) creates the directory tree and points the user at the setup guide. The plugin gracefully refuses to generate until at least one register exists.

**Future plugin updates introducing new files under `registers/` or `learning/`.** Those new files are added to `template-data/`, not to user data. First-run init only copies templates if the target doesn't exist — so a plugin update that adds a new template file will reach the user, but never overwrites their existing files.

**`~` not resolving in some context.** Audited: every path reference is in markdown (read by Claude, which expands `~`) or shell scripts (which expand `~` natively). No literal-string path concatenation in `discipline_check.py` for user data.

**Snapshot script writing to the wrong place after Windows pulls the new repo.** The two snapshot blocks (local-plugins and data) operate on different source paths, so they don't collide. The first re-run on Windows is the moment to verify — if it produces an unexpected diff, halt and inspect before committing.

## 8. Out of scope (future work)

- Extraction and learning process rework — planned for a separate session.
- Whether craft-review.md should ship a "personal style examples" extension point (so the Doctorow/Housel-style references could live in a register-like personal layer rather than the agent body). Deferred to the extraction/learning rework.
- Applying the `~/.claude/data/<plugin>/` pattern to other plugins (e.g., seo-toolkit). The pattern is reusable, but only prose-craft is migrating in this design.
- A `/prose-craft-init` standalone command (currently the init lives inline in the prose-craft skill). If the inline approach gets noisy, an explicit init command can be added later without breaking anything.
