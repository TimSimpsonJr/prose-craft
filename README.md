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
2. Follow the setup process in `setup/extraction-guide.md` to create your voice registers (~30 minutes, requires Claude Sonnet access)
3. Once your registers are configured, the skill activates automatically whenever you ask Claude to write text for outside consumption

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

See `setup/extraction-guide.md` for the full walkthrough. The process takes about 30 minutes and requires Claude Sonnet access. You'll gather writing samples, run two extraction passes, and end up with one or more register files that capture your voice.

## File structure

```
prose-craft/
  .claude-plugin/plugin.json          # Plugin manifest
  skills/
    prose-craft/SKILL.md              # Main skill: register detection, craft rules, review gate
    prose-craft-learn/SKILL.md        # Learning skill: snapshots, analysis, accumulator
  agents/
    prose-review.md                   # AI pattern detection, banned phrases, voice drift
    craft-review.md                   # Naming, endings, dwelling, literary devices
    learn-review.md                   # Diff analysis, pattern extraction, rule proposals
  registers/
    register-template.md              # Template for creating voice registers
  learning/
    accumulator.md                    # Persistent observations across sessions
    snapshots/                        # Temporary snapshot files (cleaned up after learning)
  setup/
    extraction-guide.md               # End-to-end setup walkthrough
    sample-collection.md              # How to gather your writing samples
    pass-1-prompt.md                  # Voice extraction prompt (broad)
    pass-2-prompt.md                  # Voice extraction prompt (pressure test)
```

## License

MIT
