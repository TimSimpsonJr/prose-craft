---
name: learn
description: Analyze manual edits to copydesk output and propose improvements to registers, skill rules, and review agents. Invoke after manually editing a piece generated with copydesk. Also invoked by copydesk during the review gate to save snapshots.
---

# Copydesk Learn

This skill manages the learning loop for copydesk. It captures snapshots of generated text at key pipeline stages, then (when invoked directly) dispatches the learn-review agent to analyze what the user changed by hand and propose improvements to the system.

This skill is independently invocable. It does not require copydesk to be active in the current session. It reads all files from disk.

## Argument Detection

Check the invocation arguments to determine which mode to run.

- `snapshot post-review`, `snapshot post-fixes`, or `snapshot suppression` --> Mode 1: Snapshot Save
- `evaluators` --> Mode 3: Evaluator Correction
- A file path argument (e.g., `/copydesk:learn path/to/edited-file.md`) --> Mode 2: Learning Analysis, using that file
- No arguments (just `/copydesk:learn`) --> Mode 2: Learning Analysis, using the most recent snapshot set

## Mode 1: Snapshot Save

Invoked by the copydesk skill during the review gate workflow. Does not interact with the user.

### `snapshot post-review`

1. Create the directory `~/.claude/data/copydesk/learning/snapshots/` if it doesn't exist.

2. Derive a piece filename from the output file being written. Strip the extension and any path components. For example, `/home/user/blog/my-post.md` becomes `my-post`.

3. Generate a timestamp: `YYYY-MM-DD-HHmm` (24-hour, local time).

4. Write the CURRENT generated text (the text after review agents ran and hard fails were fixed, before the user sees advisories) to:
   `~/.claude/data/copydesk/learning/snapshots/{piece-filename}-{timestamp}-post-review.md`

5. Write the **generation brief** to:
   `~/.claude/data/copydesk/learning/snapshots/{piece-filename}-{timestamp}-brief.md`

   The brief is everything that drove generation: the user's request, the source material (transcripts, research notes, outline), and any design-doc/brief used. This is what lets a piece be **regenerated** later for the held-out gate, so capture it verbatim rather than summarizing. If generation used a design doc on disk, record its path here too.

6. Write the review agent findings (both the prose review findings and the craft review advisory table) to:
   `~/.claude/data/copydesk/learning/snapshots/{piece-filename}-{timestamp}-review-findings.md`

7. Update or create `~/.claude/data/copydesk/learning/snapshots/manifest.json`. If the file exists, read it first and append to the `snapshots` array. If it doesn't exist, create it with a new array.

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
   `~/.claude/data/copydesk/learning/snapshots/{piece-filename}-{timestamp}-post-fixes.md`

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

Records the orchestrator's **decision ledger**: every finding both review agents produced, and what the orchestrator did with each. This is the Gap-F instrumentation: it makes visible whether a dropped suggestion was the reviewer proposing badly or the orchestrator filtering badly (opposite fixes). Invoked by the copydesk skill after it decides what to surface.

1. Write a suppression log to:
   `~/.claude/data/copydesk/learning/snapshots/{piece-filename}-{timestamp}-suppression.md`

   Use the same piece filename and timestamp as the matching `post-review` entry.

   Record one row per finding from BOTH agents:

   | Source agent | Finding | Disposition |
   |---|---|---|
   | prose-review | [the advisory] | surfaced-advisory / silently-fixed (hard fail) / suppressed |
   | craft-review | [the opportunity] | surfaced-advisory / suppressed |

   `suppressed` = the orchestrator neither surfaced it to the user nor silently fixed it (the dark-filter case). Be honest: log what was dropped, not only what was acted on.

2. Update the matching manifest entry to add a `suppressionLog` field with the filename.

## Mode 2: Learning Analysis

Invoked directly by the user after they have finished manually editing a piece that was generated with copydesk.

### Step 1: Load the minibatch

Read `~/.claude/data/copydesk/learning/snapshots/manifest.json`.

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

Read `~/.claude/data/copydesk/learning/accumulator.md`. If it doesn't exist, proceed with an empty accumulator and tell the agent to use higher evidence thresholds (less prior evidence to cross-reference). The accumulator's **Longitudinal Guidance** section is PROTECTED context: pass it to the agent as read-only. The agent must not propose edits to it.

### Step 4: Determine register(s)

Read the `register` field from each minibatch entry. A minibatch is normally single-register; if pieces span registers, note each piece's register so the agent can tag register-specificity correctly.

### Step 5: Load current rules and held-out splits

