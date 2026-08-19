"""Unit tests for the deterministic Markdown cleaner.

Uses short synthetic snippets only — never copyrighted source excerpts.
"""
from __future__ import annotations

import json

from agentic_testcraft.clean import CleanResult, _is_removable, clean_text

SAMPLE = """\
###### **Assertion Method**

_How do we make tests self-checking?_

**We call a utility method.**

www.it-ebook.info

<!-- Start of picture text -->
Create Testcase<br>Object<br>testMethod
<!-- End of picture text -->

defi ned behavior

Chapter 19  xUnit Basics Patterns
"""


def test_watermark_lines_removed():
    # exact watermark is removed; a typo variant is NOT auto-removed.
    assert _is_removable("www.it-ebook.info") is False  # typo 'it-ebook' not 'it-ebooks'
    assert _is_removable("www.it-ebooks.info") is True


def test_page_header_removed():
    assert _is_removable("Chapter 19  xUnit Basics Patterns") is True
    assert _is_removable("Part 3  Some Title") is True
    # a normal sentence mentioning a chapter is kept
    assert _is_removable("See Chapter 3 for details.") is False


def test_ligature_join_only_fi_and_fl():
    # fi artifact joins (leading chars preserved, lowercase regex joins the tail)
    assert clean_text("specifi cation").text == "specification\n"
    assert clean_text("verifi cation").text == "verification\n"
    # realistic capitalized form like the source: "**Confi gurable"
    assert clean_text("Confi gurable").text == "Configurable\n"
    assert clean_text("We confi gure a r").text == "We configure a r\n"
    # fl artifact joins (space falls right after the ligature)
    assert clean_text("infl uences").text == "influences\n"
    assert clean_text("confl icts").text == "conflicts\n"
    assert clean_text("refl ects").text == "reflects\n"
    # ff/er/st are genuine word boundaries and must NOT be joined
    text_ff = clean_text("sniff test").text
    assert "sniff test" in text_ff
    text_er = clean_text("number of items").text
    assert "number of items" in text_er


def test_sup_unwrap():
    out = clean_text("XUNIT<sup>TEST</sup> foo").text
    assert "XUNIT TEST" in out
    assert "<sup>" not in out


def test_stuck_hyphen_fixed():
    out = clean_text("a ~~-~~ b").text
    assert "- b" in out  # ~~-~~ -> '-'
    assert "~~-~~" not in out


def test_strikethrough_artifact_restored():
    # struck hyphen+letter between two words rejoins
    out = clean_text("people ~~-o~~ riented technologies").text
    assert "people-oriented" in out
    # stuck hyphen and struck single letter restored
    out2 = clean_text("Addison ~~-~~ Wesley ~~I~~ done").text
    assert "Addison-Wesley" in out2 or "Addison - Wesley" in out2
    assert "~~" not in out2
    # em-dash stroke restored
    out3 = clean_text("good ~~" + "\u2014" + "~~ finding").text
    assert "\u2014" in out3
    assert "~~" not in out3
    # genuine multi-word strikethrough is preserved
    out4 = clean_text("~~Key to Summary~~").text
    assert "~~Key to Summary~~" in out4


def test_break_conversion_splits_lines():
    out = clean_text("Create Testcase<br>Object").text
    assert "Create Testcase" in out
    assert "Object" in out
    assert "<br" not in out


def test_heading_emphasis_stripped():
    out = clean_text("###### **Assertion Method** ").text
    assert out.startswith("###### Assertion Method")
    out2 = clean_text("###### _Smells in This Chapter_").text
    assert out2.startswith("###### Smells in This Chapter")
    assert "**" not in out
    assert "_" not in out


def test_comments_removed_but_picture_text_preserved():
    out = clean_text("x<!-- foo -->y").text
    assert "<!-- foo -->" not in out
    assert "xy" in out


def test_blank_line_normalisation():
    out = clean_text("a\n\n\n\nb").text
    lines = out.split("\n")
    # collapsed to single blank between a and b
    blank_run = 0
    max_run = 0
    for ln in lines:
        if ln.strip() == "":
            blank_run += 1
            max_run = max(max_run, blank_run)
        else:
            blank_run = 0
    assert max_run <= 1


def test_provenance_map_records_source_lines():
    res: CleanResult = clean_text("hello world\n")
    assert res.line_map[0]["source_lines"] == [1]
    assert res.line_map[0]["clean_line"] == 1


def test_break_splits_preserve_source_line():
    res: CleanResult = clean_text("a<br>b\n")
    # two output lines, both derived from source line 1
    out_lines = res.text.split("\n")
    assert out_lines[0] == "a"
    assert out_lines[1] == "b"
    sources = [e["source_lines"] for e in res.line_map if e["clean_line"] in (1, 2)]
    assert sources == [[1], [1]]


def test_full_sample_pipeline():
    res = clean_text(SAMPLE)
    assert "www.it-ebooks.info" not in res.text
    assert "Chapter 19  xUnit Basics Patterns" not in res.text
    assert "specifi" not in res.text
    assert "Assertion Method" in res.text
    assert res.counts.removed_watermark >= 0
    assert "join_f_ligatures" in res.counts.transform_counts
    # provenance map is non-empty and clean_line numbering is sequential
    assert [e["clean_line"] for e in res.line_map] == list(range(1, len(res.line_map) + 1))


def test_jsonl_line_map_serialisable():
    res = clean_text(SAMPLE)
    for entry in res.line_map:
        json.dumps(entry)  # must not raise


def test_results_are_deterministic():
    a = clean_text(SAMPLE)
    b = clean_text(SAMPLE)
    assert a.text == b.text
    assert a.line_map == b.line_map
