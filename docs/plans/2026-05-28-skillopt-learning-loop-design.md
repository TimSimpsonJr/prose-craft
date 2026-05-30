# Design: SkillOpt-Aligned Learning Loop for prose-craft

**Date:** 2026-05-28
**Status:** Design approved in session; implementation plan pending
**Project:** prose-craft (Claude Code plugin)
**References:**
- SkillOpt: *Executive Strategy for Self-Evolving Agent Skills* (arXiv:2605.23904)
- Companion strategy doc: `skill-plugin-architecture-strategy.md`
- Prior diagnosis handoff: `2026-05-28-prose-craft-gate-architecture.md`

---

## 1. Problem

prose-craft proposes change everywhere (prose-review, craft-review, learn-review all propose) but tests improvement nowhere except the human. It is **gradient-rich and gate-poor**: the human is the gate at every layer, which is the scaling complaint that prompted this work.

SkillOpt reframes a skill document as the trainable external state of a frozen model and optimizes it with weight-space discipline: a separate optimizer turns scored rollouts into bounded edits (the **gradient**), and an edit is kept only if it strictly improves a held-out score (the **gate**). The goal of this design is to align prose-craft's learning system with that discipline, adapted to a domain SkillOpt's own Limitation B flags as its boundary: subjective, multi-dimensional, costly to judge.

### Current state (verified against the installed copy, not the clean repo)

- 3 configured registers: `advocacy`, `personal`, `dystopian-fiction`. Voice descriptions are rich and specific.
- ~6 snapshotted pieces (April), plus a larger published advocacy corpus (March onward).
- 23-observation accumulator that promotes **almost nothing**: ~20 of 23 stuck at "seen once," aging toward staleness expiry. Recurrence-gating is structurally mismatched to topically-diverse advocacy writing (a different bill each time rarely repeats a pattern within 5 sessions).
- No outcome signal exists anywhere. Accept/reject is logged for one piece only.

### The real constraint: task diversity, not rollout volume

SkillOpt runs ~40 rollouts/batch × 4 epochs. We have ~12 advocacy (brief → published-final) pairs. But rollout *volume* is not the ceiling: each brief regenerates into many rollouts, and each held-out piece can be scored multiple times to average out generation noise (§4). Bootstrapping plus regeneration is what makes the loop viable on this corpus — which is why it is **essential, not optional**, not a consolation for thin data.

The genuine residual constraints are narrower:
- **Task diversity.** ~12 distinct advocacy tasks is the breadth ceiling; regeneration adds depth (more samples per task), not new failure modes. The optimizer can only learn patterns that surface across those ~12.
- **Split allocation.** Dividing ~12 pieces across train / selection / test is tight. This is the real reason advocacy goes first: it is the only register with enough corpus to split at all. `personal` and `dystopian-fiction` start forward-only.

Expect **few committed edits — but few is not small.** SkillOpt's largest gains (+29.3, +39.0) each arose from a *single* accepted edit. A handful of edits that survive the gate is the method working, not a shortfall.

---

## 2. The SkillOpt mapping

| SkillOpt construct | prose-craft equivalent | Status today |
|---|---|---|
| Frozen model `M` | Opus (gen) + Sonnet (review) | aligned |
| Skill doc = trainable weights | registers + SKILL.md shared rules + agent prompts | aligned (spread across files) |
| Rollout `h(M, x, s)` | generating a piece in a register | aligned |
| Scored trajectory | hand-edit diff | partial — failures only, unscored |
| Optimizer `O` (separate LLM) | learn-review agent | aligned |
| Gradient = edits from **minibatch** reflection | learn-review on **one** piece | missing minibatch |
| Failure **and success** reflection | failure-only | missing success reflection |
| Validation gate: accept iff held-out score strictly improves | recurrence count + human approval | **missing** |
| Textual learning rate `L_t` (≤4, decay) | unbounded applies; soft "prefer sharpening" | missing |
| Rejected-edit buffer | accumulator "rejected" status | partial — no score, not fed back |
| Epoch slow/meta update, protected | accumulator is optimizer-side; no longitudinal meta, no protected field | partial |
| Train / selection / test splits | none | missing |

