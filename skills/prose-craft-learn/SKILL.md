---
name: prose-craft-learn
description: Analyze manual edits to prose-craft output and propose improvements to registers, skill rules, and review agents. Invoke after manually editing a piece generated with prose-craft. Also invoked by prose-craft during the review gate to save snapshots.
---

# Prose Craft Learn

This skill manages the learning loop for prose-craft. It captures snapshots of generated text at key pipeline stages, then (when invoked directly) dispatches the learn-review agent to analyze what the user changed by hand and propose improvements to the system.

This skill is independently invocable. It does not require prose-craft to be active in the current session. It reads all files from disk.

## Argument Detection

Check the invocation arguments to determine which mode to run.

- `snapshot post-review`, `snapshot post-fixes`, or `snapshot suppression` --> Mode 1: Snapshot Save
- A file path argument (e.g., `/prose-craft-learn path/to/edited-file.md`) --> Mode 2: Learning Analysis, using that file
- No arguments (just `/prose-craft-learn`) --> Mode 2: Learning Analysis, using the most recent snapshot set

## Mode 1: Snapshot Save

Invoked by the prose-craft skill during the review gate workflow. Does not interact with the user.

### `snapshot post-review`

1. Create the directory `${CLAUDE_PLUGIN_ROOT}/learning/snapshots/` if it doesn't exist.

2. Derive a piece filename from the output file being written. Strip the extension and any path components. For example, `/home/user/blog/my-post.md` becomes `my-post`.

3. Generate a timestamp: `YYYY-MM-DD-HHmm` (24-hour, local time).

4. Write the CURRENT generated text (the text after review agents ran and hard fails were fixed, before the user sees advisories) to:
   `${CLAUDE_PLUGIN_ROOT}/learning/snapshots/{piece-filename}-{timestamp}-post-review.md`

5. Write the **generation brief** to:
   `${CLAUDE_PLUGIN_ROOT}/learning/snapshots/{piece-filename}-{timestamp}-brief.md`

   The brief is everything that drove generation: the user's request, the source material (transcripts, research notes, outline), and any design-doc/brief used. This is what lets a piece be **regenerated** later for the held-out gate, so capture it verbatim rather than summarizing. If generation used a design doc on disk, record its path here too.

6. Write the review agent findings (both the prose review findings and the craft review advisory table) to:
   `${CLAUDE_PLUGIN_ROOT}/learning/snapshots/{piece-filename}-{timestamp}-review-findings.md`

7. Update or create `${CLAUDE_PLUGIN_ROOT}/learning/snapshots/manifest.json`. If the file exists, read it first and append to the `snapshots` array. If it doesn't exist, create it with a new array.

   Entry format:
   ```json
   {
     "piece": "my-post",
     "timestamp": "2026-04-10-1430",
     "register": "personal",
     "brief": "my-post-2026-04-10-1430-brief.md",
     "postReview": "my-post-2026-04-10-1430-post-review.md",
     "reviewFindings": "my-post-2026-04-10-1430-review-findings.md"
   }
   ```

   The `register` field comes from whichever register was active during generation.

### `snapshot post-fixes`

1. Write the current text (after the user accepted/rejected/modified all advisory rows) to:
   `${CLAUDE_PLUGIN_ROOT}/learning/snapshots/{piece-filename}-{timestamp}-post-fixes.md`

   Use the same piece filename and timestamp as the matching `post-review` entry. Find the match by looking for the most recent manifest entry whose `piece` field matches the current output file.

2. Update the matching manifest entry to add the `postFixes` field:
   ```json
   {
     "piece": "my-post",
     "timestamp": "2026-04-10-1430",
     "register": "personal",
     "brief": "my-post-2026-04-10-1430-brief.md",
     "postReview": "my-post-2026-04-10-1430-post-review.md",
     "reviewFindings": "my-post-2026-04-10-1430-review-findings.md",
     "postFixes": "my-post-2026-04-10-1430-post-fixes.md"
   }
   ```

### `snapshot suppression`

Records the orchestrator's **decision ledger**: every finding both review agents produced, and what the orchestrator did with each. This is the Gap-F instrumentation: it makes visible whether a dropped suggestion was the reviewer proposing badly or the orchestrator filtering badly (opposite fixes). Invoked by the prose-craft skill after it decides what to surface.

