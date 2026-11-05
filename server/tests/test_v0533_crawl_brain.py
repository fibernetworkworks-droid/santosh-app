"""v0.533 CRAWL BRAIN — the crawl4ai ideas, hand-built (the port law).

Owner read unclecode/crawl4ai and said "give this all to hoola ai". Zero upstream code: crawl4ai vendors a
fork of html2text, which upstream distributes under the GPLv3 with no header in the vendored copy, and
markdown generation runs through it on every crawl - the same reason crawl_jobs.py keeps Firecrawl's AGPL
engine out of this tree. So the ALGORITHMS are re-implemented from their published formulas and measured
here.

These tests pin the behaviour that the first implementations got WRONG, because each was a real bug:
  * the chrome gate must DROP a cookie banner / advert, not merely down-weight it (a 10% class signal left
    both of them in the kept text);
  * coverage must not be scored with BM25 (its idf collapses to ~0 when every page agrees, so the better
    the pages matched, the lower it scored - four pages stating the same GST rate never reached the bar);
  * consistency must use the overlap coefficient, not Jaccard (pages agreeing on every fact but differing
    in length scored ~0.33 for ever);
  * an off-topic link must not outrank an on-topic one on novelty alone.
"""
from __future__ import annotations

from app.crawl import enough as EN
from app.crawl.bm25 import BM25, words
from app.crawl.prune import as_text, bm25_blocks, is_chrome, prune

PAGE = """<html><body>
<div id="cookie-consent"><p>We use cookies to improve your experience. Accept all cookies to continue browsing our website today.</p></div>
<nav class="main-nav"><a href="/">Home</a><a href="/about">About</a><a href="/shop">Shop</a></nav>
<div class="sidebar widget"><h3>Trending</h3><ul><li><a href="/1">Ten tips</a></li><li><a href="/2">Best of</a></li></ul></div>
<article class="post-content">
  <h1>Sai Medical, Tilak Road, Akola</h1>
  <p>Sai Medical is a chemist on Tilak Road in Akola, open from nine in the morning until nine at night, every day including Sunday.</p>
  <p>They keep insulin refrigerated and will order anything they do not have within a day. The shop phone number is 0724 243 0000.</p>
</article>
<div class="promo-banner advert"><p>Buy now and save fifty percent on your first order with code SAVE50 today only</p></div>
<footer class="site-footer"><p>Copyright 2026 BigSite. All rights reserved. Privacy policy. Terms of service.</p></footer>
</body></html>"""


# ---------------------------------------------------------------- BM25, hand-built
def test_bm25_ranks_the_relevant_doc_first_and_keeps_hinglish():
    docs = [words("chemist medical store akola tilak road"), words("the quick brown fox"),
            words("akola chemist phone number")]
    bm = BM25(docs)
    s = bm.scores(words("akola chemist"))
    assert s[2] > s[0] > s[1] == 0.0
    assert sorted(bm.covered(words("akola chemist"))) == ["akola", "chemist"]
    # Hinglish carries the question on a Hoola ask; an English stop list must not eat it
    assert words("daam kitna hai kahan") == ["daam", "kitna", "hai", "kahan"]


def test_bm25_idf_is_never_negative():
    """A term in EVERY document must score ~0, not push a block down."""
    docs = [words("gst cement india"), words("gst cement india"), words("gst cement india")]
    assert min(BM25(docs).idf.values()) >= 0.0


# ---------------------------------------------------------------- item 2: what to cut
def test_chrome_is_dropped_not_merely_downweighted():
    kept = as_text(prune(PAGE)).lower()
    for junk in ("cookies", "trending", "save50", "all rights reserved", "about"):
        assert junk not in kept, f"boilerplate survived: {junk}"
    assert "0724 243 0000" in kept and "insulin" in kept


def test_a_content_word_vetoes_the_chrome_gate():
    from lxml import html as LH
    for cls, want in [("cookie-consent", True), ("advert", True), ("promo-banner advert", True),
                      ("ad-article", False), ("content-promo", False), ("post-content", False),
                      ("", False), ("sidebar-content", False)]:
        assert is_chrome(LH.fromstring(f'<div class="{cls}">x</div>')) is want, cls


def test_a_plain_page_with_no_markers_does_not_come_back_empty():
    plain = "<html><body>" + "".join(
        f"<div><p>Paragraph {i} about the price of cement in Akola, which moved by a rupee a bag.</p></div>"
        for i in range(5)) + "</body></html>"
    assert len(prune(plain)) >= 3


def test_an_all_chrome_page_comes_back_empty_rather_than_inventing_content():
    junk = ('<html><body><nav class="menu"><a href="/">a</a></nav>'
            '<div class="cookie-banner"><p>We use cookies for everything on this website.</p></div></body></html>')
    assert prune(junk) == []


