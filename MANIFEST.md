# Copydesk — Structural Map

State: v3.0.0 (renamed from prose-craft). Voice-driven prose generation, a dual
review gate, and a SkillOpt-aligned learning loop. User data lives OUTSIDE the
install path at ~/.claude/data/copydesk/ (relocated so plugin updates never clobber it).
WHY in docs/plans/; HOW in the skill/agent prompts; the contract in tests/.

## Stack
- Claude Code plugin (`.claude-plugin/plugin.json`): skills + agents invoked in-session; no runtime server.
- Markdown prompts are the primary artifacts: skills (orchestration), agents (reviewers/optimizer/judges), registers (per-voice feature descriptions).
- Python 3 + pytest for `scripts/discipline_check.py` (stdlib `re` only): the deterministic half of the learning gate.

## Structure
```
.claude-plugin/plugin.json       Manifest (name copydesk, v3.0.0, MIT, component dirs).
.claude-plugin/marketplace.json  Standalone marketplace pointer (source ./).
README.md / LICENSE / pytest.ini Public README, MIT license, pytest config.
skills/
  init/SKILL.md                  copydesk:init -- bootstraps ~/.claude/data/copydesk/ and runs voice extraction.
  write/SKILL.md                 copydesk:write -- register detection, craft rules, the review-gate workflow.
  learn/SKILL.md                 copydesk:learn -- snapshot save + minibatch learning analysis.
agents/
  prose-review.md                High-precision: banned phrases, fatal pattern, em dashes, ChatGPT-isms (hard fails).
  craft-review.md                High-recall: aphoristic endings, naming, dwelling, anchoring.
  fatal-pattern-recheck.md       Independent confirm a fatal-pattern rewrite did not reintroduce it.
  learn-review.md                The optimizer: diffs pipeline output vs hand edits into bounded edits.
  taste-judge.md                 Shadow judge for the pairwise taste gate.
scripts/discipline_check.py      Deterministic banned-pattern check; --diff reports introduced violations.
scripts/banned_phrases.txt       AI-vocab / ChatGPT-ism list.
setup/                           Extraction passes + guides (pass-1/2, sample-collection, extraction, brief-stripping).
tests/                           pytest suite for discipline_check.py; offline.
docs/plans/                      Design docs, incl. the user-data-relocation design.
```

## Key Relationships
- **User data is relocated.** Registers + learning live at `~/.claude/data/copydesk/` (NOT in the install dir), so a plugin update never overwrites them. `copydesk:init` creates that dir idempotently.
- **Review gate** (`skills/write/SKILL.md`): generate -> `prose-review` (precision; hard fails fixed silently) -> `fatal-pattern-recheck` on any rewrite -> `craft-review` (recall; advisories) -> surface -> snapshot every stage via `copydesk:learn`.
- **Learning loop** (`skills/learn/SKILL.md`): `learn-review` proposes bounded edits; the gate = `discipline_check.py` (objective) + `fatal-pattern-recheck` (semantic) for discipline, human pairwise + `taste-judge` (shadow) for taste. An edit lands only if it improves a held-out score.
- **Agent namespace** is `copydesk:*`; agent base filenames are unchanged from the prose-craft era.
