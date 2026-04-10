# prose-craft

A Claude Code plugin that writes in your voice.

## What this does

Prose-craft extracts your distinctive writing patterns from samples of your own writing and uses them to generate text that sounds like you, not like AI. It uses a modular register system, so you can have different voices for different contexts (personal essays vs. advocacy copy, for example), and a dual review gate that catches AI patterns and evaluates craft depth before you see the output.

## Quick start

1. Clone this repo
2. Follow the setup process in `setup/extraction-guide.md` to create your voice registers (~30 minutes, requires Claude Sonnet access)
3. Test it out: `claude --plugin-dir /path/to/prose-craft`
4. When satisfied, install permanently using Claude Code's plugin management features

## How it works

- The skill detects which register to use based on what you're writing.
- It loads your voice feature description from the matching register file.
- After generating text, it dispatches two review agents in parallel:
  - **Prose review:** checks for AI patterns, banned phrases, and voice drift against your register features.
  - **Craft review:** evaluates naming opportunities, endings, dwelling, literary devices, and human-moment anchoring.
- Hard fails (banned phrases, AI vocabulary) are fixed automatically. Everything else is presented as an advisory table for you to accept, reject, or modify.

## Setup

See `setup/extraction-guide.md` for the full walkthrough. The process takes about 30 minutes and requires Claude Sonnet access. You'll gather writing samples, run two extraction passes, and end up with one or more register files that capture your voice.

## File structure

```
prose-craft/
  .claude-plugin/plugin.json     # Plugin manifest
  skills/prose-craft/SKILL.md    # Main skill: register detection, craft rules, review gate
  agents/
    prose-review.md              # AI pattern detection, banned phrases, voice drift
    craft-review.md              # Naming, endings, dwelling, literary devices
  registers/
    register-template.md         # Template for creating voice registers
  setup/
    extraction-guide.md          # End-to-end setup walkthrough
    sample-collection.md         # How to gather your writing samples
    pass-1-prompt.md             # Voice extraction prompt (broad)
    pass-2-prompt.md             # Voice extraction prompt (pressure test)
```

## License

MIT