def test_bad_input_never_raises():
    assert prune("") == []
    assert prune("<html><body><p>hi") == []
    assert bm25_blocks("", "anything") == []


def test_bm25_blocks_keeps_only_what_answers_the_question():
    got = bm25_blocks(PAGE, "chemist phone number akola", top_k=3)
    assert got and "0724 243 0000" in got[0].text


# ---------------------------------------------------------------- item 1: when to stop
def _k(query: str, texts: list[str]) -> EN.Knowledge:
    k = EN.Knowledge(query=query)
    for i, t in enumerate(texts):
        k.add(f"p{i}", t)
    return k


AGREE = [
    "The GST rate on cement in India is 28 percent, the highest slab, and it has been 28 percent since 2017.",
    "Cement attracts GST at 28 percent in India. Industry bodies asked the GST council to cut the cement rate.",
    "GST on cement in India remains 28 percent. The cement industry says the 28 percent GST rate raises cost.",
]
JUNK = [
    "Our company was founded in 1998 and values integrity above all else in every market.",
    "Careers at our firm include roles in sales, marketing, logistics and human resources today.",
    "Read our blog about leadership, teamwork, innovation and the future of modern workplaces.",
    "Contact us by phone or email, our offices are open Monday to Friday during business hours.",
]


def test_it_stops_early_when_the_pages_actually_answer_the_question():
    k = _k("GST rate on cement in India", AGREE)
    stop, why = EN.should_stop(k)
    assert stop and why.startswith("enough:"), why
    assert len(k.pages) < EN.EnoughConfig().max_pages


def test_coverage_is_not_scored_with_bm25():
    """The bug: BM25 idf collapses when every page agrees, so agreement LOWERED the score."""
    k = _k("GST rate on cement in India", AGREE)
    assert EN.coverage(k) >= 0.95


def test_consistency_uses_overlap_not_jaccard():
    k = _k("GST rate on cement in India", AGREE)
    assert EN.consistency(k) >= 0.45          # Jaccard scored these ~0.33 and never cleared the bar


def test_irrelevant_pages_never_claim_enough():
    k = EN.Knowledge(query="GST rate on cement in India")
    for i, t in enumerate(JUNK):
        k.add(f"j{i}", t)
        stop, why = EN.should_stop(k)
        assert not why.startswith("enough:"), why
        if stop:
            assert why.startswith("stalled:")
            break
    assert EN.confidence(k)["confidence"] < 0.2


def test_one_page_is_never_enough():
    k = _k("GST rate on cement in India", AGREE[:1])
    stop, _ = EN.should_stop(k)
    assert not stop
    assert EN.consistency(k) == 0.0           # a single source is not corroboration


def test_the_page_budget_always_wins():
    k = _k("anything at all", ["filler text number %d about nothing in particular" % i for i in range(9)])
    stop, why = EN.should_stop(k, EN.EnoughConfig(max_pages=5))
    assert stop and "page budget" in why


def test_the_most_relevant_link_wins_when_nothing_has_been_read():
    k = EN.Knowledge(query="GST rate on cement in India")
    out = EN.rank_links(k, [{"url": "https://x.com/careers", "text": "Careers"},
                            {"url": "https://x.com/gst-rate-cement", "text": "GST rate on cement"},
                            {"url": "https://x.com/privacy", "text": "Privacy policy"}],
                        EN.EnoughConfig(top_k_links=3))
    assert out[0]["url"].endswith("gst-rate-cement")


def test_an_offtopic_link_cannot_win_on_novelty_alone():
    k = _k("GST rate on cement in India", AGREE)
    out = EN.rank_links(k, [{"url": "https://x.com/careers", "text": "Careers"},
                            {"url": "https://x.com/gst-rate-cement", "text": "GST rate on cement"}],
                        EN.EnoughConfig(top_k_links=2))
    off = [r for r in out if "careers" in r["url"]][0]
    on = [r for r in out if "gst-rate" in r["url"]][0]
    assert off["score"] < on["score"], "an off-topic link outranked an on-topic one"


def test_a_link_already_read_is_never_offered_again():
    k = _k("GST rate on cement in India", AGREE)
    k.pages[0]["url"] = "https://x.com/seen"
    out = EN.rank_links(k, [{"url": "https://x.com/seen", "text": "seen"}], EN.EnoughConfig())
    assert out == []


def test_the_authority_weight_is_deliberately_absent():
    """Upstream weights relevance/novelty/authority 0.5/0.3/0.2 but hard-codes authority to 1.0 with the
    real calculation commented out, so a fifth of its score is inert. We carry the two live weights,
    renormalised to sum to 1.0, keeping their 5:3 ratio."""
    c = EN.EnoughConfig()
    assert not hasattr(c, "w_authority")
    assert abs(c.w_relevance + c.w_novelty - 1.0) < 1e-9
    assert abs(c.w_relevance / c.w_novelty - 5.0 / 3.0) < 1e-9
