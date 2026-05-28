import json
import pathlib
import subprocess
import sys

from scripts.discipline_check import count_violations, introduced_new_violation

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "discipline_check.py"


def _run_cli(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )


def test_counts_em_dashes():
    assert count_violations("a — b — c")["em_dash"] == 2


def test_counts_caps_phrases_not_single_words():
    # a single ALL-CAPS word is allowed (it's an endorsed advocacy technique);
    # two or more in a row is a violation
    v = count_violations("Say NO today. This is REALLY BAD news.")
    assert v["caps_phrase"] == 1  # "REALLY BAD"


def test_colon_inline_elaboration_flagged_list_colon_ok():
    assert count_violations("The point: it works.")["colon_inline"] == 1
    assert count_violations("Three asks:\n- one\n- two")["colon_inline"] == 0


def test_banned_phrase_hit():
    assert count_violations("It's worth noting that delve is bad.")["banned_phrase"] >= 1


def test_introduced_new_violation_true_when_new_type_appears():
    assert introduced_new_violation("clean text", "now with an em — dash") is True


def test_introduced_new_violation_false_when_only_reduced():
    assert introduced_new_violation("em — dash here", "em dash gone") is False


def test_banned_phrase_uses_word_boundaries():
    # "harnessed" should NOT match the banned word "harness"
    assert count_violations("She harnessed it")["banned_phrase"] == 0
    # but a standalone "harness" should
    assert count_violations("harness the grid")["banned_phrase"] == 1


def test_banned_phrase_multiword_still_matches():
    assert count_violations("it's worth noting that this works")["banned_phrase"] == 1


def test_banned_phrase_with_trailing_punctuation_matches():
    # phrases ending in punctuation (e.g. "are you paying attention?") must still match;
    # a trailing \b after "?" would fail, so the matcher uses lookarounds
    assert count_violations("Are you paying attention?")["banned_phrase"] == 1


def test_cli_no_args_exits_2():
    result = _run_cli()
    assert result.returncode == 2


def test_cli_diff_missing_path_exits_2():
    result = _run_cli("--diff", str(SCRIPT))
    assert result.returncode == 2


def test_cli_nonexistent_file_exits_1_with_json_error():
    result = _run_cli("does_not_exist_12345.md")
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)
    assert "error" in payload


def test_cli_single_file_success_prints_counts(tmp_path):
    f = tmp_path / "sample.md"
    f.write_text("plain clean text", encoding="utf-8")
    result = _run_cli(str(f))
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert set(payload) == {"em_dash", "caps_phrase", "colon_inline", "banned_phrase"}


def test_cli_diff_success_prints_counts_and_introduced(tmp_path):
    before = tmp_path / "before.md"
    after = tmp_path / "after.md"
    before.write_text("clean text", encoding="utf-8")
    after.write_text("harness the grid", encoding="utf-8")
    result = _run_cli("--diff", str(before), str(after))
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert "counts" in payload and "introduced_new" in payload
    assert payload["introduced_new"] is True