1. Write a suppression log to:
   `${CLAUDE_PLUGIN_ROOT}/learning/snapshots/{piece-filename}-{timestamp}-suppression.md`

   Use the same piece filename and timestamp as the matching `post-review` entry.

   Record one row per finding from BOTH agents:

   | Source agent | Finding | Disposition |
   |---|---|---|
   | prose-review | [the advisory] | surfaced-advisory / silently-fixed (hard fail) / suppressed |
   | craft-review | [the opportunity] | surfaced-advisory / suppressed |

   `suppressed` = the orchestrator neither surfaced it to the user nor silently fixed it (the dark-filter case). Be honest: log what was dropped, not only what was acted on.

2. Update the matching manifest entry to add a `suppressionLog` field with the filename.

## Mode 2: Learning Analysis

Invoked directly by the user after they have finished manually editing a piece that was generated with prose-craft.

### Step 1: Load the minibatch

Read `${CLAUDE_PLUGIN_ROOT}/learning/snapshots/manifest.json`.

**If a file path was provided** as an argument, the target is that single piece: match by piece name (derived from the path as in Mode 1; most recent by timestamp if several match).

**If no file path was provided**, load the **last N unprocessed entries** (default **N=3**) from the manifest: the minibatch. Every entry still in the manifest is unprocessed (cleanup removes processed ones in the last step). If fewer than N entries exist, use what's there.

For **each** piece in the minibatch, read its files:
- **post-review snapshot**: the `postReview` file
- **post-fixes snapshot**: the `postFixes` file
- **brief**: the `brief` file, if present (older snapshots may lack it)
- **live edited file**: if the user provided a path, read that file; otherwise determine the original output path from conversation context. If a batched piece has no locatable live file, fall back to its post-fixes snapshot.

If a piece's `postFixes` is missing, use its post-review snapshot as the post-fixes (the diff between post-review and the live file still captures everything).

### Step 2: Load review findings and suppression logs

For each piece, read its `reviewFindings` file, and its `suppressionLog` file if present (the decision ledger from the live gate).

### Step 3: Load accumulator

Read `${CLAUDE_PLUGIN_ROOT}/learning/accumulator.md`. If it doesn't exist, proceed with an empty accumulator and tell the agent to use higher evidence thresholds (less prior evidence to cross-reference). The accumulator's **Longitudinal Guidance** section is PROTECTED context: pass it to the agent as read-only. The agent must not propose edits to it.

### Step 4: Determine register(s)

Read the `register` field from each minibatch entry. A minibatch is normally single-register; if pieces span registers, note each piece's register so the agent can tag register-specificity correctly.

### Step 5: Load current rules and held-out splits

