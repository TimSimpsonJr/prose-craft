# Collecting Writing Samples

This guide covers how to gather your own writing samples for voice extraction.

## What Counts as a Sample

Any writing you produced naturally: reddit comments, blog posts, emails, slack messages, forum posts, social media, essays, documentation. The key requirement is that you wrote it yourself, without AI editing or heavy revision by others.

Casual writing is often better than polished writing. It captures your natural voice, the patterns you fall into without thinking about them.

## How Many Samples

- 10-20 samples per register
- Aim for 3,000-5,000 total words across all samples for a register
- More is generally better, but returns diminish past 20 samples

## What to Look For

Collect representative samples, not your best work. You want how you actually write, not how you write on your best day.

Mix different topics within the same register. This helps the extraction focus on voice rather than subject matter.

Include samples where you're doing different things: explaining something, arguing a point, reacting to something, sharing something. Variety in purpose helps the extraction isolate voice features from content features.

## Registers

If you write noticeably differently in different contexts (casual comments vs. professional articles, personal essays vs. advocacy writing), collect separate sample sets. Each set becomes a register with its own voice feature description.

Most people need 1-2 registers. Don't over-split. If two contexts sound similar when you read them back, use one register.

## Anonymization

This step matters more than it sounds.

Strip usernames, subreddit names, platform names, dates, and any identifying metadata. Label each sample "Sample 1" through "Sample N."

Why: the extraction model can anchor on content, topic, or platform context instead of analyzing how you write. Stripping context forces it to focus on voice features, things like sentence structure, vocabulary choices, and rhetorical moves.

Extractions run on labeled, contextual samples produce noticeably worse feature descriptions. The model latches onto what you're talking about instead of how you talk.

## Format

- Plain text, one sample per block
- Separate samples with a blank line and the label (Sample 1, Sample 2, etc.)
- No need to preserve formatting from the original platform

Example structure:

```
Sample 1

Your first writing sample goes here. Plain text, no special formatting needed.

Sample 2

Your second writing sample goes here.
```
