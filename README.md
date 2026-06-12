# Copydesk

![License](https://img.shields.io/badge/license-MIT-blue) ![Version](https://img.shields.io/badge/version-3.0.0-informational) ![Built for Claude Code](https://img.shields.io/badge/built%20for-Claude%20Code-8A3FFC) ![Python](https://img.shields.io/badge/python-3.12-3776AB) ![Status](https://img.shields.io/badge/status-beta-orange)

Copydesk turns findings into publishable writing in your own voice. You feed it your raw material (an investigation's findings, research notes, a transcript, an outline) and it drafts in your own voice, then runs the draft past two reviewers before you ever see it: one that hunts AI tells and voice drift, one that checks whether the writing actually lands. The output comes back clean, with a short advisory table you can accept or reject row by row.

It learns the voice from samples of your own writing, and it keeps refining from your edits. Every time you fix a draft by hand, Copydesk can study what you changed and sharpen its rules so the next draft needs fewer fixes. Your writing, your registers, and everything the learning loop accumulates stay on your machine, inside your own Claude Code session.

## How it works

**Your raw material** → register select (pick the voice that fits) → draft in your voice → a **dual review gate** runs `prose-review` and `craft-review` in parallel → hard fails are fixed silently and everything else comes back as an advisory table → **your final draft**. When you edit it by hand, the **learning loop** studies the change and sharpens the rules for next time.

## What you can do with it

- **Write up findings in your own voice.** Hand Copydesk an investigation's findings and ask it to write the piece. It activates automatically whenever you ask Claude to write text for an audience (a blog post, an article, advocacy copy, an email, a newsletter), drafts in the register that fits, and runs the review gate before you see anything.
- **Keep separate voices for separate work.** Configure one register for advocacy copy and another for personal essays. Copydesk detects which fits the context and loads that voice profile as the primary instruction. If it's ambiguous, it asks which register to use.
- **Catch AI tells before they reach the page.** The gate fixes em dashes, the "this isn't X, this is Y" construction, and the ChatGPT-isms silently, and surfaces everything else (voice drift, structural monotony, dead transitions) as advisory rows you decide on.
- **Sharpen the voice from your edits.** Edit a draft by hand, then run `/copydesk:learn` to study what you changed. It diffs the pipeline output against your hand edits and proposes bounded improvements to your register, the skill rules, or the review agents.
- **Build the voice once from your own samples.** Run `/copydesk:init`: it sets up your data directory and walks you through a two-pass extraction over 10-20 samples of your writing, producing a register that captures your vocabulary, sentence structure, rhetorical moves, and voice qualities. Run it again any time to add another register.

## Why it's useful

Most AI writing reads like AI writing. It puffs up significance, leans on the same dozen transition words, and forces every idea into a group of three. A reader can feel it even when they can't name it. Copydesk's job is to make the writing sound like a specific person wrote it, because a specific person did the thinking, and then to defend that voice with a review pass that knows exactly what machine writing looks like.

The two reviewers pull in deliberately different directions. One is tuned for precision: it fires rarely and is meant to be right, catching banned phrases and voice drift. The other casts wide for craft opportunities you'd otherwise miss (a pattern you described but never named, an ending that summarizes instead of landing). Most of what it surfaces gets rejected, and that's the design working. You stay in control of every judgment call. Hard fails get fixed for you; everything else is a suggestion you can wave off.

The learning loop compounds. The initial extraction gets you a usable voice. Your edits make it precise. Over a handful of pieces, the drafts tend to need fewer corrections, because the system has watched what you actually do and adjusted its rules to match, with a held-out gate making sure each change is a real improvement and not just noise.

## Quick start

Install it from the Fieldwork marketplace:

```
/plugin marketplace add TimSimpsonJr/fieldwork-plugins
/plugin install copydesk@fieldwork
```

Build your voice once. Run `/copydesk:init` (about 30 minutes, using Claude Sonnet). It creates your data directory at `~/.claude/data/copydesk/` and walks you through gathering writing samples and two extraction passes, leaving you with a register Copydesk draws on automatically.

After that, just ask Claude to write something for an audience. The skill activates on its own, drafts in the register that fits, runs the review gate, and hands you a clean draft with an advisory table.

When you've edited a draft by hand and want the system to learn from it:

```
/copydesk:learn path/to/your-edited-file.md
```

## Under the hood

The mechanics behind a draft.

### The two reviewers

After Copydesk drafts a piece, it dispatches both review agents in parallel before you see the text. They are tuned for opposite jobs:

| Agent          | Tuned for     | What it checks                                                                                   | How its findings land                    |
|----------------|---------------|--------------------------------------------------------------------------------------------------|------------------------------------------|
| `prose-review` | high precision | banned phrases, the fatal pattern, em dashes, ChatGPT-isms (hard fails); plus voice drift, mid-tier AI vocabulary, and structural patterns (advisory) | hard fails fixed silently; rest advisory |
| `craft-review` | high recall    | aphoristic endings, unnamed concepts, central-point dwelling, structural literary devices, human-moment anchoring | advisory opportunities                   |

`prose-review` carries a reference catalog of AI writing patterns (undue emphasis on significance, copula avoidance, rule-of-three overuse, generic positive conclusions, and the rest). `craft-review` self-checks its own suggestions against the banned-pattern list before it emits them, so it can't hand you a "fix" that smuggles in a fatal pattern.

### Hard fails vs. advisories

Two outcomes come out of the gate. **Hard fails** (em dashes, the "this isn't X, this is Y" fatal pattern, AI vocabulary, ChatGPT-isms) are fixed before you ever see the draft. Whenever a fatal pattern gets rewritten, a separate `fatal-pattern-recheck` agent independently confirms the rewrite didn't reintroduce it (the writer and the checker are deliberately different dispatches). **Everything else** comes back as an advisory table:

| # | Line | Pattern | Current | Proposed fix |
|---|------|---------|---------|--------------|
| 1 | "Furthermore, the committee decided..." | Dead AI transition | "Furthermore" is a dead transition | Cut it. Start the sentence at "The committee decided..." |

You accept, reject, or modify each row individually.

### The learning loop

After you edit a draft by hand, `/copydesk:learn` diffs the pipeline's output against your hand edits and dispatches the `learn-review` optimizer, which proposes a small, bounded set of candidate edits to your register, the skill rules, or the review agents. Nothing is applied on recurrence count alone. Each candidate has to pass a held-out gate:

| Edit type       | What it changes                                 | How it's gated                                                                 |
|-----------------|-------------------------------------------------|--------------------------------------------------------------------------------|
| Discipline edit | objective banned patterns (em dashes, colons-for-inline-elaboration, caps-on-phrases, the banned list, the fatal pattern) | `scripts/discipline_check.py` plus the `fatal-pattern-recheck` agent           |
| Taste edit      | voice, craft, structure, word choice            | a human A/B pairwise pick, with the `taste-judge` agent logging a shadow vote   |

The discipline script is a regression guardrail (it confirms a change didn't introduce a new violation), never an optimization target. On taste edits you are the only gatekeeper; the shadow judge only accumulates calibration data. An edit lands only if it strictly improves the held-out result, and observations that stop recurring go stale and get cleaned up on their own.

### Project layout

See [MANIFEST.md](MANIFEST.md) for the full file tree and how the pieces fit together.

> [!NOTE]
> **What you need:** Python 3.12 and [Claude Code](https://docs.anthropic.com/en/docs/claude-code), and nothing else. Copydesk's one script is standard-library Python, so there's nothing extra to install. (mise, Node, and Docker are contributor-only.)

> [!IMPORTANT]
> **Your data & privacy:** Copydesk runs entirely inside your own Claude Code session. Your writing samples, your drafts, your registers, and everything the learning loop accumulates stay on your machine; nothing is uploaded to a Copydesk service, because there isn't one. Your registers and all learning state (the accumulator, snapshots, and run logs) live in `~/.claude/data/copydesk/` on your own machine, kept separate from the plugin code so a plugin update never touches them. The review gate scrubs em dashes, AI vocabulary, and ChatGPT-isms automatically before a draft reaches you. The one bundled feature note: Copydesk writes *outward-facing prose*, so it does not redact PII for you. If a draft draws on findings that contain names, addresses, or other sensitive details, treat redaction as your responsibility (or hand that step to Magpie before you write).

## For developers

```bash
pytest tests/ -v
```

The Python suite is 20 tests for `scripts/discipline_check.py`, all offline, no API key needed. The script is standard-library only (`re`), so there is nothing to install beyond Python itself.

**Requirements:** Python 3.12 and [Claude Code](https://docs.anthropic.com/en/docs/claude-code). No third-party Python dependencies.

## Part of the Fieldwork suite
- [Researcher](https://github.com/TimSimpsonJr/researcher): gather sources into cited notes
- [Magpie](https://github.com/TimSimpsonJr/magpie): analyze FOIA/data into findings
- [Librarian](https://github.com/TimSimpsonJr/librarian): organize findings into linked vault notes (shared layer)
- [Copydesk](https://github.com/TimSimpsonJr/copydesk): write findings up in your voice

## License

MIT
