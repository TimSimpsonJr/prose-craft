from scripts.discipline_check import count_violations, introduced_new_violation


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
