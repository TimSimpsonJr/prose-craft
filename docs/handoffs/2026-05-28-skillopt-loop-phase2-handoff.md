# Handoff: SkillOpt Learning Loop — Phase 1 complete, Phase 2 (live + bootstrap) next

**Date:** 2026-05-28
**Project:** prose-craft (Claude Code plugin) — `C:\Users\tim\OneDrive\Documents\Projects\prose-craft`
**Branch:** `skillopt-learning-loop`

---

## What We Did

Executed the repo-side (Phase 1) of the SkillOpt-aligned learning-loop implementation plan (`docs/plans/2026-05-28-skillopt-learning-loop-implementation.md`). Task 1 (discipline-check script) was done in a prior session; this session did **Tasks 2, 4, 5, 6, 7, 8, 9, 10, 11, 12** — all markdown prompt/agent/doc edits — plus a review-feedback fix, Task 3 prep (corpus pairing + split allocation), and a **selective plugin reinstall**.

Execution mode (user choice): batch all repo edits, reinstall once, then reconvene for the live migrations + bootstrap (where the human is the pairwise gate). Verification of prompt edits is by spec-check now and by the bootstrap dry-run later — no pytest on prose edits (only Task 1's script has tests).

## Decisions Made

- **Absolute ≥2-pieces reusability rule:** a pattern confined to a single piece is always Hold, never Apply — no single-dramatic-rewrite exception. (User decision, commit `c9e5edd`.) Reusability is measured across pieces, or 1 piece + prior accumulator evidence.
- **Leakage-free split allocation:** `s447` goes in **train** (its hand-edit snapshots are gradient evidence), never test — testing on it would leak. This forced 3 selection / 2 test instead of the plan's estimated 3/4.
- **Selective reinstall, not full:** copied only the 9 changed/new prompt+code files into the installed cache. A naive full reinstall would clobber live data (see Context to Reload).
- **Brief retention on cleanup:** the cleanup step deletes a processed piece's brief but requires copying it into the split record first if the piece is promoted to a held-out split, so `splits.md` always points at a durable path.
- **Forward references accepted:** `prose-craft-learn` Step 9 references the `taste-judge` agent and generative-gate harness; both landed later in Tasks 9/10. All resolved.

## Current State

**Commits this session (11), on `skillopt-learning-loop`, no PR yet:**
```
2a9480c Task 12  ablation operation + initial sweep doc
2405fb6 Task 11  evaluator-correction mode (/prose-craft-learn evaluators)
fa01c62 Task 10  brief-stripping guide + generative-gate harness
d354ce1 Task 9   shadow taste-judge agent
e2e8a1f Task 8   independent fatal-pattern re-checker agent
8dc2b0b Task 7   suppression logging in review gate
dce41f8 Task 6   Demonstrated Edits sections
c9e5edd (fix)    absolute >=2-pieces rule
074096d Task 5   prose-craft-learn loop wiring (gate + pairwise, 12 steps)
bec9891 Task 4   learn-review minibatch/budget/success/error-classes
f6b2c67 Task 2   accumulator format (protected guidance + rejected buffer)
```

**New files:** `agents/fatal-pattern-recheck.md`, `agents/taste-judge.md`, `setup/brief-stripping-guide.md` (Task 1 also added `scripts/discipline_check.py`, `scripts/banned_phrases.txt`, `tests/test_discipline_check.py`, `pytest.ini`).

**Plugin reinstalled (selective).** These 9 files were synced repo → `C:\Users\tim\.claude\plugins\cache\local\prose-craft\2.0.0\`: the two skills, `learn-review.md`, the two new agents, `register-template.md`, both `scripts/` files, `brief-stripping-guide.md`. Verified the installed skills carry the new content and that installed `prose-review.md` still has #25/#26. **User is restarting** for it to take effect.

**Live data NOT yet touched** (Phase 2 migrations): installed `learning/accumulator.md` (still old 23-obs format), the 3 live registers (no Demonstrated Edits section yet), no `splits.md`, no `judge-agreement.md` / `bootstrap-run.md` / `ablation-log.md` yet.

## What Remains

Do these after the user confirms the restart took effect. **Pause for explicit go-ahead before each live-data write** (user's standing instruction).

1. **Task 2 (live):** migrate installed `learning/accumulator.md` to the new format. Keep the 23 observations as candidate evidence; add the PROTECTED `## Longitudinal Guidance` (the 3 seed entries already in the format spec) seeded also with the existing "Anchor percentages — declined to promote, piece-specific" note as a do-not-generalize label; add empty `## Rejected Edits` table.
2. **Task 3 (live):** write installed `learning/splits.md` per the approved allocation (below). Verify each selection/test piece has both a brief and a final on disk.
3. **Task 6 (live):** add an empty `## Demonstrated Edits` section to the 3 installed registers (`advocacy.md`, `personal.md`, `dystopian-fiction.md`).
4. **Task 13 (bootstrap, NEEDS USER):** assemble the advocacy minibatch (s447 snapshots + accumulator) → run `learn-review` minibatch → ≤3 candidate edits → gate each (discipline script for discipline edits; retrospective + generative pairwise/judge for taste) → apply accepted to installed registers + retain exemplars + log rejected → `D_test` check on the 2 test pieces → tune `discipline_check.py` regexes against any false positives and re-run `tests/test_discipline_check.py` → record `learning/bootstrap-run.md`.
5. **Task 14:** generate `MANIFEST.md` (owned repo, none yet), commit, push, open PR linking the design doc, merge-commit style. **Also decide** whether to sync repo `prose-review.md` with the installed #25/#26 (only after the ablation sweep says whether they survive).

## Open Questions

- **Repo `prose-review.md` lags installed.** Installed has graduated rules **#25 Performed Specificity** and **#26 Hollow Anadiplosis**; repo has only 1-24 + 6 advisory patterns. Resolve at Task 14, after the bootstrap ablation sweep decides if #25/#26 earn their place. Don't sync before the sweep (would be churn).
- **D_test is only 2 pieces.** Honest-progress reads will be noisy. User confirmed no other blog finals have briefs, so this is the ceiling unless briefs are reconstructed later.

## Context to Reload

**THE DUAL-LOCATION HAZARD (most important).** prose-craft lives in two places:
- **Repo** (`...\Projects\prose-craft`) = clean prompts/scripts. Its `registers/` has ONLY `register-template.md`; its `learning/accumulator.md` is EMPTY.
- **Installed** (`...\.claude\plugins\cache\local\prose-craft\2.0.0\`) = live data: the 3 configured registers, the 23-obs accumulator, snapshots, and graduated rules (prose-review #25/#26).
- **NEVER do a full/naive reinstall.** A whole-directory sync would overwrite the live registers and accumulator with the repo's empty templates and wipe #25/#26. Reinstall = **selective copy of changed prompt/code files only** (skills, learn-review, the new agents, register-template, scripts, brief-stripping-guide). Leave `prose-review.md`, `craft-review.md`, the 3 registers, `accumulator.md`, and `snapshots/` alone.

**Approved splits (advocacy register):**

6 brief↔final pairs exist (briefs in `deflocksc-website/docs/plans/`, finals in `deflocksc-website/src/content/blog/`):
| Final | Brief |
|---|---|
| the-4th-amendment-loophole | blog-rework-4th-amendment-design |
| sc-has-no-license-plate-camera-law | blog-rework-sc-no-law-design |
| h4675-strongest-alpr-bill-in-sc | h4675-blog-post-design |
| how-to-fight-alpr-surveillance-sc | action-guide-blog-post-design |
| flock-safety-patent-facial-recognition | patent-blog-post-design |
| s447-time-is-running-out | s447-post-design |

- **Train (gradient):** s447 snapshots + the 23-obs accumulator. **H.4216 excluded** (confounded — gate ran after the manual edit). `disbursecloud` is the **personal** register, not advocacy — exclude from this loop.
- **Selection (gates edits, 3):** h4675, the-4th-amendment-loophole, flock-safety-patent-facial-recognition.
- **Test (honest progress only, 2):** sc-has-no-license-plate-camera-law, how-to-fight-alpr-surveillance-sc.
- The 4 finals `flock-safetys-track-record`, `99-percent-of-the-plates-they-scan`, `scpif-v-sled-explainer`, `greenville-flock-contracts` have **no briefs** (user confirmed); `building-deflocksc` is meta — all excluded.

**Other gotchas:**
- The advocacy corpus repo is `C:\Users\tim\OneDrive\Documents\Projects\deflocksc-website` (a sibling project, not referenced by path in the plan).
- The discipline-check regexes (caps-adjacency, en-dash, banned-phrase false positives) are deliberately deferred to bootstrap tuning. After editing them, re-run `python -m pytest tests/test_discipline_check.py -v`.
- Snapshots use a 5-section split for s447 (sections 2-5 are separate manifest entries) — treat as one piece's evidence, not five.
- The plan's "Execution status & handoff" section at the top of the implementation plan has been updated to point here.
- CLAUDE.md note: in-repo docs (plans, this handoff, MANIFEST) are coding-task artifacts — do NOT run prose-craft on them.
