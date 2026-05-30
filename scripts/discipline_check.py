"""Deterministic discipline-check: the objective half of the prose-craft outcome gate.

Counts banned-construction violations in a markdown/prose file. In ``--diff`` mode it
reports whether a rewrite INTRODUCED a new violation (a count going up for any check),
which closes the hole where a silent auto-rewrite could sneak in a banned construction.

This script intentionally covers only the four MECHANICAL checks below. The semantic
"fatal pattern" ("not X, it's Y" and variants) is handled by a separate LLM re-checker.

Checks:
  em_dash        em dashes (the literal character, or a bare "--" not inside a longer run)
  caps_phrase    two or more consecutive ALL-CAPS words used for emphasis. A run made up
                 ENTIRELY of known acronyms (e.g. "SC ALPR", "SC FOIA") is an initialism,
                 not emphasis, and is NOT counted. Extend CAPS_ALLOWLIST for new acronyms.
  colon_inline   a colon followed by inline elaboration (a colon introducing a list is fine)
  banned_phrase  literal banned phrases from banned_phrases.txt (boundary-aware, case-insensitive)

Counting runs on PROSE only: YAML frontmatter, fenced code blocks, <script> blocks
(e.g. JSON-LD), and markdown heading lines are stripped first, so a piece's metadata
and embedded markup don't masquerade as prose violations. (Stripping is symmetric in
--diff mode, so it never affects whether a rewrite "introduced" a violation.)
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

# An all-caps run composed ONLY of these is an acronym/initialism, not emphasis, so it is
# not counted as a caps_phrase violation. Tuned against the advocacy corpus (SC ALPR, SC
# FOIA, SLED, ...); extend as new domain acronyms surface.
CAPS_ALLOWLIST = {
    "SC", "US", "USA", "EU", "UK", "NY", "DC",
    "ALPR", "ALPRS", "LPR", "SLED", "SCDOT", "DMV", "CCTV", "GPS",
    "FOIA", "PII", "SSN", "DUI", "SWAT", "VPN",
    "FBI", "DEA", "ICE", "CBP", "NSA", "DHS", "DOJ", "IRS", "AG", "DA",
    "AI", "SAAS", "API", "URL", "HTML", "JSON", "PDF", "FAQ",
    "HOA", "NGO", "CEO", "CTO", "PR", "TV", "ID",
}

_CAPS_RUN = re.compile(r"\b[A-Z]{2,}(?:\s+[A-Z]{2,})+\b")
_FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
_FENCED = re.compile(r"```.*?```", re.DOTALL)
_SCRIPT = re.compile(r"<script[^>]*>.*?</script>", re.DOTALL | re.IGNORECASE)
_HEADING = re.compile(r"(?m)^\s{0,3}#{1,6}\s.*$")


def _strip_nonprose(text: str) -> str:
    """Remove non-prose regions so metadata/markup don't count as prose violations."""
    text = _FRONTMATTER.sub("", text, count=1)
    text = _FENCED.sub("", text)
    text = _SCRIPT.sub("", text)
    text = _HEADING.sub("", text)
    return text


def _caps_phrase_count(text: str) -> int:
    """Consecutive ALL-CAPS words used for emphasis; runs of only acronyms don't count."""
    count = 0
    for run in _CAPS_RUN.findall(text):
        if all(tok.upper() in CAPS_ALLOWLIST for tok in run.split()):
            continue  # initialism run (e.g. "SC ALPR"), not vocal-stress emphasis
        count += 1
    return count


def count_violations(text: str) -> dict:
    text = _strip_nonprose(text)
    caps_phrase = _caps_phrase_count(text)
    em_dash = text.count("—") + len(re.findall(r"(?<!-)--(?!-)", text))
    colon_inline = len(re.findall(r":\s+(?![\n\-\*\d])", text))
    low = text.lower()
    banned_phrase = sum(
        len(re.findall(r"(?<!\w)" + re.escape(p) + r"(?!\w)", low)) for p in BANNED
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
