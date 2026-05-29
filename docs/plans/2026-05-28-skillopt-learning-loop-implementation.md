# SkillOpt-Aligned Learning Loop — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace prose-craft's recurrence-gated learning loop with a SkillOpt-aligned one: bounded edits proposed from minibatch reflection, accepted only when a held-out outcome score improves, with the human spent as a sparse pairwise judge.

**Architecture:** Claude-Code-native orchestration. The "optimizer" is the existing `learn-review` agent and `prose-craft-learn` skill, extended; the "gate" is a deterministic Python discipline-check script plus an in-session human pairwise step plus a shadow model-judge. There is **no standalone program** — Claude orchestrates the loop in-session using the existing Agent-dispatch pattern (same as the current review gate). The one true code artifact is the discipline-check script.

**Tech Stack:** Markdown prompts (skills/agents/registers); Python 3 + `pytest` for the discipline-check script (stdlib `re` only, no deps); the deflocksc-website `docs/plans` design docs + `src/content/blog` finals as the advocacy training corpus.

---

## Execution status & handoff (read first)

**As of 2026-05-28, branch `skillopt-learning-loop`.** This plan was produced and Task 1 executed in a prior session; the rest is handed to a fresh session for interactive execution.

**Done:** Task 1 (discipline-check script) — TDD, 14/14 tests green, spec + code-quality reviewed. Commits `92e83cb` (script) → `6413915` (CLI hardening + word-boundary matching) → `0598927` (lookaround boundaries). The design doc and this plan are committed at `57648dd`.

**Start here:** Task 2. Tasks 2–14 remain. No PR yet — the branch accumulates and the single PR comes at Task 14.

**Carry these forward (not fully spelled out in the task bodies):**
- **Do not mutate live plugin data without the user's explicit go-ahead.** Tasks that write the installed copy (`C:\Users\tim\.claude\plugins\cache\local\prose-craft\2.0.0\`) — Task 2's accumulator migration over 23 real observations, Task 6's edits to the advocacy/personal/fiction registers the user actively writes with, Tasks 3/9/12's splits and logs — touch un-versioned data the user depends on. Confirm before each.
- **Review proportionally.** Task 1 was real code and earned full TDD + two-stage review. The rest are markdown prompt edits and procedures; a spec-check (does the prompt say what the plan asks?) plus a dry-run is enough. Don't wrap pytest ceremony around prose edits.
- **Headless verification is limited.** "Verify by dry-run" means running the loop on a real batch, which needs the plugin reinstalled and the user's pairwise judgment. Prompt edits written without that are speculative until exercised.
- **Task 1 deferrals → Task 13 tuning:** the discipline script's caps-adjacency and en-dash heuristics, plus any banned-phrase false positives, get tuned against real text during the bootstrap.
- **Briefs are thick and skill-entangled** (see Task 10): strip the copied voice section and pre-named concepts before using a deflocksc design doc as a regeneration brief.

**Kickoff for the fresh session:** load this plan + `docs/plans/2026-05-28-skillopt-learning-loop-design.md`, invoke `superpowers:executing-plans`, start at Task 2.

---

## Implementation decisions (override before starting if you disagree)

