# Pass 2: Pressure Test

This prompt refines the voice feature description produced by pass 1. It pressure-tests each feature against your original samples, sharpens vague descriptions into specific ones, removes features that any competent writer would have, and catches patterns pass 1 missed.

## How to Use

Open a Claude Sonnet conversation (the same one you used for pass 1, or a new one). Paste the prompt template below, filling in both bracketed sections with your pass-1 output and your original writing samples.

The output replaces your pass-1 description. Paste it directly into your register file.

## Prompt Template

```
Here is a voice feature description extracted from a writer's samples:

[Paste your pass-1 output here]

And here are the original writing samples it was extracted from:

[Paste your anonymized writing samples here]

Pressure-test this feature description:

1. **Specificity check:** Which features are genuinely distinctive to this writer vs. things any competent human writer does? A feature like "varies sentence length" is too generic — every decent writer does that. A feature like "alternates between 3-word fragments and 30-word accumulative sentences where each clause adds another concrete detail" is specific enough to be useful. Remove or sharpen anything too generic to distinguish this writer from a skilled baseline.

2. **Completeness check:** Reread the samples looking for patterns the first pass missed. Pay special attention to:
   - How the writer handles uncertainty, disagreement, or being wrong
   - Characteristic opening and closing moves
   - How parenthetical asides or mid-sentence qualifications function (do they anticipate objections? subvert the sentence? add context?)
   - Rhythm patterns at the paragraph level (not just sentence level)
   - The writer's relationship to the reader (insider vs. explainer, peer vs. authority, formal vs. casual)
   - Any recurring structural moves that appear across multiple samples

3. **Operationality check:** For each feature, ask: could someone follow this instruction and actually reproduce this pattern? Rewrite any instruction that is descriptive ("uses varied sentence lengths") into an operational form ("alternate between fragments of 3-5 words and accumulative sentences of 25+ words that add concrete detail with each clause"). The test: if you handed these instructions to a language model, would the output sound noticeably different from its default?

Output the revised feature description in the same four-section format (Vocabulary, Sentence Structure, Rhetorical Techniques, Voice Qualities). This output replaces the pass-1 description. Paste it into your register file.
```
