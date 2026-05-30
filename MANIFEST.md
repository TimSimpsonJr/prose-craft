# MANIFEST

Structural map of **prose-craft**, a Claude Code plugin that generates and refines prose in a learned personal voice, with a SkillOpt-aligned learning loop that updates the voice from your hand edits.

## Stack

- **Claude Code plugin** (`.claude-plugin/plugin.json`) — skills + agents invoked in-session; no runtime server.
- **Markdown prompts** are the primary artifacts: skills (orchestration), agents (dispatched reviewers/optimizer/judges), registers (per-voice feature descriptions).
- **Python 3 + pytest** for the one true code artifact, `scripts/discipline_check.py` (stdlib `re` only, no deps) — the deterministic half of the learning loop's outcome gate.

## Structure

```
.claude-plugin/plugin.json     Plugin manifest (name, version, component dirs)
README.md                      User-facing overview + setup
LICENSE

skills/
  prose-craft/SKILL.md         Generation skill + review gate: generate in the active register,
                               dispatch the two review agents, fix hard fails (incl. the
                               fatal-pattern silent rewrite + re-check), surface advisories,
                               snapshot each pipeline stage.
  prose-craft-learn/SKILL.md   The learning loop. Mode 1 snapshot save; Mode 2 minibatch
                               learning analysis (optimizer dispatch + gate + pairwise step);
                               Mode 3 evaluator correction; the ablation operation; the
                               accumulator / splits / gate format specs.

agents/
  prose-review.md              High-PRECISION reviewer: AI patterns, banned phrases, the fatal
                               pattern (hard fails), 9 advisory patterns, 26-item AI reference.
  craft-review.md              High-RECALL reviewer: aphoristic destinations, naming, dwelling,
                               literary devices, human-moment anchoring. Self-checks its own
                               suggestions against banned patterns before emitting.
  learn-review.md              The OPTIMIZER. Diffs pipeline output vs. hand edits across a
                               minibatch; proposes <=L_t bounded candidate edits. Read-only.
  taste-judge.md               Shadow judge for the pairwise gate. Logs agreement; gates nothing.
  fatal-pattern-recheck.md     Independent re-checker confirming a fatal-pattern rewrite did not
                               reintroduce the pattern (separate dispatch from the rewriter).

registers/
  register-template.md         Template: Voice Feature Description (vocab / structure / rhetoric /
                               voice) + a Demonstrated Edits exemplar section. The live registers
                               (advocacy, personal, dystopian-fiction) are installed-only data.

setup/                         Register-building + gate inputs:
  sample-collection.md           how to gather writing samples
  pass-1-prompt.md / pass-2-prompt.md / extraction-guide.md   two-pass voice extraction
  brief-stripping-guide.md       strip skill-encoding from a thick brief for the generative gate

scripts/
  discipline_check.py          Deterministic gate half: counts em_dash / caps_phrase /
                               colon_inline / banned_phrase; --diff reports introduced violations.
                               Caps allowlist + non-prose stripping reduce false positives.
  banned_phrases.txt           AI-vocab / ChatGPT-ism list (loaded by the script).

tests/test_discipline_check.py Pytest for the script (20 tests); pytest.ini at root.
learning/accumulator.md        Clean/empty in the repo; the live accumulator is installed-only.
docs/plans/                    SkillOpt loop design + implementation plan.
docs/handoffs/                 Cross-session handoff notes.
```

## Key Relationships

- **Dual location (critical).** Prompt/code artifacts live in the repo and must be reinstalled to `~/.claude/plugins/cache/local/prose-craft/<ver>/` to take effect. **Live data lives ONLY in the installed copy**: the configured registers, `learning/accumulator.md`, `learning/splits.md`, `learning/snapshots/`, retained exemplars, and run logs (`bootstrap-run.md`, `ablation-log.md`, `judge-agreement.md`). The repo's `registers/` holds only the template and its `learning/accumulator.md` is empty. **Never full-reinstall** (it clobbers live data); sync changed prompt/code files selectively.
- **Review gate** (`prose-craft/SKILL.md`): generate -> prose-review (precision; hard fails fixed silently) -> fatal-pattern-recheck on any rewrite -> craft-review (recall; advisories) -> surface to user -> snapshot every stage via `prose-craft-learn`.
- **Learning loop** (`prose-craft-learn/SKILL.md`): `learn-review` reads snapshots + the accumulator's candidate-evidence observations and proposes bounded edits; the **gate** = `discipline_check.py` (objective) + `fatal-pattern-recheck` (semantic) for discipline edits, and a human pairwise step + `taste-judge` (shadow) for taste edits. An edit lands only if it improves a held-out score; recurrence count alone never graduates a rule.
- **PROTECTED field.** `accumulator.md`'s `## Longitudinal Guidance` is read-only to step-level edits ("discipline wins on banned patterns"; "craft-review is high-recall, don't tune it down"). The optimizer must never edit or contradict it.
- **Splits drive the gate.** `learning/splits.md` partitions the advocacy corpus (briefs in the sibling `deflocksc-website` repo, finals in its blog) into train / selection / test; the gate regenerates selection briefs and reads test only for honest-progress.