The top half is aligned. The entire learning **engine** (bottom half) is what this design builds.

### Ablation-derived leverage ranking (SkillOpt Table 3)

This reorders build priority. It surprised the analysis and overrides intuition:

1. **Slow/meta update — dominant.** Removing it costs −22.5 points (catastrophic). For *us* the value is not anti-thrash (we won't run enough epochs to thrash) but **protected institutional memory**: the place scarce human judgments accrete durably.
2. **Edit budget (learning rate)** — bounded vs unbounded: +2.5 to +3.5.
3. **Rejected-edit buffer** — +1.6 to +4.6.
4. **The gate** — never ablated alone; it is necessary substrate, and we lack it entirely, so it must be built regardless.
5. **Minibatch *size*** — nearly flat from 1→32. Minibatch *reflection vs single-trajectory* still matters conceptually (reusable vs anecdotal); the size does not.

---

## 3. Architecture

### 3.1 Two-tier optimization units

- **Tier 1 — the generator (the real weights):** registers + SKILL.md shared craft rules. This is what an epoch optimizes.
- **Tier 2 — the evaluators (part of the gate):** prose-review + craft-review.
- **The optimizer (never self-optimized by its own loop):** learn-review + prose-craft-learn. Improved by hand only.

**Individually:** each register trains against its **own per-register held-out set** (voice is register-specific).
**Together:** SKILL.md shared rules touch every register, so a shared-rule edit is scored across **all** held-out sets. Registers can override shared rules (`dystopian-fiction` does), so the true objective is the **system-level score**; per-artifact optimization is a decomposition checked against it.

**Stability rule (the mutable-evaluator hazard):** never optimize the generator against a *moving* evaluator. **Freeze prose-review and craft-review during a generator run** — they participate in the rollout (the scored piece is post-review), so drift breaks score comparability. Improve evaluators in dedicated runs (§6), then **re-baseline** held-out scores.

**The scorer is not the reviewers.** The taste scorer is human pairwise judgment (v1) or a separate audited model-judge (later) — never craft-review rating its own pipeline's output. Keeping scorer distinct from reviewers prevents the reward-hacking loop.

Each run carries an explicit declaration: *what is optimized, what is frozen.* E.g., "optimize `advocacy.md` + shared craft rules; freeze both reviewers, the discipline script, and human-judgment-as-scorer."

### 3.2 The loop (per round)

1. **Rollouts.** Generate new pieces (online) or regenerate held-out briefs (epoch mode).
2. **Minibatch reflection.** Reflect across a batch of pieces, separating **failures** (hand-edits) from **successes** (un-edited spans), merging with **failure priority**. The batch lets the optimizer distinguish reusable patterns from piece-specific noise directly — replacing cross-session recurrence-gating, which fails on topically-diverse work.
3. **Propose ≤ `L_t` edits** (edit budget; start `L_t` = 2–3), ranked by expected utility.
4. **Gate.** Accept an edit only if it strictly improves the held-out score (§3.3).
5. **Slow-update.** Write a protected longitudinal-guidance block (§3.5).
6. **Rejected-edit buffer.** Record rejected edits + why (the score drop), as negative feedback for later reflection.

### 3.3 The gate's two-fraction scoring

The honest core. Do **not** build a verifier for "is this good." Split:

- **Discipline fraction (objective, automatic):** a **script** counts violations before/after — em-dashes, colon-used-for-inline-elaboration (the graduated rule in SKILL.md), banned-phrase/ChatGPT-ism list, caps-on-phrases (2+ words). Accept only if violations dropped and **no new violation** was introduced. Plus an **independent LLM re-checker** for the semantic fatal-pattern ("not X, it's Y"), which a regex cannot catch reliably — this closes the one ungated generative hole (the silent fatal-pattern *rewrite* at `skills/prose-craft/SKILL.md` ~line 105).
- **Taste fraction (structured-subjective):** **pairwise human judgment** — regenerate held-out content under old vs new skill-state, present A/B, human picks which is more *them*. The human is the only gatekeeper in v1; a model-judge runs in shadow from day one (logging agreement) but does not gate until calibrated (§8). SkillOpt's Limitation B explicitly authorizes "human or model-based evaluation" for the gate in subjective domains, so this is faithful, not a deviation.

The discipline gate is a **regression test** (a guardrail), not a fitness function. It must never be used to *minimize* violations as an optimization target — that trains toward clean-but-lifeless prose, the failure mode prose-review already warns about.

### 3.4 Three data splits

- **`D_tr` (train):** supplies rollout evidence for proposing edits.
- **`D_sel` (selection):** gates updates (the accept/reject test above).
- **`D_test` (test):** used only to report honest progress; never trained or gated on.

Without `D_test` the loop overfits to the gate set across epochs. SkillOpt's 2:1:7 ratio is not literally applicable at our volume; do something proportional — a handful of frozen test pieces per register, checked rarely by pairwise judgment to answer "is the skill actually better?" as distinct from "did this edit pass the gate?"

### 3.5 Slow-update / protected memory (the centerpiece)

An optimizer-side, **protected** field the routine loop cannot overwrite. The deployed registers stay compact; the rich record lives with the optimizer. Seed entries:

- **Gap-D protection:** "`craft-review` is intentionally high-recall; rejection is expected; do NOT tune its triggers down." Makes the boldest agent's boldness un-sandable by construction.
- **User regularization labels:** the logged "declined to promote — piece-specific" (e.g., the Anchor-percentages observation) is a human-provided "do-not-generalize" signal; treat as a labeled negative.
- **Override decisions:** the unlogged human choice to narrow `dystopian-fiction`'s overrides (see §7).

---

## 4. Bootstrapping (advocacy first)

The briefs exist: each advocacy piece has a design doc in `deflocksc-website/docs/plans/` and a published final in `src/content/blog/`. So the generative-gate corpus = **(design-doc brief + published post) pairs across the whole blog history** (a dozen-ish advocacy pieces), not just the 3 snapshotted ones.

Two bootstrap moves, both on existing data:

1. **Proposals from history.** Run minibatch reflection over accumulated hand-edits → candidate edits. Exclude the H.4216 piece (its gate ran *after* the manual edit — a confounded gradient).
2. **Two gate flavors:**
   - **Retrospective gate** (works on existing snapshots, no briefs): does a candidate edit catch a held-out piece's actual corrections without over-flagging kept text? Tests generalization; strong for discipline edits, judge-assisted for taste.
   - **Generative gate** (needs briefs — now available): regenerate the brief under candidate skill-state, compare to the published final by pairwise judgment. Regenerate each brief several times per skill-state and aggregate — this averages out generation noise and lets a small held-out set still yield a stable gate score.

**Brief-stripping (required).** The briefs are thick and skill-entangled: the s447 design doc copies `advocacy.md`'s rules verbatim into a "Voice and Style" section and **pre-names the concept** ("Codification Trap"). Held constant across with/without-edit regenerations, a thick brief makes the edit's effect small (low signal); worse, a brief's embedded *old* voice rules will **contradict an edited register**. So strip the skill-encoding (voice section, pre-named concepts, paragraph-level prose direction) and keep the substantive task content (facts, argument, audience) before regenerating.

**Register coverage:** only `advocacy` has the corpus to bootstrap now. `personal` has little; `dystopian-fiction` has none (only extraction artifacts). Those start forward-only. Each register bootstraps when its own corpus is large enough — consistent with optimizing registers individually.

**Prerequisite (forward):** capture the generation brief in snapshots so the generative gate works on *new* pieces. Historical pieces use the deflocksc design docs.

---

## 5. Extraction as initialization

Extraction is `s_0`. It is the contrastive init (your samples vs a Claude baseline isolates the gross delta in one big step). Training is everything after.

- **Pass-1 (contrastive extraction) stays** — required to cold-start a register with no corpus.
- **Pass-2 (judgment-based pruning) migrates into the loop** — "keep the feature only if it improves a held-out score" replaces "ask a model if it looks distinctive." Real data confirms pass-2 currently changes nothing structural (no feature discovered or deleted; only reorganization + dosing).
- **Existing registers are not re-extracted** — they train from current state.
- **Register lifecycle:** born from extraction (description), refined forever by training (gated description edits + validated exemplars + outcome-pruning).

**The fidelity-vs-discipline tension (make explicit).** Extraction optimizes fidelity to your influences (Orwell uses em-dashes); the discipline layer optimizes not-looking-like-AI; they collide on banned patterns. In the real data, a human had to *reverse* an extraction-proposed em-dash override at the final step. Discipline wins on banned patterns, and the loop must be told not to "relearn" em-dashes/fatal-patterns from the source corpus.

**Tacit layer via exemplars.** The system already deploys exemplars (craft-review's real-author names, SKILL.md's writing samples). The gap: the accumulator's harvested before/after pairs are deleted at graduation (`prose-craft-learn/SKILL.md` Step 9 rule 4). Fix: when the gate **accepts** an edit, retain its winning before/after pair as an exemplar (now a *validated* demonstration) in a capped `## Demonstrated Edits` section per register, fed into generation context.

---

## 6. Evaluator correction loop (separate from generator training)

The reviewers make real errors; freezing a flawed evaluator means training the generator against a flawed signal. They need their own loop with their own ground truth (your advisory accept/reject/modify), at a different cadence, and a re-baseline afterward.

Three distinct error classes (from the real data — do not collapse them):

- **(a) High-recall boldness** — craft-review surfaces non-obvious opportunities; ~60% rejection is the design working. Measure recall-at-1 (did ≥1 suggestion per piece land?), not acceptance rate. **Do not tune down.**
- **(b) Reviewer self-violation** — craft-review emits ~1 fatal-pattern violation per long piece *in its own suggestions* ("Not reform. That's a rescue."). This is a ready-made **objective** metric (self-violation rate); track and fix.
- **(c) Factual hallucination** — craft-review invented a plaintiff and confused two cities. Always wrong, independent of recall/precision.

Split calibration by agent: **prose-review** = high-precision (rejection signals over-firing); **craft-review** = high-recall (rejection is expected).

---

## 7. Instrumentation and data hygiene

- **Suppression logging (Gap F) — build day one.** Confirmed real: on the disbursecloud piece, prose-review produced 14 advisory items (~6 acted on, 7 vanished with no trace); craft-review's 5 opportunities — 0 acted on, with **no decision ledger at all**. The orchestrator (opus) is the dark, behaviorally-decisive filter. Log the full agent findings alongside what opus surfaced. A week of this tells us whether the leak is in the reviewers (proposing badly) or opus (filtering badly) — opposite fixes.
- **Lossy gradient (acknowledge or enrich).** Before/after string pairs cannot represent content-additions (the user added a whole 5th amendment no agent proposed), paragraph-splits for rhythm, or multi-pass refinement (interim snapshots prove iteration). At minimum, capture multi-pass; flag the categories the representation drops.
- **Data hygiene.** Validate that a snapshot is a clean (generate → edit) pair before using it as a gradient. Exclude inverted-pipeline pieces (H.4216).
- **Override integrity check.** `skills/prose-craft/SKILL.md` ~line 21 claims `dystopian-fiction` overrides 3 shared rules; the register delivers 1. Co-optimizing shared + register layers needs an integrity check, ideally with overrides expressed as structured pointers, not prose paraphrase that silently desyncs when a shared rule is reworded.

### The design-doc phase (resolved)

The register/rules are a **single shared artifact** applied at both the brainstorming/design-doc phase and the drafting phase (your CLAUDE.md loads prose-craft during copy-brainstorming; the design doc's "Voice and Style" section is the fingerprint). So optimizing the shared rules via the drafting loop **improves both phases** — no separate design-phase target needed. The one residual: a drafting-stage gradient **under-samples** the decisions made upstream (naming, structure, anchor choice), so those rules get the weakest signal. Free mitigation: the design docs in `docs/plans` already record those upstream decisions — diff design-intent against the published piece for naming/structure signal, no new capture required.

---

## 8. Scope: v1 vs deferred

The deferral principle is narrow: not caution-phasing (sequencing independent builds buys nothing here), but **load-bearing readiness**. Both "deferred" items are still *built* in v1 — just in a non-load-bearing form until the data that would justify trusting them exists.

**v1 (build it all at once — one coherent change, not phased rollout):**
- Minibatch reflection + edit budget (prompt-only edits to `prose-craft-learn` and `learn-review`).
- Held-out gate: discipline script + independent fatal-pattern re-checker + human pairwise taste step.
- Three splits (small, per-register).
- Slow-update protected field with seed entries.
- Rejected-edit buffer with score drops.
- Success reflection over un-edited spans.
- Exemplar retention at graduation.
- Suppression logging.
- Evaluator correction loop (documented mode; can stay light).
- Bootstrap advocacy via proposals + retrospective gate + generative gate (with brief-stripping).
- **Model-judge in shadow mode** — runs alongside every human pairwise pick, logs agreement, gates nothing. Accumulates the calibration corpus and operationalizes the "audit it" requirement. Cost: one extra model call per comparison.
- **Ablation operation + an initial sweep** — the mechanism (drop a rule, regenerate held-out, keep the drop if the gate score holds) plus one sweep over current graduated rules (e.g. prose-review's #25 performed-specificity, #26 hollow-anadiplosis, the colon rule) to test whether they earn their place.

**Deferred — built in v1, promoted later once the data exists:**
- **Promoting the model-judge to a gatekeeper.** The shadow judge gates nothing until its agreement with your picks clears a threshold. Skipping calibration invites reward-hacking: the judge stands in for your taste, the generator learns to exploit its blind spots, and the signal that would catch the drift (you) is out of the loop. Promotion waits on the shadow corpus — a hard dependency, not caution.
- **The recurring ablation cadence.** The operation runs in v1; only *how often* to sweep waits on observed rule-growth. A trivial default covers the interim (sweep before each release, or when rule count crosses a threshold).

---

## 9. Component change list

| File / artifact | Change |
|---|---|
| `skills/prose-craft-learn/SKILL.md` | Minibatch loading (last N unprocessed entries, not 1); brief-capture; suppression snapshot stage; gate-invocation step; exemplar retention instead of deletion at Step 9 rule 4 |
| `agents/learn-review.md` | Minibatch reflection (reusable vs anecdotal across batch); failure+success passes, failure-priority merge; edit budget `L_t`; rejected-edit buffer with score; data-hygiene filter |
| `learning/accumulator.md` | Demoted from graduation-gate to optimizer-side slow record; add protected longitudinal-guidance field + seed entries |
| `agents/prose-review.md`, `agents/craft-review.md` | Frozen during generator runs; corrected via the separate evaluator loop; craft-review measured on recall-at-1 + self-violation rate |
| `registers/*.md` | Gain capped `## Demonstrated Edits` exemplar sections fed into generation |
| **New** — discipline-check script | Em-dash / colon-misuse / banned-phrase / caps-phrase counter; "no new violation" check |
| **New** — held-out set designation | 5–10 frozen pieces per register for `D_sel`; small `D_test` |
| **New** — brief-stripping + generative-gate harness | Strip skill-encoding from deflocksc design docs; regenerate-and-compare workflow |

---

## 10. Open questions / risks

- **Brief-stripping judgment call.** What counts as "substantive" vs "skill-encoding" in a thick design doc is a human call; document a rule of thumb.
- **Data volume.** Gains may be modest at our corpus size; the honest target is fewer, higher-confidence edits.
- **Multi-skill co-optimization is uncharted.** SkillOpt leaves heterogeneous/multi-skill explicitly unresolved; our register routing is ahead of the paper, but shared+register interaction has no theoretical guarantee. The override-integrity check is the guard.
- **Model-judge reward-hacking** (when built) — audit against periodic human re-judging.

---

## 11. What this does to the core problem

Today: human is the gate at every layer. After: the optimizer proposes ≤ `L_t` edits; the **script** gates the discipline ones with zero human input; the **taste** ones reach you as a few A/B regenerations a couple of times per batch. You become a sparse pairwise judge at one layer — SkillOpt's "few accepted edits" plus the strategy doc's pairwise principle. You don't stop being the measurement; you stop being the measurement for everything that never needed you.
