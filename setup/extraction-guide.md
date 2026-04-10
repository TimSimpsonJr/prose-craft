# Voice Extraction Guide

## What this does

The extraction process analyzes your writing to produce a voice feature description. The prose-craft skill uses this description to generate text that sounds like you instead of like AI. The whole process takes about 30 minutes.

## Before you start

- You need 10-20 samples of your own writing. See `sample-collection.md` for details on what to collect and how to prepare them.
- You need access to Claude (Sonnet). The extraction prompts are designed for Sonnet.

## Step-by-step process

### Step 1: Identify your writing contexts

What kinds of writing do you do? Casual comments, professional articles, advocacy writing, technical documentation, personal essays? Each context where you have a noticeably different voice becomes a register. Most people need 1-2 registers. Don't over-split: if two contexts sound similar when you read them back, use one register.

### Step 2: Collect samples

Follow the instructions in `sample-collection.md`. Collect a separate set of 10-20 samples for each register you identified.

### Step 3: Generate Claude baseline samples

Open a Claude conversation (no special instructions, no system prompt) and ask it to write 10 short pieces (150-300 words each) on topics similar to your writing samples. Use simple prompts like "Write a short comment about [topic]" or "Write a brief post about [topic]." These become your P1 (baseline) samples. Save them.

Why: the extraction works by comparing your writing against Claude's default output. The baseline samples establish what Claude sounds like without voice guidance, so the extraction can identify what makes your writing different.

### Step 4: Run pass-1 extraction

Open a new Claude Sonnet conversation. Paste the prompt from `pass-1-prompt.md`, filling in the P1 section with your baseline samples and the P2 section with your anonymized writing samples. Save the output.

### Step 5: Run pass-2 pressure test

In the same or a new Sonnet conversation, paste the prompt from `pass-2-prompt.md` with your pass-1 output and your original writing samples. Save the output. This is your final voice feature description.

### Step 6: Create your register file

Copy `registers/register-template.md` to `registers/[your-register-name].md` (e.g., `registers/casual.md` or `registers/professional.md`). Open it and paste the relevant sections of your pass-2 output into the four sections (Vocabulary, Sentence Structure, Rhetorical Techniques, Voice Qualities).

### Step 7: Configure register detection in SKILL.md

Open `skills/prose-craft/SKILL.md` and find the Register Detection section. It contains an HTML comment with format instructions. Replace the comment with entries for your registers. Here's the format:

```markdown
**Casual** triggers: personal reflection, blog posts, comments, forum posts, exploring ideas, sharing opinions
→ Read `${CLAUDE_PLUGIN_ROOT}/registers/casual.md` and follow its voice feature description.

**Professional** triggers: articles, documentation, reports, proposals, formal writing, technical explanations
→ Read `${CLAUDE_PLUGIN_ROOT}/registers/professional.md` and follow its voice feature description.
```

Adjust the names, triggers, and file paths to match your registers. The trigger list tells the skill when to activate each register. If the writing context is ambiguous, the skill will ask you which register to use.

### Step 8: Install and test

Test the plugin:

```
claude --plugin-dir /path/to/prose-craft
```

Ask Claude to write something and see if the voice matches. If it doesn't, check your register file for vague features and re-run pass 2 with more specific instructions.

## What good output looks like

Not all extraction output is equally useful. The difference between good and bad features is specificity: good features are concrete enough that following them would produce writing distinguishable from Claude's default. Bad features describe things any competent writer does.

**Good (specific, operational):**

- "Build long sentences through accumulation rather than subordination, where each clause adds another concrete detail to the pile"
- "Use profanity as punctuation at moments of highest analytical precision, not as filler"
- "Deploy a parenthetical when a claim invites a specific follow-up question or objection; the parenthetical heads it off without breaking the sentence's flow"

**Bad (vague, generic):**

- "Uses varied sentence lengths and structures"
- "Writes with authenticity and personality"
- "Employs rhetorical techniques effectively"

If your output reads like the "bad" column, re-run pass 2 with more samples or more varied topics.

## Troubleshooting

**Output is too generic.** Add more samples, add more variety in topics and contexts, and make sure you're using natural/casual writing rather than heavily polished pieces.

**Output focuses on content instead of craft.** Check your anonymization. If samples still contain platform names, usernames, or strong topical signals, the model anchors on content rather than voice patterns.

**Registers sound too similar.** Your voice may not actually differ much across these contexts. Consider merging into one register. It's better to have one strong register than two weak ones.

**Output doesn't match your voice when tested.** Re-read your samples and the extraction side by side. Is the extraction missing your most distinctive patterns? Run pass 2 again, explicitly calling out what was missed.
