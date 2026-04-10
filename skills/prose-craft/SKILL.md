---
name: prose-craft
description: Use before writing ANY text for outside consumption — blog posts, articles, emails, social media, documentation aimed at readers, letters, advocacy copy, newsletter content. Produces engaging, human prose and runs a review gate on all output.
---

# Prose Craft

You are writing for a human audience. Every sentence should earn the next one.

## Register Detection

On invocation, determine which register to use from context:

<!-- 
Configure your registers here after running the extraction process.
See setup/extraction-guide.md for the format and a worked example.

Each register entry has three parts:
- A name
- Trigger contexts (what kind of writing activates this register)
- A file path to the register's voice feature description

Example format:

**[Register Name]** triggers: [comma-separated list of contexts]
→ Read `${CLAUDE_PLUGIN_ROOT}/registers/[name].md` and follow its voice feature description.
-->

**Ambiguous:** Ask the user which register to use.

The register's voice feature description is the primary voice instruction. The rules below (formatting, craft techniques, banned phrases) are shared across all registers and layer on top of the register's features.

## Source Material

When the user provides source material (conversation transcripts, research notes, outlines, links):

- Frame source material as raw inputs the writer is still thinking through, not content to summarize or report on.
- Write as if working through this material for the first time on the page, not reporting conclusions already reached.
- Rich context (conversation transcripts, research notes, detailed outlines) produces dramatically better output than topic sentences. If the user provides only a topic, ask if they have notes or context to share.

## Formatting

- Short paragraphs (1-3 sentences default).
- Numbers as digits.
- Contractions always.
- **NO em dashes ever.** Use commas, periods, colons, semicolons, or parentheses.
- When replacing em dashes, identify the function:
  - Parenthetical aside → use parentheses
  - Elaboration → use colon
  - Joining related clauses → use comma
  - Do NOT split into separate sentences (causes choppiness). Semicolons OK occasionally.
- Bold sparingly, 1-2 key moments per section.

## Craft Techniques

These architectural rules apply to both registers.

### Concrete-first

Lead with a person, a number, a scene, or a specific object. Abstraction is earned, never assumed. No more than 2 sentences of abstraction before grounding with a concrete example.

### Opening moves

Every piece needs a deliberate first move. Pick one:

**Arresting fact.** Drop the reader into something specific they didn't know.

**Person in a situation.** Start with someone doing something. The reader follows the person before they understand the argument.

**Specific scene.** Set a visual. Let the reader see it before you explain it.

**Counterintuitive claim.** State something that sounds wrong, then say you'll prove it.

**Confession.** Earn authority by admitting a failure first.

### Naming

When introducing a pattern or concept, name it in 2-4 words before explaining it. Named concepts travel. Unnamed concepts don't.

**How to find the name:** If you've described a dynamic, mechanism, or pattern in 2+ sentences without labeling it, stop. The name is hiding in the description. Look for what the thing does or what it feels like. The name compresses the description into something portable. If you can't name it, you might not understand it well enough yet.

**When to name:** Every piece longer than 300 words should name at least one thing. Not a throwaway label, but a genuine compression of the piece's central insight into a phrase readers can carry out and use in conversation.

**Make the name genuinely new.** The best names are phrases that have never appeared together before. Generic labels like "the accountability gap" or "the transparency problem" don't count. Those are category descriptions, not names. A good name surprises on first read and feels inevitable on second read.

### Structural unpredictability

Vary paragraph and section architecture deliberately. If your first paragraph is 3 sentences long, make the next one 1 sentence, or 5. Never write 3 consecutive paragraphs with the same sentence count or the same internal pattern.

Mix your moves within sections too. A paragraph that opens with a question, followed by one that opens with a concession, followed by one that opens with a concrete detail. Don't settle into a rhythm that a compression algorithm could predict.

Don't let transitions be too smooth either. Human writing has rough joins. Sometimes one paragraph just ends and the next one starts somewhere slightly different, and the reader fills in the gap. Let some joins be abrupt.

## Banned Phrases

### The fatal pattern (HARD FAIL)

- "This isn't X. This is Y." and ALL variations.
- Embedded: "The critical variable isn't X, it's Y"
- Split across sentences: "Culture isn't the wall. Incentives are the wall."
- "Not X. Y." fragments
- "Forget X. This is Y." / "Less X, more Y."
- "I don't mean X... I mean Y."
- ANY sentence where a negated framing is followed by a corrected one, regardless of punctuation or sentence boundaries.
- If even ONE of these appears, delete the negation and just state the positive claim.

### Em dashes (HARD FAIL)

Never, in any form. See formatting rules for replacements.

### AI vocabulary (HARD FAIL, fix silently)

- "In today's [anything]"
- "It's important to note" / "It's worth noting"
- "Delve" / "Dive into" / "Unpack"
- "Let that sink in" / "Read that again" / "Full stop"
- "Here's the part nobody's talking about" / "What nobody tells you"
- "I'd be happy to help"

### ChatGPT-isms (HARD FAIL, fix silently)

- "And you know what" / "and that matters"
- "Let's be honest here" / "let me be clear"
- "Here's the thing though" / "I'll say this"
- "Look," (as sentence opener for false emphasis)
- "Sit with" / "worth sitting with" / "sit with that" and all variants

## Review Gate

After generating text for outside consumption, dispatch both review agents before presenting the text to the user.

**How to dispatch:**

Use the Agent tool to launch TWO agents in parallel:

1. **Prose review agent** (model: sonnet):
   - `subagent_type`: "prose-craft:prose-review"
   - `prompt`: Include the generated text AND the active register's voice feature description (from the register file). The register features enable voice drift detection.
   - `description`: "Review prose for AI patterns"

2. **Craft review agent** (model: sonnet):
   - `subagent_type`: "prose-craft:craft-review"
   - `prompt`: Include the generated text.
   - `description`: "Review prose for craft depth"

Wait for both agents to return.

**Processing results:**

- **Hard fails** (banned phrases, fatal pattern, em dashes, ChatGPT-isms): fix these silently before presenting to user.
- **All other findings**: present in an advisory table below the text:

| # | Line | Pattern | Current | Proposed fix |
|---|---|---|---|---|
| 1 | [quote] | [pattern name] | [the current text] | [a proposed replacement] |

The user accepts, rejects, or modifies each row individually.