Read these from `${CLAUDE_PLUGIN_ROOT}/`:
- The register file(s) for the batch: `registers/{register}.md` (includes the register's `## Demonstrated Edits` exemplars)
- The skill file: `skills/prose-craft/SKILL.md`
- The prose review agent: `agents/prose-review.md`
- The craft review agent: `agents/craft-review.md`
- The held-out splits: `learning/splits.md` if it exists (defines the train / selection / test sets the gate uses). If absent, the gate falls back to retrospective checks on available snapshots.

### Step 6: Dispatch the learning agent (the optimizer)

Use the Agent tool:
- `subagent_type`: "prose-craft:learn-review"
- `model`: opus
- `description`: "Analyze edits and propose improvements"
- `prompt`: Include the per-piece inputs for **all N pieces** (clearly labeled by piece) plus the shared context once:

  ```
  ## BATCH: N pieces

  ### Piece 1: {piece name} (register: {register})
  #### Post-Review Snapshot
  [full text]
  #### Post-Fixes Snapshot
  [full text]
  #### Post-Manual-Edit (Live File)
  [full text]
  #### Compacted Review Findings
  [full text of review-findings file]

  ### Piece 2: {piece name} (register: {register})
  [...same four sub-sections...]

  (repeat for each piece in the batch)

  ## Shared context

  ### Current Register: {register name}
  [full text of the register file, including its Demonstrated Edits]

  ### Current SKILL.md
  [full text]

  ### Current Prose Review Agent
  [full text]

  ### Accumulator
  [full text, or "EMPTY -- no prior observations. Use higher evidence thresholds." The Longitudinal Guidance section is PROTECTED: do not propose edits to it.]
  ```

Wait for the agent to return its tiered findings (Apply / Hold / Reinforce / Contradictions), with Apply capped at `L_t` candidate edits.

### Step 7: Present candidates and classify them

Show the agent's full analysis. "Hold" and "Reinforce" observations are shown for information only. "Contradiction" flags are shown for the user to resolve (optional, can be deferred).

For each **Apply** candidate edit, present the pattern name, target file, evidence table, and exact proposed edit (old/new text), and classify it:
- **Discipline edit** — targets an objective banned pattern: em-dashes, colon-for-inline-elaboration, the banned-phrase / ChatGPT-ism list, caps-on-phrases, or the fatal-pattern. Gated by the discipline script (and the fatal-pattern re-checker), no human input.
- **Taste edit** — changes voice, craft, structure, or word choice in a way no script can score. Gated by the human pairwise step.

An edit can be both; if so it must pass both fractions.

### Step 8: Gate each candidate edit

The gate decides what lands. An edit is applied only if it **strictly passes** its fraction(s). **Freeze the reviewers and the discipline script for the duration of the gate** so scores stay comparable (improve evaluators separately; see the evaluators mode).

**Discipline fraction (objective, automatic).** For a discipline edit, take a before/after sample (a held-out selection piece regenerated under old-vs-new skill-state, or the candidate's own before/after text), write each to a temp file, and run:

```
python scripts/discipline_check.py --diff <before-file> <after-file>
```

Accept only if `introduced_new` is `false` (no new violation) and the targeted violation count dropped. The discipline gate is a **regression guardrail, not a fitness function**: never use it to minimize violations as an optimization target. That trains toward clean-but-lifeless prose.

**Taste fraction (structured-subjective).** For a taste edit, run the **pairwise step (Step 9)**. Accept only if the human picks the edited (new-skill-state) version.

Record, per candidate: accepted or rejected, which fraction(s) ran, and the score delta (discipline) or pairwise pick (taste). Rejected candidates feed the Rejected Edits buffer (Step 11).

### Step 9: The pairwise step (human taste gate + shadow judge)

For each taste edit being gated:

1. Pick a held-out **selection-set** piece (`D_sel` from `splits.md`) in the edit's register that exercises the pattern, and use its captured brief.
2. Regenerate that brief twice: once under the **current** skill-state (A) and once under the **edited** skill-state (B). Generate **several samples each** (2-3) and treat them as a set, to average out generation noise. (The regeneration mechanics are the generative-gate harness, documented below.)
3. Present the user an **A/B comparison** (blind if practical) and ask: *which is more you* — more in-register? Capture the human pick. **The human is the only gatekeeper.**
4. **Shadow judge:** dispatch the `taste-judge` agent on the same A/B (brief + both versions). Log the judge's pick **alongside** the human pick to `${CLAUDE_PLUGIN_ROOT}/learning/judge-agreement.md`. The judge **gates nothing** — it only accumulates a calibration corpus.
5. The edit passes the taste fraction iff the **human** picked the edited version (B).

### Step 10: Apply accepted edits and retain exemplars

For each edit the gate **accepted**, apply the text edit to the target file in BOTH locations:
- **Installed plugin copy:** `~/.claude/plugins/cache/local/prose-craft/2.0.0/{target-path}`
- **Source repo copy:** `prose-craft/{target-path}` (relative to the current working directory)

If the source repo copy doesn't exist at the expected path, skip it silently (the user may not be working from the source repo).

**Retain the winning exemplar.** For each accepted edit, append its **winning before/after pair** (the pipeline output vs. the user's edit that motivated it) to the target register's `## Demonstrated Edits` section, verbatim, no commentary. This is now a *validated* demonstration fed back into generation. FIFO-cap the section at 8-12 pairs: if adding one exceeds the cap, drop the oldest. (Skill/agent edits have no register section; their winning pairs are not retained here.)

Do not apply rejected edits. They go to the Rejected Edits buffer in Step 11.

### Step 11: Update accumulator

After all candidates have been gated, update `${CLAUDE_PLUGIN_ROOT}/learning/accumulator.md`.

The accumulator is the **optimizer-side slow record**, not a graduation gate. Its observations are *evidence the learn-review agent uses to propose candidate edits* (see `agents/learn-review.md`); that agent's minibatch reflection decides reusable-vs-anecdotal directly. An observation is **never promoted to a rule change by recurrence count**. Promotion happens only when a proposed edit passes the held-out gate (the gate step in Mode 2 below).

The accumulator file format:

```markdown
# Accumulator

staleness_threshold: 5

## Longitudinal Guidance (PROTECTED — step-level edits MUST NOT modify this)
- craft-review is intentionally high-recall; rejection is expected; do NOT tune its triggers down.
- Discipline wins on banned patterns: never restore em-dashes / fatal-pattern from a source corpus even if an influence uses them.
- User regularization labels (do-not-generalize): <list>

## Observations

### {Pattern Name}
- **Target:** {target file}
- **Category:** {category from learn-review agent}
- **Sessions seen:** {count}
- **Sessions since last seen:** {count}
- **Status:** hold | rejected
- **Instances:**

| # | Before | After | Context | Session |
|---|---|---|---|---|
| 1 | [quote] | [quote] | [context] | {date} |

## Rejected Edits (negative feedback for the optimizer)

| Edit | Target | Held-out score delta | Round |
|---|---|---|---|
| [proposed edit] | [target file] | [score drop] | [round/date] |

---
```

Update rules:

1. **New observations** from this session: add them with `Sessions seen: 1`, `Sessions since last seen: 0`, and `Status: hold`. These are candidate evidence for the optimizer, not pending-promotion-by-count.

2. **Existing observations matched this session** (the agent merged new instances into an existing pattern): increment `Sessions seen`, reset `Sessions since last seen` to 0, and append the new instance rows. Recurrence enriches the evidence the optimizer sees; it does not by itself trigger a rule change.

3. **Existing observations NOT seen this session**: increment `Sessions since last seen` by 1.

4. **Observations whose proposed edit the gate accepted**: the observation has graduated into a committed rule change. Remove it from the Observations list. Its winning before/after pair was already retained as an exemplar in the register's `## Demonstrated Edits` (Step 10); do not also keep it as an observation.

5. **Observations whose proposed edit the user rejected or the gate failed**: set `Status: rejected` and append a row to the **Rejected Edits** table (target + held-out score delta + round). Rejected edits are never re-proposed in the same form (the agent checks this status). The observation stays as negative-feedback context.

6. **Staleness expiry**: remove any observation where `Sessions since last seen` exceeds the `staleness_threshold` value (default: 5). This is hygiene for piece-specific noise that never recurred, not a graduation signal.

7. **PROTECTED — Longitudinal Guidance**: never modify this section during a routine learning run. It is updated only by the slow-update (epoch) step or by explicit user instruction. Step-level edits MUST NOT touch it.

### Step 12: Cleanup

Do this for **each piece processed in this batch**:

1. **Compact review findings**: rewrite the review-findings file to contain only a summary of accept/reject/modify decisions (not the full advisory tables). This preserves the signal while reducing disk usage.

2. **Delete snapshot files** for the piece: remove the post-review, post-fixes, review-findings, brief, and suppression files from the snapshots directory. (If a piece is being promoted into a held-out split, copy its brief into the split record first — `splits.md` must point at a durable brief path, not a soon-deleted snapshot.)

3. **Remove the entry** from manifest.json.

4. **Delete orphaned files**: scan the snapshots directory for any files not referenced by any remaining manifest entry. Delete them.

5. If the manifest's `snapshots` array is now empty, delete manifest.json itself.

## Notes

- Snapshots are per-session. If writing spans multiple sessions, only the most recent session's snapshots are available. Earlier sessions' snapshots may have been cleaned up or may reference stale text. The learning analysis works from whatever snapshots exist at invocation time.

- The accumulator is the optimizer's long-term memory. It persists across sessions and pieces and supplies the **evidence** the learn-review agent reflects over. It does not itself graduate patterns; promotion happens at the gate. Its PROTECTED Longitudinal Guidance section is the durable home for scarce human judgments and must not be rewritten by routine runs.

- When the accumulator is empty or doesn't exist, the learning agent works with evidence from the current piece only. The agent uses judgment on thresholds in that case (a single dramatic rewrite can still warrant an "apply" recommendation).

- The `staleness_threshold` in the accumulator header is user-configurable. Lower values mean patterns expire faster (more aggressive pruning). Higher values give patterns more sessions to recur before being discarded.
