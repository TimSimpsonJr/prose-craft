# Brief-Stripping Guide

The generative gate regenerates a held-out brief under two skill-states (current vs. edited) and asks which output is more in-register. For that comparison to mean anything, the brief must be **stripped of skill-encoding** first.

## Why strip

A deflocksc design doc is a *thick* brief: it carries the task (facts, argument, audience) **and** a copy of the skill's own decisions (voice rules, pre-named concepts, paragraph-by-paragraph prose direction). Two problems if you regenerate from the thick brief as-is:

1. **The edit's effect shrinks to nothing.** If the brief already dictates the voice and the structure, both skill-states produce nearly the same output, so the gate can't see what the candidate edit changed. Low signal.
2. **An embedded *old* voice rule contradicts an *edited* register.** The brief's "Voice and Style" section is a snapshot of the register at writing time. If your candidate edit changes that register, the brief now fights the edit: the generator gets two conflicting instructions and the comparison is corrupted.

So: keep the substance, strip the skill-encoding. What remains is a brief that tells the writer *what to say and to whom*, and lets the skill decide *how*.

## What to strip (skill-encoding)

- **The voice/style section.** Any block that restates register rules (sentence construction, punctuation bans, vocabulary bans, deictic-pronoun preferences, caps rules). This is exactly what the gate varies.
- **Pre-named concepts.** If the brief hands over a finished name ("call it the X Trap", "named concept: Y"), the skill never gets tested on whether it *produces* a good name. Strip the name; keep the underlying mechanism it was naming.
- **Paragraph-level prose direction.** Beat-by-beat breakdowns with word counts, "open on a scene," "merge short declaratives," "build long sentences through accumulation," "end the section on the pattern, not the evidence." These are generation/craft moves the skill owns.

## What to keep (substantive task content)

- **Purpose and audience.** Who's reading, what they know, what action the piece should drive.
- **The argument.** The actual claim and its load-bearing logic (e.g. "this bill codifies the worst practices; four amendments close the gap").
- **The facts.** People, dates, numbers, quotes, statutory text, case specifics, sources to cite. Verbatim where precision matters.
- **Messaging substance.** Strategic constraints that are about *argument*, not *voice* ("don't demonize the sponsor", "cite the Colorado incident", "use the bipartisan frame briefly").

## The gray area (rule of thumb)

Some lines are both. "Acknowledge the capture-adjacent dynamic without using 'regulatory capture'" is an argument constraint (keep) that also pre-names by exclusion (the naming part is skill territory). When a line mixes substance and encoding, **keep the substance and delete the encoding clause.**

The test: *would this line still belong in the brief if a different writer with a different voice were writing the piece?* If yes, it's substance (keep). If it only makes sense as an instruction to *this* skill's voice, it's encoding (strip).

## Worked example: the S.447 design doc

Source: `deflocksc-website/docs/plans/2026-04-24-s447-post-design.md`.

| Section | Classify | Why |
|---|---|---|
| Purpose, Audience | **Keep** (minus "Unique angle: the codification trap") | Who/what/why is substance; the "unique angle" line pre-names. |
| Central Argument | **Keep** | The actual claim and leverage logic. |
| Structure (P1-P5 beats, word counts) | **Strip the prose direction, keep the facts** | "P1: the Colorado scene, Gilliam, 4 kids, $1.9M settlement" — keep the facts, drop "~100 words, grounded, no political framing yet." |
| Section 2 contents (S.447 specifics, the silences, §23-1-235(D)(1) verbatim text) | **Keep** | Facts and statutory text. |
| "Named concept opportunity: authorization by omission" | **Strip** | Pre-named concept. Keep the mechanism (silence reads as permission); let the skill name it. |
| Section 3 "Call it the **Codification Trap**" | **Strip the name, keep the mechanism** | "a bill that regulates visibly while authorizing structurally" is the substance; the 2-word label is skill output. |
| The Four Amendments (contents of each) | **Keep** | Substantive policy detail. |
| Messaging Constraints 1-6 | **Keep** | Argument strategy. |
| Messaging Constraint 7 ("Codification trap is the named concept, not regulatory capture") | **Keep the substance, strip the naming directive** | "don't assert regulatory capture, no documented lobbying trail" is substance; "Codification trap is the named concept" is encoding. |
| **Voice and Style** (the whole section) | **Strip entirely** | Verbatim advocacy-register rules + banned-pattern lists. This is the register, which the gate varies. |
| Sources to Cite, Verification facts | **Keep** | Facts. |
| Frontmatter, Visual Elements, Related Technical Work | **Drop** (not voice, not argument) | Site-build mechanics, irrelevant to a prose regeneration. |

**Sketch of the stripped S.447 brief** (what a generation sub-agent would receive):

> Write an urgent call-to-action blog post for cold readers arriving from social media who know "Flock cameras track you" but nothing about S.447. Drive constituent contact with SC state senators before the session ends May 14, 2026.
>
> Argument: for most legislation a weak version sets a floor advocacy can build from; S.447 is the rare exception. It would be SC's first ALPR law and would codify the worst practices of the current unregulated system. Four floor amendments close the gap; constituent contact in the next three weeks is the highest-leverage action.
>
> Cover: the Colorado/Brittney Gilliam wrongful-detention case (Aurora 2020, four kids, plate misread, $1.9M settlement) as the human anchor; what S.447 regulates (90-day retention, written policies, hot-list oversight, misdemeanor penalty, SCDOT permitting); what it leaves silent (cloud storage, AI vehicle ID, federal access, warrant requirement, audits, private right of action, exclusionary rule); the SLED clause §23-1-235(D)(1) verbatim ("including the operation and maintenance of an automatic license plate reader database by SLED") and how it answers the question SCPIF v. SLED was filed to force; the mechanism whereby visible regulation makes structural authorization harder to unwind; the four amendments (strike the SLED authorization, block federal access absent a warrant, require warrants for historical queries, cut retention 90→30).
>
> Constraints: lead with what strong regulation includes, not with opposition; don't demonize Sen. Adams (target the language and the silences); use the bipartisan frame briefly; don't assert "regulatory capture" (no documented lobbying trail).
>
> [Sources list appended verbatim.]

Notice what's gone: no voice rules, no "Codification Trap" handed over, no word-count beats. The skill must now produce the voice, the naming, and the structure itself — which is exactly what the candidate edit is being tested on.
