# Pass 1: Voice Feature Extraction

This prompt extracts your distinctive voice features by comparing your writing against Claude's default output. The comparison highlights what makes your writing yours, rather than what makes writing generically good.

## How to use

1. **Generate baseline samples (P1).** In a fresh Claude conversation, ask it to write 10 short pieces (150-300 words each) on topics similar to your writing samples. Use simple prompts with no style instructions: "Write a short comment about [topic]." or "Write a brief post about [topic]." These baseline samples show what Claude sounds like without any voice guidance.

2. **Run the extraction.** Paste the prompt below into a new Claude Sonnet conversation, filling in the P1 and P2 sections with your samples.

## What you get

A voice feature description organized into four sections (vocabulary, sentence structure, rhetorical techniques, voice qualities) that you will refine in pass 2.

---

## Prompt

```
Here are writings from two sources, P1 and P2:

P1 writings:
[Paste your 10 Claude baseline samples here]

P2 writings:
[Paste your anonymized writing samples here]

Compare P1 and P2. Describe the distinctive features of P2's writing that P1 lacks. Organize your analysis into four sections:

1. **Vocabulary** — word choices, register, domain terminology usage, how formal/informal language is deployed, what kinds of words P2 reaches for that P1 doesn't
2. **Sentence Structure** — sentence length patterns, clause construction, use of fragments, parenthetical asides, how sentences begin and end, rhythm and pacing
3. **Rhetorical Techniques** — how arguments are built, how evidence is used, how the writer persuades or explains, structural moves, relationship between claims and examples
4. **Voice Qualities** — personality, tone, relationship to reader, emotional register, what makes this voice recognizable as a specific person rather than generic competent writing

For each section, write operational instructions that could be followed to reproduce these patterns. Frame each feature as "do X" or "when Y, do Z" rather than "tends to use" or "often employs." Be specific enough that following these instructions would produce writing distinguishable from P1.

Focus on structural and stylistic features, not content or topic. Do not quote specific passages from the samples. Describe the patterns and moves, not the subject matter.
```
