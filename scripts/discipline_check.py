"""Deterministic discipline-check: the objective half of the prose-craft outcome gate.

Counts banned-construction violations in a markdown/prose file. In ``--diff`` mode it
reports whether a rewrite INTRODUCED a new violation (a count going up for any check),
which closes the hole where a silent auto-rewrite could sneak in a banned construction.

This script intentionally covers only the four MECHANICAL checks below. The semantic
"fatal pattern" ("not X, it's Y" and variants) is handled by a separate LLM re-checker.

Checks:
  em_dash        em dashes (the literal character, or a bare "--" not inside a longer run)
  caps_phrase    two or more consecutive ALL-CAPS words (a single one is allowed advocacy)
  colon_inline   a colon followed by inline elaboration (a colon introducing a list is fine)
  banned_phrase  literal banned phrases from banned_phrases.txt (substring, case-insensitive)
"""

import json
import pathlib
import re
import sys

BANNED = [
    line.strip().lower()
    for line in (pathlib.Path(__file__).parent / "banned_phrases.txt")
    .read_text(encoding="utf-8")
    .splitlines()
    if line.strip()
]


def count_violations(text: str) -> dict:
    caps_phrase = len(re.findall(r"\b[A-Z]{2,}(?:\s+[A-Z]{2,})+\b", text))
    em_dash = text.count("—") + len(re.findall(r"(?<!-)--(?!-)", text))
    colon_inline = len(re.findall(r":\s+(?![\n\-\*\d])", text))
    low = text.lower()
    banned_phrase = sum(low.count(p) for p in BANNED)
    return {
        "em_dash": em_dash,
        "caps_phrase": caps_phrase,
        "colon_inline": colon_inline,
        "banned_phrase": banned_phrase,
    }


def introduced_new_violation(before: str, after: str) -> bool:
    b, a = count_violations(before), count_violations(after)
    return any(a[k] > b[k] for k in a)


if __name__ == "__main__":
    if sys.argv[1] == "--diff":
        before = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")
        after = pathlib.Path(sys.argv[3]).read_text(encoding="utf-8")
        print(
            json.dumps(
                {
                    "counts": count_violations(after),
                    "introduced_new": introduced_new_violation(before, after),
                }
            )
        )
    else:
        text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
        print(json.dumps(count_violations(text)))