1. **Claude-native, not a standalone program.** The loop runs in a Claude Code session. Rationale: the whole plugin is prompt-driven, the taste gate needs a human in the loop, and the corpus is ~12 pieces — a batch program is unjustified. *If you want a standalone Python orchestrator instead, this plan changes substantially.*
2. **Python for the discipline-check script** (`scripts/discipline_check.py`). Swap to Node if preferred; only the test commands change.
3. **No worktree was created** (brainstorming didn't open one). For a markdown-heavy plugin this is low-risk; create one with @superpowers:using-git-worktrees if you want isolation.

## Repo vs installed copy (critical)

prose-craft has two locations and they hold different things:
- **Code/prompt artifacts** (`skills/`, `agents/`, `registers/register-template.md`, `scripts/`, format docs) → edit in the **repo** (`C:\Users\tim\OneDrive\Documents\Projects\prose-craft`), then reinstall/sync to the cache.
- **Live data** (configured registers `advocacy.md`/`personal.md`/`dystopian-fiction.md`, `learning/accumulator.md`, snapshots, splits, exemplars) → lives in the **installed copy** (`C:\Users\tim\.claude\plugins\cache\local\prose-craft\2.0.0\`). The repo's registers are intentionally template/clean.

So: develop prompts/scripts in the repo; run the loop against installed data; data-migration steps target the installed copy. Each task says which.

## Testing approach

- **Discipline-check script:** real TDD (pytest, red/green/commit).
- **Prompt edits:** verified by a **dry-run** — invoke the changed skill/agent on a real 2-piece advocacy batch and confirm the described behavior. No unit tests.
- **Procedures (bootstrap, ablation):** verified by running them once and recording output.

---

## Task 1: Discipline-check script (TDD)

The deterministic objective gate. Counts violations and, in diff mode, reports whether a rewrite introduced a NEW violation. Does **not** detect the semantic fatal-pattern (that's the LLM re-checker, Task 8).

**Files:**
- Create: `scripts/discipline_check.py`
- Create: `tests/test_discipline_check.py`
- Create: `scripts/banned_phrases.txt` (one phrase per line, seeded from `agents/prose-review.md`'s AI-vocab + ChatGPT-ism lists)
- Create: `pytest.ini` (minimal)

**Step 1: Write failing tests**

```python
# tests/test_discipline_check.py
from scripts.discipline_check import count_violations, introduced_new_violation

def test_counts_em_dashes():
    assert count_violations("a — b — c")["em_dash"] == 2

def test_counts_caps_phrases_not_single_words():
    # single caps word is allowed (advocacy technique); 2+ in a row is a violation
    v = count_violations("Say NO today. This is REALLY BAD news.")
    assert v["caps_phrase"] == 1  # "REALLY BAD"

def test_colon_inline_elaboration_flagged_list_colon_ok():
    assert count_violations("The point: it works.")["colon_inline"] == 1
    assert count_violations("Three asks:\n- one\n- two")["colon_inline"] == 0

def test_banned_phrase_hit():
    assert count_violations("It's worth noting that delve is bad.")["banned_phrase"] >= 1

def test_introduced_new_violation_true_when_new_type_appears():
    before = "clean text"
    after = "now with an em — dash"
    assert introduced_new_violation(before, after) is True

def test_introduced_new_violation_false_when_only_reduced():
    before = "em — dash here"
    after = "em dash gone"
    assert introduced_new_violation(before, after) is False
```

**Step 2: Run, verify red**

Run: `python -m pytest tests/test_discipline_check.py -v`
Expected: FAIL (module not found).

**Step 3: Implement minimal script**

```python
# scripts/discipline_check.py
import re, sys, json, pathlib

BANNED = [l.strip().lower() for l in
          (pathlib.Path(__file__).parent / "banned_phrases.txt").read_text(encoding="utf-8").splitlines()
          if l.strip()]

def count_violations(text: str) -> dict:
    caps_phrase = len(re.findall(r"\b[A-Z]{2,}(?:\s+[A-Z]{2,})+\b", text))
    em_dash = text.count("—") + len(re.findall(r"(?<!-)--(?!-)", text))
    # colon used for inline elaboration: ": " followed by a word, not introducing a list (next non-space isn't a newline/bullet)
    colon_inline = len(re.findall(r":\s+(?![\n\-\*\d])", text))
    low = text.lower()
    banned_phrase = sum(low.count(p) for p in BANNED)
    return {"em_dash": em_dash, "caps_phrase": caps_phrase,
            "colon_inline": colon_inline, "banned_phrase": banned_phrase}

def introduced_new_violation(before: str, after: str) -> bool:
    b, a = count_violations(before), count_violations(after)
    return any(a[k] > b[k] for k in a)

if __name__ == "__main__":
    # usage: discipline_check.py FILE  |  discipline_check.py --diff BEFORE AFTER
    if sys.argv[1] == "--diff":
        before = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")
        after = pathlib.Path(sys.argv[3]).read_text(encoding="utf-8")
        print(json.dumps({"counts": count_violations(after),
                          "introduced_new": introduced_new_violation(before, after)}))
    else:
        text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
        print(json.dumps(count_violations(text)))
```

**Step 4: Run, verify green.** `python -m pytest tests/test_discipline_check.py -v` → PASS. Iterate the regexes against failures (the colon and caps heuristics will need tuning on real pieces in Task 13).

**Step 5: Commit.** `git add scripts/ tests/ pytest.ini && git commit -m "feat: deterministic discipline-check script for the outcome gate"`

---

## Task 2: Restructure the accumulator (format + live migration)

Demote it from graduation-gate to optimizer-side slow record. Add the protected longitudinal field and the rejected-edit buffer.

**Files:**
- Modify (repo): `skills/prose-craft-learn/SKILL.md` (Step 9 — the accumulator format spec)
- Migrate (installed): `learning/accumulator.md`

**Step 1:** In `prose-craft-learn/SKILL.md` Step 9, replace the recurrence-graduation rules with: observations are evidence for *proposing* candidate edits (Task 4), not promoted by recurrence count. Add two new top-level sections to the format:

```markdown
## Longitudinal Guidance (PROTECTED — step-level edits MUST NOT modify this)
- craft-review is intentionally high-recall; rejection is expected; do NOT tune its triggers down.
- Discipline wins on banned patterns: never restore em-dashes / fatal-pattern from a source corpus even if an influence uses them.
- User regularization labels (do-not-generalize): <list>

## Rejected Edits (negative feedback for the optimizer)
| Edit | Target | Held-out score delta | Round |
```

**Step 2:** Migrate the installed `learning/accumulator.md` to the new format — keep existing observations as candidate evidence, add the two new sections, seed Longitudinal Guidance with the three entries above plus the existing "declined to promote — piece-specific" Anchor-percentages note as a do-not-generalize label.

**Step 3 (verify):** Re-read the migrated file; confirm the protected section is present and the seed entries are correct.

**Step 4: Commit.** `git add skills/prose-craft-learn/SKILL.md && git commit -m "feat: accumulator becomes optimizer-side slow record with protected guidance + rejected buffer"` (the installed data migration is not committed — repo accumulator stays clean).

---

## Task 3: Designate held-out splits

**Files:** Create (installed) `learning/splits.md`.

**Step 1:** Enumerate the advocacy corpus: pair each `deflocksc-website/docs/plans/*-design.md` brief with its `src/content/blog/*.md` final. List them.

**Step 2:** Assign each advocacy piece to `train` / `selection` / `test`. With ~12 pieces, target ≈ 5 train / 3 selection / 4 test. **Exclude** the H.4216 piece from gradient use (confounded). Record the assignment in `splits.md` with the brief path + final path per piece.

**Step 3 (verify):** Confirm every selection/test piece has both a brief and a final on disk (the gate needs both).

**Step 4: Commit** the format doc only if you add a `splits-template.md` to the repo; the live `splits.md` is installed-only data.

---

## Task 4: learn-review agent — minibatch, budget, success reflection, error classes

**Files:** Modify (repo): `agents/learn-review.md`

**Step 1 (minibatch):** Change the analysis unit from "this piece" to "this batch of N pieces." Add: "A pattern appearing in ≥2 pieces is reusable; in 1 piece, anecdotal — hold it, do not propose it as an edit yet."

**Step 2 (edit budget):** In the Apply tier, add: "Propose at most `L_t` edits (default 3), ranked by expected utility. Bounded updates preserve continuity."

**Step 3 (success reflection):** Add a pass over **un-edited spans** of hand-edited pieces: "These are successes — what the skill got right. Use them to reinforce/protect existing rules and to nominate positive exemplars. Merge with failure-priority (failures first)."

**Step 4 (error classes for evaluators):** Replace the uniform "consistent rejection = over-firing" logic with three classes: (a) high-recall boldness (craft-review — rejection expected, measure recall-at-1, do NOT tighten), (b) reviewer self-violation (track rate, propose a fix), (c) factual hallucination (always flag).

**Step 5 (protected field):** Add: "Never propose edits to the accumulator's Longitudinal Guidance section."

**Step 6 (dry-run verify):** Invoke `prose-craft-learn` on a 2-piece advocacy batch (after Task 5). Confirm the agent (a) separates reusable vs anecdotal, (b) caps at `L_t`, (c) emits a success-reflection section, (d) does not touch the protected field.

**Step 7: Commit.** `git add agents/learn-review.md && git commit -m "feat(learn-review): minibatch reflection, edit budget, success reflection, evaluator error classes"`

---

## Task 5: prose-craft-learn skill — loading, brief-capture, suppression log, exemplar retention, gate + pairwise step

**Files:** Modify (repo): `skills/prose-craft-learn/SKILL.md`

**Step 1 (minibatch loading):** Mode 2 Step 1 — load the last N unprocessed manifest entries (default N=3), not just the most recent. Pass all N snapshot-triples to learn-review.

**Step 2 (brief-capture):** In Mode 1 snapshot save, add capture of the **generation brief/prompt** alongside the text, so future pieces are regenerable for the gate.

**Step 3 (suppression log):** Add a snapshot stage that records the **full** agent findings (from both review agents) alongside which ones the orchestrator surfaced to the user — the Gap-F instrumentation.

**Step 4 (exemplar retention):** Replace Step 9 rule 4 ("remove graduated observations"). On an edit accepted by the gate, **retain its winning before/after pair** as an exemplar appended to the target register's `## Demonstrated Edits` section (Task 6), FIFO-capped at 8–12.

**Step 5 (gate invocation):** Add a gate step: for each candidate edit from learn-review, run the discipline script (`python scripts/discipline_check.py --diff before after`) for discipline edits, and the pairwise step (Step 6) for taste edits. Accept only if discipline introduced no new violation / taste pick favors the edited version.

**Step 6 (pairwise + shadow judge):** Add the human pairwise step — regenerate a selection-set piece old-vs-new (several samples, aggregate), present A/B, capture the human pick. Log the shadow judge's pick alongside (Task 9). The human is the only gatekeeper; the judge gates nothing.

**Step 7 (dry-run verify):** Run the full Mode 2 on a 2-piece batch; confirm loading, snapshotting with brief, suppression log written, and the gate step fires.

**Step 8: Commit.** `git add skills/prose-craft-learn/SKILL.md && git commit -m "feat(prose-craft-learn): minibatch load, brief-capture, suppression log, exemplar retention, outcome gate + pairwise step"`

---

## Task 6: Register `## Demonstrated Edits` sections

**Files:** Modify (repo): `registers/register-template.md` and `skills/prose-craft/SKILL.md`; (installed) the three live registers.

**Step 1:** Add a `## Demonstrated Edits` section to `register-template.md` (verbatim before/after pairs, no commentary, FIFO-capped 8–12) with a usage note.

**Step 2:** In `prose-craft/SKILL.md`, add to generation instructions: "Read the active register's Demonstrated Edits and treat them as exemplars alongside the feature description."

**Step 3:** Add an empty `## Demonstrated Edits` section to the three installed registers.

**Step 4: Commit** (repo files only). `git add registers/register-template.md skills/prose-craft/SKILL.md && git commit -m "feat: Demonstrated Edits exemplar sections fed into generation"`

---

## Task 7: Suppression logging in the live review gate

**Files:** Modify (repo): `skills/prose-craft/SKILL.md` (Review Gate section).

**Step 1:** After both review agents return, before processing, record the complete findings set. After the orchestrator decides what to surface/silently-fix, record the surfaced/suppressed split into the snapshot (ties to Task 5 Step 3).

**Step 2 (dry-run verify):** Generate a short advocacy snippet, run the gate, confirm the full-findings-vs-surfaced record is written.

**Step 3: Commit.** `git add skills/prose-craft/SKILL.md && git commit -m "feat: log full review findings vs surfaced (Gap F instrumentation)"`

---

## Task 8: Independent fatal-pattern re-checker

The silent fatal-pattern *rewrite* is the one ungated generative hole. A re-checker that did NOT perform the rewrite confirms it didn't reintroduce the pattern.

**Files:** Create (repo): `agents/fatal-pattern-recheck.md` (tiny sonnet agent), and wire it into `prose-craft/SKILL.md`'s hard-fail handling.

**Step 1:** Write the agent: input = the rewritten passage; output = pass/fail on whether any fatal-pattern variant survived, with the quote. It must be a *different* dispatch than the one that wrote the rewrite (separation of proposer and checker).

**Step 2:** In `prose-craft/SKILL.md`, after a fatal-pattern silent rewrite, dispatch the re-checker; if it fails, redo the rewrite or escalate to the user.

**Step 3 (dry-run verify):** Feed a passage containing "Not X. It's Y.", confirm the rewrite happens and the re-checker passes the result; feed a sneaky cross-sentence variant, confirm it's caught.

**Step 4: Commit.** `git add agents/fatal-pattern-recheck.md skills/prose-craft/SKILL.md && git commit -m "feat: independent re-checker closes the ungated fatal-pattern rewrite"`

---

## Task 9: Shadow model-judge

**Files:** Create (repo): `agents/taste-judge.md` (a *judging* rubric, distinct from craft-review's generating concerns).

**Step 1:** Write the judge: input = brief + two regenerations (A/B); output = which is more in-register, with reasoning, built from a judging rubric (how to evaluate voice fidelity), NOT a generating rubric.

**Step 2:** Wire into Task 5 Step 6: the judge runs on every pairwise comparison, its pick + the human pick are logged to an agreement log (installed: `learning/judge-agreement.md`). The judge gates nothing.

**Step 3 (verify):** Run on one A/B; confirm both picks logged and the judge does not influence acceptance.

**Step 4: Commit.** `git add agents/taste-judge.md skills/prose-craft-learn/SKILL.md && git commit -m "feat: shadow taste-judge logs agreement, gates nothing (calibration corpus)"`

---

## Task 10: Brief-stripping + generative-gate harness

**Files:** Create (repo): `setup/brief-stripping-guide.md`; extend `prose-craft-learn/SKILL.md` with a generative-gate procedure.

**Step 1 (stripping rule):** Document what to strip from a deflocksc design-doc brief — the "Voice and Style" section, pre-named concepts, paragraph-level prose direction — keeping substantive content (facts, argument, audience). Give the s447 design doc as a worked example.

**Step 2 (harness procedure):** Document: stripped brief + skill-state s → dispatch a generation sub-agent (existing Agent pattern) → repeat k times → compare aggregate to the published final via Task 5/6 pairwise + judge. This is in-session orchestration, not a script.

**Step 3 (verify):** Strip the s447 brief, regenerate once under the current advocacy register, eyeball that the output is a plausible draft (not a copy of the brief).

**Step 4: Commit.** `git add setup/brief-stripping-guide.md skills/prose-craft-learn/SKILL.md && git commit -m "feat: brief-stripping + generative-gate procedure"`

---

## Task 11: Evaluator correction loop (documented mode)

**Files:** Add a new mode to `prose-craft-learn/SKILL.md` (e.g. `/prose-craft-learn evaluators`).

**Step 1:** Document: ground truth = your advisory accept/reject/modify decisions (from the suppression log + review-findings). Metrics: craft-review on recall-at-1 + self-violation rate; prose-review on precision. Freeze evaluators during generator runs; this mode runs separately and re-baselines held-out scores afterward.

**Step 2 (verify):** Run the mode against the existing review-findings; confirm it reports recall-at-1 and self-violation rate without proposing trigger-tightening for craft-review.

**Step 3: Commit.** `git add skills/prose-craft-learn/SKILL.md && git commit -m "feat: separate evaluator-correction mode with error-class-aware metrics"`

---

## Task 12: Ablation operation + initial sweep

**Files:** Document in `prose-craft-learn/SKILL.md`; record results in (installed) `learning/ablation-log.md`.

**Step 1 (operation):** Document: drop a rule, regenerate the selection set, keep the drop if the gate score does not fall.

**Step 2 (initial sweep):** Run it once on current graduated rules — prose-review's #25 (performed-specificity), #26 (hollow-anadiplosis), and the SKILL.md colon rule. Record which earn their place.

**Step 3 (verify):** Confirm the log records a keep/remove decision + score delta per rule.

**Step 4: Commit** (the operation doc only). `git add skills/prose-craft-learn/SKILL.md && git commit -m "feat: ablation operation + initial sweep on graduated rules"`

---

## Task 13: Bootstrap run (end-to-end integration)

The first real exercise of the whole loop on the advocacy corpus. This is where the discipline-script heuristics get tuned against real text.

**Step 1:** Assemble the advocacy minibatch from `splits.md` train set (existing hand-edits + briefs).
**Step 2:** Run proposals (learn-review minibatch) → candidate edits (≤ L_t).
**Step 3:** Gate each: discipline script for discipline edits; retrospective gate (does it predict held-out corrections?) + generative gate (regenerate stripped briefs, pairwise + shadow judge) for taste edits.
**Step 4:** Apply accepted edits to the installed registers; retain winning pairs as exemplars; log rejected edits + score deltas; leave the protected field untouched.
**Step 5:** Run the `D_test` check: pairwise-judge a couple of test pieces old-vs-new to confirm genuine improvement, not validation-set fit.
**Step 6:** Record the run (edits accepted/rejected, test verdict) in `learning/bootstrap-run.md`. Tune discipline-script regexes against any false positives surfaced here, re-run Task 1 tests.

**Verify:** A small number (1–3) of edits survived the gate, the test check did not regress, and the accumulator/exemplars/rejected-buffer all updated correctly.

---

## Task 14: MANIFEST + PR

**Step 1:** Generate `MANIFEST.md` at the repo root (owned repo, none exists yet) per the global convention — Stack / Structure / Key Relationships. Include the new `scripts/`, `tests/`, the new agents, and the changed skills.
**Step 2:** Commit MANIFEST.
**Step 3:** Push the branch and open a PR summarizing the SkillOpt alignment (link the design doc). Use a merge commit per the global git-merge convention.

---

## Notes for the executor

- **Dual location:** prompt/script edits go in the repo and must be reinstalled to take effect in a live session; data migrations target the installed copy. Don't commit installed data into the clean repo.
- **Most "verification" is a dry-run, not a test.** Only Task 1 has pytest. For prompt tasks, the bar is "invoke it on a real 2-piece advocacy batch and confirm the behavior."
- **Order matters:** Tasks 1–3 are foundations; 4–9 are the loop; 10–12 are the bootstrap tooling + evaluator/metabolism; 13 exercises everything; 14 ships it.
- **Reference skills:** @superpowers:executing-plans (task-by-task), @superpowers:test-driven-development (Task 1 only), @superpowers:verification-before-completion (before any "done" claim, especially Task 13).
