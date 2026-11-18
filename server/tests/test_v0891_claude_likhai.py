"""v0.891 CLAUDE JAISA LIKHAI: the model is told how a reply looks, the way Claude's apps draw it - real `##`
headings for a long answer (never a bold line as a heading), bold only on list-item openers or one figure, tables
of at most 3 short columns, sources as links at the end, code fenced with its language. Both reply rulebooks (the
small live prompt and the long one) carry the same rules, and the small prompt stays under its size limit."""
from app.agent import core_prompt as cp
from app.agent import replystyle

RULES = ["## ", "### ", "Never a whole bold line", "at most 3 columns", "up to 4 words", "units in the header",
         "Sources at the end as links", "fenced block with the language named", "opening words of a list item"]


def test_small_prompt_carries_the_look_rules():
    core = cp.core_prompt("default", True)
    for r in RULES:
        assert r in core, r
    assert "How your words look" in core
    assert len(core) < 10500, len(core)         # the whole system prompt must stay < 12,000 with her chat block


def test_long_rulebook_says_the_same():
    t = replystyle.CHAT
    for r in ["`## ` heading per part", "never a whole bold line", "at most 3 columns", "up to 4 words",
              "units in the header", "sources at the end as markdown links", "fenced block with the language named"]:
        assert r in t, r
    assert "{" not in replystyle.CHAT and "}" not in replystyle.CHAT    # voice.PERSONA .format()s these strings


def test_plain_still_strips_the_new_marks():
    s = replystyle.plain("## Apple\n\n| Source | Revenue |\n|---|---|\n| iPhone | $196.5B |\n\nSources: [apple.com](https://apple.com)")
    assert "##" not in s and "---" not in s and "apple.com (https://apple.com)" in s
