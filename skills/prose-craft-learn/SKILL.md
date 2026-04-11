---
name: prose-craft-learn
description: Analyze manual edits to prose-craft output and propose improvements to registers, skill rules, and review agents. Invoke after manually editing a piece generated with prose-craft. Also invoked by prose-craft during the review gate to save snapshots.
---

# Prose Craft Learn

This skill manages the learning loop for prose-craft. It captures snapshots of generated text at key pipeline stages, then (when invoked directly) dispatches the learn-review agent to analyze what the user changed by hand and propose improvements to the system.

This skill is independently invocable. It does not require prose-craft to be active in the current session. It reads all files from disk.

## Argument Detection

Check the invocation arguments to determine which mode to run.

- `snapshot post-review` or `snapshot post-fixes` --> Mode 1: Snapshot Save
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

5. Write the review agent findings (both the prose review findings and the craft review advisory table) to:
   `${CLAUDE_PLUGIN_ROOT}/learning/snapshots/{piece-filename}-{timestamp}-review-findings.md`

6. Update or create `${CLAUDE_PLUGIN_ROOT}/learning/snapshots/manifest.json`. If the file exists, read it first and append to the `snapshots` array. If it doesn't exist, create it with a new array.

   Entry format:
   ```json
   {
     "piece": "my-post",
     "timestamp": "2026-04-10-1430",
     "register": "personal",
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
     "postReview": "my-post-2026-04-10-1430-post-review.md",
     "reviewFindings": "my-post-2026-04-10-1430-review-findings.md",
     "postFixes": "my-post-2026-04-10-1430-post-fixes.md"
   }
   ```

## Mode 2: Learning Analysis

Invoked directly by the user after they have finished manually editing a piece that was generated with prose-craft.

### Step 1: Load snapshots

Read `${CLAUDE_PLUGIN_ROOT}/learning/snapshots/manifest.json`.

If a file path was provided as an argument, match by piece name (derive the piece name from the file path the same way as in Mode 1). If multiple entries match, use the most recent by timestamp.

If no file path was provided, use the most recent entry in the manifest (last element of the `snapshots` array).

Read three files:
- **post-review snapshot**: the `postReview` file from the manifest entry
- **post-fixes snapshot**: the `postFixes` file from the manifest entry
- **live edited file**: if the user provided a path, read that file. If not, determine the original output path from the current conversation context.

If the `postFixes` file is missing from the manifest entry, the user may have skipped the advisory step. In that case, use the post-review snapshot as the post-fixes snapshot (the diff between post-review and the live file captures everything).

### Step 2: Load review findings

Read the `reviewFindings` file from the manifest entry.

### Step 3: Load accumulator

Read `${CLAUDE_PLUGIN_ROOT}/learning/accumulator.md`. If it doesn't exist, proceed with an empty accumulator. Note this in the agent dispatch so the agent knows thresholds should be higher for promoting to "apply" (less prior evidence to cross-reference).

### Step 4: Determine register

Read the `register` field from the manifest entry. This tells the learning agent which register file to load.

### Step 5: Load current rules

Read these three files from `${CLAUDE_PLUGIN_ROOT}/`:
- The register file: `registers/{register}.md`
- The skill file: `skills/prose-craft/SKILL.md`
- The prose review agent: `agents/prose-review.md`

### Step 6: Dispatch the learning agent

Use the Agent tool:
- `subagent_type`: "prose-craft:learn-review"
- `model`: opus
- `description`: "Analyze edits and propose improvements"
- `prompt`: Include ALL of the following, clearly labeled with headers:

  ```
  ## Post-Review Snapshot
  [full text of post-review file]

  ## Post-Fixes Snapshot
  [full text of post-fixes file]

  ## Post-Manual-Edit (Live File)
  [full text of the user's edited file]

  ## Compacted Review Findings
  [full text of review-findings file]

  ## Current Register: {register name}
  [full text of the register file]

  ## Current SKILL.md
  [full text of SKILL.md]

  ## Current Prose Review Agent
  [full text of prose-review.md]

  ## Accumulator
  [full text of accumulator.md, or "EMPTY -- no prior observations. Use higher evidence thresholds for apply recommendations." if file didn't exist]
  ```

Wait for the agent to return.

### Step 7: Present results to user

Show the agent's full analysis.

For each "apply" recommendation, present it individually with:
- The pattern name and target file
- The evidence table
- The exact proposed edit (old text and new text)

Ask the user to **approve**, **reject**, or **modify** each one. Wait for the user's decision on each recommendation before moving to the next.

"Hold" and "reinforce" observations are shown for information but do not require approval. "Contradiction" flags are shown and the user is asked to resolve them (but resolution is optional and can be deferred).

### Step 8: Apply approved changes

For each approved recommendation, apply the text edit to the target file.

Apply to BOTH locations:
- **Installed plugin copy:** `~/.claude/plugins/cache/local/prose-craft/2.0.0/{target-path}`
- **Source repo copy:** `prose-craft/{target-path}` (relative to the current working directory)

If the source repo copy doesn't exist at the expected path, skip it silently (the user may not be working from the source repo).

For "modify" decisions, apply the user's modified version instead of the agent's proposed text.

### Step 9: Update accumulator

After all recommendations have been processed, update `${CLAUDE_PLUGIN_ROOT}/learning/accumulator.md`.

The accumulator file format:

```markdown
# Accumulator

staleness_threshold: 5

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

---
```

Update rules:

1. **New "hold" observations** from this session: add them to the accumulator with `Sessions seen: 1`, `Sessions since last seen: 0`, and `Status: hold`.

2. **Existing observations matched this session** (the agent merged new instances into an existing pattern): increment `Sessions seen`, reset `Sessions since last seen` to 0, and append the new instance rows.

3. **Existing observations NOT seen this session**: increment `Sessions since last seen` by 1.

4. **Observations promoted to "apply" and approved by user**: remove from the accumulator entirely. They have graduated into actual rule changes.

5. **Observations promoted to "apply" but rejected by user**: keep in the accumulator. Set `Status: rejected`. Rejected observations are never promoted to "apply" again by the agent (the agent should check for this status). They remain as context.

6. **Staleness expiry**: remove any observation where `Sessions since last seen` exceeds the `staleness_threshold` value from the accumulator header (default: 5). The pattern didn't recur; it was likely piece-specific.

### Step 10: Cleanup

1. **Compact review findings**: rewrite the review-findings file to contain only a summary of accept/reject/modify decisions (not the full advisory tables). This preserves the signal for future reference while reducing disk usage.

2. **Delete snapshot files** for this piece: remove the post-review, post-fixes, and review-findings files from the snapshots directory.

3. **Remove the entry** from manifest.json.

4. **Delete orphaned files**: scan the snapshots directory for any files not referenced by any remaining manifest entry. Delete them.

5. If the manifest's `snapshots` array is now empty, delete manifest.json itself.

## Notes

- Snapshots are per-session. If writing spans multiple sessions, only the most recent session's snapshots are available. Earlier sessions' snapshots may have been cleaned up or may reference stale text. The learning analysis works from whatever snapshots exist at invocation time.

- The accumulator is the long-term memory for the learning system. It persists across sessions and across pieces. Its observations are the primary mechanism for patterns to accumulate enough evidence to graduate from "hold" to "apply."

- When the accumulator is empty or doesn't exist, the learning agent works with evidence from the current piece only. The agent uses judgment on thresholds in that case (a single dramatic rewrite can still warrant an "apply" recommendation).

- The `staleness_threshold` in the accumulator header is user-configurable. Lower values mean patterns expire faster (more aggressive pruning). Higher values give patterns more sessions to recur before being discarded.
