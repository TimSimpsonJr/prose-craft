# prose-craft

A Claude Code plugin that writes in your voice.

## What this does

Prose-craft extracts your distinctive writing patterns from samples of your own writing and uses them to generate text that sounds like you, not like AI. It uses a modular register system, so you can have different voices for different contexts (personal essays vs. advocacy copy, for example), and a dual review gate that catches AI patterns and evaluates craft depth before you see the output.

## Installation

Paste this repo's URL into the Claude Code desktop app:

```
https://github.com/TimSimpsonJr/prose-craft
```

Claude Code will install it as a plugin automatically. You can also install from the CLI:

```bash
/install-plugin https://github.com/TimSimpsonJr/prose-craft
```

## Quick start

1. Install the plugin (see above)
2. Run `/prose-craft-init` — the init skill creates `~/.claude/data/prose-craft/`, copies the starter template, and walks you through extracting your first voice register (~30 minutes, requires Claude Sonnet access). Re-run any time to add a new register.
3. Once at least one register is configured, `/prose-craft` activates automatically whenever you ask Claude to write text for outside consumption.

Your personal data (registers, accumulator, snapshots) lives at `~/.claude/data/prose-craft/` and is invariant under plugin updates — feel free to update the plugin from the marketplace without worrying about losing your voice extractions.

## How it works

### Registers

A register is a voice profile for a specific kind of writing. You might have one for casual posts and another for professional articles. Each register contains a voice feature description extracted from your own writing samples, organized into four sections: vocabulary, sentence structure, rhetorical techniques, and voice qualities.

When you ask Claude to write something, the skill detects which register fits the context and loads that register's voice features as the primary writing instructions.

### Craft rules

On top of your voice features, the skill applies a shared set of architectural craft rules:

- **Concrete-first:** lead with a person, a number, a scene, or a specific object. Abstraction is earned, never assumed.
- **Opening moves:** every piece starts with a deliberate first move (arresting fact, person in a situation, specific scene, counterintuitive claim, or confession).
- **Naming:** when introducing a pattern or concept, name it in 2-4 words. Named concepts travel. Unnamed concepts don't.
- **Structural unpredictability:** vary paragraph and section architecture deliberately. Never settle into a rhythm a compression algorithm could predict.

It also enforces a banned phrase list that catches common AI writing patterns (em dashes, "delve," "it's important to note," the "this isn't X, this is Y" construction, and others).

### Review gate

After generating text, the skill dispatches two review agents in parallel before you see the output:

**Prose review** checks for:
- Banned phrases and AI vocabulary (hard fails, fixed automatically)
- Voice drift against your register's feature description
- Structural monotony (repeated sentence architecture, uniform paragraph length)
- Missing self-correction, grounding, or personality

**Craft review** evaluates:
- Naming opportunities (patterns described but not labeled)
- Aphoristic destinations (does the piece end on a sentence that travels?)
- Central-point dwelling (does the piece give disproportionate space to its load-bearing point?)
- Structural literary devices (metaphors that carry argumentative weight, not decoration)
- Human-moment anchoring (abstractions grounded in specific people or scenes)

Hard fails are fixed before you see the text. Everything else comes back as advisory tables from each agent.

**Prose review advisory table:**

| # | Line | Pattern | Current | Proposed fix |
|---|------|---------|---------|--------------|
| 1 | "Furthermore, the committee decided..." | Mid-tier AI vocabulary | "Furthermore" is a dead AI transition | Cut it. Start the sentence at "The committee decided..." |
| 2 | "This is important because..." | Frictionless transition | 4 transitions in a row and none of them feel abrupt | Drop the transition. Start the next paragraph mid-thought and let the reader fill the gap. |
| 3 | "The system was efficient. The system was fast. The system was reliable." | Structural monotony | 3 sentences in a row with the same shape | Vary: "The system was efficient. Fast, too. But reliable is the word that kept showing up in the post-mortems." |

**Craft review advisory table:**

| Dimension | Rating | Notes | Proposed improvement |
|-----------|--------|-------|---------------------|
| Naming | Opportunity | "The policy created a strange dynamic where everyone pretends the rules matter" describes a pattern in 2 sentences but never labels it | Name it: "compliance theater" — compresses the dynamic into something portable |
| Aphoristic destination | Opportunity | Piece ends with "This matters because it affects everyone" — a generic summary that could close any article | End on the mechanism: "Four inspectors for 2,000 facilities. A confession dressed up as a staffing decision." |
| Central-point dwelling | Strong | Enforcement failure gets too much of the piece on purpose and comes back twice. That's the right call. | |
| Structural literary devices | Opportunity | Nothing in here is doing double duty. Every sentence means one thing and stops. | The committee lifecycle ("conversation → process → ritual") could structure the whole analysis instead of sitting in one paragraph |
| Human-moment anchoring | Strong | Opens with one inspector walking into one facility. The abstraction earns its space after that. | |

You accept, reject, or modify each row individually.

### Learning from your edits

After you manually edit a piece that was generated with prose-craft, invoke `/prose-craft-learn` to analyze what you changed. The skill captures three snapshots during the writing process (after review agents run, after you accept/reject advisories, and after your manual edits), then dispatches a learning agent that diffs the snapshots and proposes improvements to your register, skill rules, or review agents.

Observations that don't have enough evidence yet get stored in an accumulator file. Over multiple pieces, patterns accumulate until they cross the evidence threshold and get promoted to concrete rule changes. Observations that stop recurring go stale and get cleaned up automatically.

The learning loop is the fastest way to sharpen your voice registers after the initial extraction. Every piece you write and edit teaches the system something.

## Setup

Run `/prose-craft-init` after installing the plugin. The init skill walks you through extraction interactively. The process takes about 30 minutes and requires Claude Sonnet access — you'll gather writing samples, run two extraction passes, and end up with a register file at `~/.claude/data/prose-craft/registers/<name>.md` that captures your voice (with `triggers:` frontmatter declaring the contexts that activate it).

For a top-down look at the manual process underneath the init skill — useful if you want to understand what's happening or run it by hand — see `setup/extraction-guide.md`.

## File structure

```
prose-craft/                          # The plugin (this repo, shipped via marketplace)
  .claude-plugin/plugin.json          # Plugin manifest
  skills/
    prose-craft/SKILL.md              # Main skill: register detection (frontmatter-based), craft rules, review gate
    prose-craft-learn/SKILL.md        # Learning skill: snapshots, analysis, accumulator
    prose-craft-init/SKILL.md         # First-run setup + extraction walkthrough
  agents/
    prose-review.md                   # AI pattern detection, banned phrases, voice drift
    craft-review.md                   # Naming, endings, dwelling, literary devices
    learn-review.md                   # Diff analysis, pattern extraction, rule proposals
  template-data/                      # Read-only starter content (copied to ~/.claude/data/ on first run)
    registers/register-template.md
    learning/accumulator.md
  setup/                              # Reference prompts and guides
    extraction-guide.md
    sample-collection.md
    pass-1-prompt.md
    pass-2-prompt.md
    brief-stripping-guide.md

~/.claude/data/prose-craft/           # Your personal data (NOT in this repo; survives plugin updates)
  registers/                          # Your voice registers with triggers: frontmatter
  learning/
    accumulator.md                    # Accumulated observations
    snapshots/                        # Per-piece snapshots
    extraction-artifacts/             # Pass-1/pass-2 outputs from each extraction run
    pending-upstream.md               # Queue of plugin-code edits the learning loop wants to upstream via PR
```

## License

MIT