Read these:
- The register file(s) for the batch: `~/.claude/data/copydesk/registers/{register}.md` (includes the register's `## Demonstrated Edits` exemplars)
- The skill file: `${CLAUDE_PLUGIN_ROOT}/skills/write/SKILL.md`
- The prose review agent: `${CLAUDE_PLUGIN_ROOT}/agents/prose-review.md`
- The craft review agent: `${CLAUDE_PLUGIN_ROOT}/agents/craft-review.md`
- The held-out splits: `~/.claude/data/copydesk/learning/splits.md` if it exists (defines the train / selection / test sets the gate uses). If absent, the gate falls back to retrospective checks on available snapshots.

### Step 6: Dispatch the learning agent (the optimizer)

Use the Agent tool:
- `subagent_type`: "copydesk:learn-review"
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
4. **Shadow judge:** dispatch the `taste-judge` agent (model: sonnet) on the same comparison — pass the brief, the register's voice feature description, and both versions (A = current, B = edited). Append a row to `~/.claude/data/copydesk/learning/judge-agreement.md` recording: date, register, edit name, the **human** pick, the **judge** pick, the judge's confidence, and whether they **agree** (columns: `| Date | Register | Edit | Human | Judge | Confidence | Agree? |`). The judge **gates nothing** — it only accumulates the calibration corpus that would later justify promoting it to a gatekeeper.
5. The edit passes the taste fraction iff the **human** picked the edited version (B).

### Step 10: Apply accepted edits and retain exemplars

For each edit the gate **accepted**, route the write by target type:

| Target type | Write to |
|---|---|
| Register file (`registers/<name>.md`) | `~/.claude/data/copydesk/registers/<name>.md` |
| `accumulator.md` | `~/.claude/data/copydesk/learning/accumulator.md` |
| Other learning artifacts (`splits.md`, `ablation-log.md`, `judge-agreement.md`, etc.) | `~/.claude/data/copydesk/learning/<filename>` |
| Plugin-code file (agent body, skill body, scripts) | **Do not write to the install path.** Append a proposal to `~/.claude/data/copydesk/learning/pending-upstream.md` for review and upstream PR. |

The marketplace install path is owned by plugin updates — any local write there gets clobbered on next update. The `pending-upstream.md` queue keeps plugin-code edits visible without silently mutating disposable state.

**`pending-upstream.md` append format** (newest-first). The example below uses 4-backtick outer fences so the inner 3-backtick `diff` fence renders correctly:

````markdown
## <ISO-8601 timestamp> · <target-path-relative-to-plugin-root>

- **Source candidate:** `<learn-review proposal id or short label>`
- **Rationale:** <one-paragraph summary of the gate evidence supporting this edit>

```diff
<unified diff of the proposed change>
```
````

The richer UX (e.g., a `/copydesk-pending` skill that surfaces queued edits) is out of scope; lands in the planned extraction/learning rework.

**Retain the winning exemplar.** For each accepted edit, append its **winning before/after pair** (the pipeline output vs. the user's edit that motivated it) to the target register's `## Demonstrated Edits` section, verbatim, no commentary. This is now a *validated* demonstration fed back into generation. FIFO-cap the section at 8-12 pairs: if adding one exceeds the cap, drop the oldest. (Skill/agent edits have no register section; their winning pairs are not retained here.)

Do not apply rejected edits. They go to the Rejected Edits buffer in Step 11.

### Step 11: Update accumulator

After all candidates have been gated, update `~/.claude/data/copydesk/learning/accumulator.md`.

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

## The generative-gate harness

The generative gate regenerates a held-out brief under two skill-states and compares the results. It is **in-session orchestration**, not a script: the loop dispatches generation sub-agents (the same Agent pattern the review gate uses) and aggregates their output.

**Inputs:** a **stripped brief** (see `setup/brief-stripping-guide.md` — strip the skill-encoding so the edit's effect is visible and an old embedded voice rule can't contradict the edited register), and the two skill-states to compare (current vs. edited).

**Procedure (per candidate taste edit):**

1. Pick a held-out **selection** piece (`D_sel`) in the edit's register and load its stripped brief.
2. **Regenerate under skill-state A (current).** Dispatch a generation sub-agent with the stripped brief + the current register/rules. Repeat **k times** (k = 2-3) to get a sample set; this averages out generation noise.
3. **Regenerate under skill-state B (edited).** Same brief, same k, but with the candidate edit applied to the register/rules.
4. **Compare.** Run the pairwise step (Mode 2 Step 9): present the A-set vs. the B-set to the human, capture the pick, and log the shadow taste-judge alongside. For a stable read, compare the sets (or representative samples), not a single lucky draw.
5. The edit passes the taste fraction iff the human prefers the **B** (edited) set.

**Two gate flavors** (per the bootstrap):

- **Generative gate** (above): needs a captured brief; tests whether the edit improves fresh generation.
- **Retrospective gate** (no brief needed): does the candidate edit catch a held-out piece's *actual* hand-corrections without over-flagging text the user kept? Use this for discipline edits and when a brief isn't available. Strong for discipline, judge-assisted for taste.

**Cost note:** k regenerations × 2 skill-states × one judge call per comparison. Keep k small; the point is noise reduction, not exhaustive sampling.

## Mode 3: Evaluator Correction

Invoked with `/copydesk:learn evaluators`. This is a **separate loop** from generator training, with its own ground truth and cadence. It corrects the review agents (prose-review, craft-review); it never runs while a generator run is in flight.

**Why separate.** The reviewers participate in every rollout (the scored piece is post-review). If you improve a reviewer mid-generator-run, you have moved the evaluator and broken score comparability. So: **freeze prose-review and craft-review during generator runs.** Improve them here, then **re-baseline** the held-out scores before the next generator round.

### Ground truth

Your advisory **accept / reject / modify** decisions, read from the suppression logs and the (compacted) review-findings across recent pieces. An accepted advisory = the check was right. A rejected advisory = interpret by agent and error class (below). A modified advisory = the agent found a real issue but proposed the wrong fix.

### Metrics, by agent and error class

Do **not** score both agents the same way (the three error classes):

- **prose-review = high precision.** It should fire rarely and be right. Metric: **precision** (of its advisories, what fraction did you accept?). A pattern of consistent rejection of an advisory type signals **over-firing**: propose a tightened trigger for that check.
- **craft-review = high recall.** It is *meant* to surface non-obvious opportunities; most get rejected and that is the design working. Metric: **recall-at-1** (did at least one of its opportunities per piece land?). **Never tune its triggers down on rejection rate** (the PROTECTED Longitudinal Guidance enforces this).
- **Reviewer self-violation** (either agent): the agent's *own suggested text* contains a banned pattern. Metric: **self-violation rate** (violations per long piece). Objective defect: propose a fix to the agent's suggestion-generation guidance.
- **Factual hallucination** (either agent): the agent invented a fact (a plaintiff, a place, a number). Always a defect, independent of precision or recall.

### Procedure

1. Gather the accept/reject/modify ledger across recent pieces (suppression logs + review-findings).
2. Compute the metrics above per agent.
3. Propose evaluator edits **only** where the metric (not the raw rejection rate) justifies it: tighten prose-review triggers that over-fire; fix self-violations; flag hallucinations. Leave craft-review's recall-driven boldness alone.
4. Approved evaluator edits route per the same table in Mode 2 Step 10. `agents/prose-review.md` and `agents/craft-review.md` are plugin-code files — append the proposed edit to `~/.claude/data/copydesk/learning/pending-upstream.md` for upstream PR. Do not write to the marketplace install path.
5. **Re-baseline.** Because the evaluators just changed, previously recorded held-out scores are stale. Note in the bootstrap/run log that held-out scores must be re-measured before the next generator round.

## The ablation operation

Rules accrete; some stop earning their place. Ablation is the metabolism that removes dead weight, using the same gate as everything else.

**Operation (per rule):**

1. **Drop the rule** from its file (register, SKILL.md, or a review agent), temporarily.
2. **Regenerate the selection set** (`D_sel`) under the dropped-rule skill-state, k samples per brief (the generative-gate harness).
3. **Score against the gate.** Compare dropped-rule output to with-rule output by the pairwise step (for discipline rules, also run the discipline script).
4. **Decide.** If the gate score does **not** fall when the rule is gone, the rule wasn't earning its place: **keep the drop** (remove the rule). If the score falls, the rule is load-bearing: **restore it**.
5. **Log** the keep/remove decision and the score delta per rule to `~/.claude/data/copydesk/learning/ablation-log.md`.

This is the inverse of the edit gate: an edit is kept only if it *improves* the held-out score; a rule is dropped only if its removal *doesn't hurt* it. Both protect the held-out score from drift.

**Cadence (interim default):** sweep before each release, or when a file's rule count crosses a threshold (e.g. a review-agent section passing ~10 rules). A fixed recurring cadence is deferred until observed rule-growth justifies one.

**Initial sweep targets** (run at bootstrap), the most recently graduated rules, to test whether they earn their place:
- prose-review **#25 Performed Specificity** and **#26 Hollow Anadiplosis** (reference target is `agents/prose-review.md` in the marketplace install at `~/.claude/plugins/cache/copydesk/copydesk/<ver>/agents/prose-review.md` — read-only. Any rule drop that survives the gate is a plugin-code edit and routes to `~/.claude/data/copydesk/learning/pending-upstream.md` for upstream PR per Mode 2 Step 10.)
- the SKILL.md **colon-for-inline-elaboration** rule (also enforced by the discipline script).

Record each as a keep/remove decision + score delta in `~/.claude/data/copydesk/learning/ablation-log.md`.

## Notes

- Snapshots are per-session. If writing spans multiple sessions, only the most recent session's snapshots are available. Earlier sessions' snapshots may have been cleaned up or may reference stale text. The learning analysis works from whatever snapshots exist at invocation time.

- The accumulator is the optimizer's long-term memory. It persists across sessions and pieces and supplies the **evidence** the learn-review agent reflects over. It does not itself graduate patterns; promotion happens at the gate. Its PROTECTED Longitudinal Guidance section is the durable home for scarce human judgments and must not be rewritten by routine runs.

- When the accumulator is empty or doesn't exist, the learning agent works with evidence from the current batch only. A pattern still needs to appear in ≥2 pieces to be proposed; a single piece (even with no prior accumulator evidence) yields only Hold observations, which wait for a second piece to corroborate. This is the intended SkillOpt-aligned discipline, not a limitation.

- The `staleness_threshold` in the accumulator header is user-configurable. Lower values mean patterns expire faster (more aggressive pruning). Higher values give patterns more sessions to recur before being discarded.
