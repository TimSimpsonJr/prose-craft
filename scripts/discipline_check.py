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
  banned_phrase  literal banned phrases from banned_phrases.txt (word-boundary, case-insensitive)
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
    banned_phrase = sum(
        len(re.findall(r"\b" + re.escape(p) + r"\b", low)) for p in BANNED
    )
    return {
        "em_dash": em_dash,
        "caps_phrase": caps_phrase,
        "colon_inline": colon_inline,
        "banned_phrase": banned_phrase,
    }


def introduced_new_violation(before: str, after: str) -> bool:
    b, a = count_violations(before), count_violations(after)
    return any(a[k] > b[k] for k in a)


USAGE = "usage: discipline_check.py <file> | discipline_check.py --diff <before> <after>"


def _read(path: str) -> str:
    """Read a file, or print a uniform JSON error to stdout and exit 1 if missing."""
    try:
        return pathlib.Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        print(json.dumps({"error": f"file not found: {path}"}))
        sys.exit(1)


def main(argv: list) -> None:
    if len(argv) < 1:
        print(USAGE, file=sys.stderr)
        sys.exit(2)
    if argv[0] == "--diff":
        if len(argv) < 3:
            print(USAGE, file=sys.stderr)
            sys.exit(2)
        before = _read(argv[1])
        after = _read(argv[2])
        print(
            json.dumps(
                {
                    "counts": count_violations(after),
                    "introduced_new": introduced_new_violation(before, after),
                }
            )
        )
    else:
        print(json.dumps(count_violations(_read(argv[0]))))


if __name__ == "__main__":
    main(sys.argv[1:])
