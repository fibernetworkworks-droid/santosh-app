"""Item 2: decide what to CUT from a page. Hand-built, zero upstream code (the port law).

Why this exists: `scrape_page` already makes markdown, but it prunes nothing - nav, footer, cookie
banners, share rails and ads all spend her 24,000-character budget, and then the model reads them. This
scores every node and drops the boilerplate BEFORE the markdown is made.

Two filters, both from published ideas, both implemented here from scratch:

* `prune(html)` - no query needed. Scores each element on five signals and keeps what reads like content.
  Computed in ONE bottom-up pass (each node's text/link/tag counts folded up from its children), so it is
  O(nodes), not O(nodes x subtree). The naive shape re-walks every subtree and is ~10x slower on a long page.
* `bm25_blocks(html, query)` - keeps only the blocks that answer HER question, scored with our own BM25.

Both return the kept blocks AND the pruned HTML, so the caller can hand either to the markdown step.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .bm25 import BM25, words

# Tags that are never content, whatever they score.
_DROP_TAGS = {"script", "style", "noscript", "template", "svg", "canvas", "iframe", "form", "button",
              "input", "select", "textarea", "nav", "footer", "aside", "header"}
# Tags that are usually content, and get a lift.
_GOOD_TAGS = {"article": 1.0, "main": 1.0, "section": 0.7, "p": 0.8, "div": 0.5, "td": 0.5, "li": 0.4,
              "blockquote": 0.7, "pre": 0.8, "code": 0.6, "h1": 0.8, "h2": 0.8, "h3": 0.7, "h4": 0.6,
              "h5": 0.5, "h6": 0.5, "table": 0.6, "span": 0.3, "figure": 0.5, "dd": 0.4, "dt": 0.4}
# Words in class/id that mark chrome, and words that mark content.
_BAD_WORDS = re.compile(
    r"nav|menu|sidebar|side-bar|footer|header|banner|cookie|consent|gdpr|popup|modal|overlay|advert|\bads?\b"
    r"|promo|sponsor|share|social|follow|subscribe|newsletter|signup|login|breadcrumb|pagination|pager"
    r"|related|recommend|trending|widget|toolbar|masthead|skip-link|offcanvas|drawer|hamburger|search-form", re.I)
_GOOD_WORDS = re.compile(r"article|content|post|entry|story|main|body|text|prose|detail|description|product"
                         r"|answer|question|recipe|spec|price|review", re.I)
_WS = re.compile(r"\s+")


@dataclass
class Block:
    """One kept piece of the page."""
    tag: str
    text: str
    score: float
    chars: int = 0
    def __post_init__(self) -> None:
        self.chars = len(self.text)


@dataclass
class _N:
    """Folded-up counts for one element. Filled bottom-up, once."""
    chars: int = 0          # text characters in this subtree
    link_chars: int = 0     # of those, inside <a>
    tags: int = 0           # elements in this subtree
    commas: int = 0
    own: str = ""           # this node's own direct text
    kids: list = field(default_factory=list)


def _clean(s: str) -> str:
    return _WS.sub(" ", (s or "")).strip()


def _tag_weight(tag: str) -> float:
    return _GOOD_TAGS.get(tag, 0.2)


def _attr_weight(el) -> float:
    """class/id signal: chrome words push down, content words lift. Range -1..+1."""
    blob = f"{el.get('class') or ''} {el.get('id') or ''} {el.get('role') or ''}"
    if not blob.strip():
        return 0.0
    bad = len(_BAD_WORDS.findall(blob))
    good = len(_GOOD_WORDS.findall(blob))
    if not bad and not good:
        return 0.0
    return max(-1.0, min(1.0, (good - bad) / float(good + bad)))


def is_chrome(el) -> bool:
    """A hard gate, not a nudge. A node whose class/id/role says cookie-consent, advert, promo, share or
    sidebar IS chrome, whatever its text reads like - and the first version of this file got that wrong:
    the class signal was only 10% of the score, so a wordy cookie banner and a promo advert both scored
    above the bar and survived. Content words in the same attribute veto the gate (a div class="ad-article"
    on a news site is an article), and so does a real sectioning role."""
    blob = f"{el.get('class') or ''} {el.get('id') or ''} {el.get('role') or ''}"
    if not blob.strip():
        return False
    bad, good = len(_BAD_WORDS.findall(blob)), len(_GOOD_WORDS.findall(blob))
    if good >= bad:
        return False
    return bad >= 1


def _fold(el, acc: dict) -> _N:
    """ONE bottom-up pass: a node's counts are its own text plus its children's folded counts."""
    tag = str(getattr(el, "tag", "") or "").lower()
    n = _N(own=_clean(el.text if isinstance(el.text, str) else ""))
    n.chars = len(n.own)
    n.commas = n.own.count(",") + n.own.count("।")   # danda counts, Hindi prose uses it
    n.tags = 1
    if tag == "a":
        n.link_chars = n.chars
    for kid in el:
        ktag = str(getattr(kid, "tag", "") or "").lower()
        if not isinstance(ktag, str) or ktag in _DROP_TAGS or ktag.startswith("{") or is_chrome(kid):
            continue                                   # comments/PIs have non-str tags; chrome is dropped
        kn = _fold(kid, acc)
        n.chars += kn.chars
        n.link_chars += kn.link_chars
        n.tags += kn.tags
        n.commas += kn.commas
        n.kids.append((kid, kn))
        tail = _clean(kid.tail if isinstance(kid.tail, str) else "")
        if tail:
            n.chars += len(tail)
            n.commas += tail.count(",")
    acc[id(el)] = n
    return n


def _score(el, n: _N, page_chars: int) -> float:
    """Five signals, weighted the way the published pruning filter weights them."""
    if n.chars <= 0:
        return 0.0
    text_density = n.chars / float(max(1, n.tags))          # characters per element
    link_density = n.link_chars / float(n.chars)
    tag = str(getattr(el, "tag", "") or "").lower()
    share = n.chars / float(max(1, page_chars))
    s = (0.40 * min(1.0, text_density / 80.0)               # dense text reads like prose
         + 0.20 * (1.0 - min(1.0, link_density))            # a link farm is not content
         + 0.20 * _tag_weight(tag)
         + 0.10 * ((_attr_weight(el) + 1.0) / 2.0)          # mapped to 0..1
         + 0.10 * min(1.0, share * 4.0))                    # a node holding much of the page matters
    if n.commas >= 3:
        s += 0.05                                           # punctuated prose, not a label list
    return max(0.0, min(1.0, s))


def prune(html: str, threshold: float = 0.48, dynamic: bool = True, min_words: int = 2,
          keep_classes: tuple[str, ...] = (), max_blocks: int = 400) -> list[Block]:
    """Score every element and return the blocks that read like content, in page order.

    `dynamic` lowers the bar on a page where everything scores low (a sparse page would otherwise come back
    empty, which is worse than a little boilerplate).
    """
    from lxml import html as LH
    try:
        root = LH.fromstring(html or "")
    except Exception:
        return []
    body = root.find("body")
    if body is None:
        body = root
    acc: dict = {}
    _fold(body, acc)
    page_chars = acc[id(body)].chars or 1
    scored: list[tuple[float, object, _N]] = []
    for el in body.iter():
        tag = str(getattr(el, "tag", "") or "").lower()
        if not isinstance(tag, str) or tag.startswith("{") or tag in _DROP_TAGS or tag in ("body", "html"):
            continue
        n = acc.get(id(el))
        if n is None or n.chars < 25:
            continue                                   # acc has no entry for a chrome subtree: _fold skipped it
        if is_chrome(el):
            continue
        scored.append((_score(el, n, page_chars), el, n))
    if not scored:
        return []
    bar = threshold
    if dynamic:
        vals = sorted(s for s, _, _ in scored)
        median = vals[len(vals) // 2]
        bar = min(threshold, max(0.18, median))             # never above the fixed bar, never silly-low
    keepcls = tuple(c.lower() for c in keep_classes)
    out: list[Block] = []
    taken: set[int] = set()
    for s, el, n in scored:
        blob = f"{el.get('class') or ''} {el.get('id') or ''}".lower()
        forced = any(c in blob for c in keepcls) if keepcls else False
        if not forced and s < bar:
            continue
        # keep the OUTERMOST winner: if an ancestor was already taken, its text already carries this
        anc = el.getparent()
        skip = False
        while anc is not None:
            if id(anc) in taken:
                skip = True
                break
            anc = anc.getparent()
        if skip:
            continue
        text = _clean(el.text_content())
        if len(words(text, keep_stop=True)) < min_words:
            continue
        taken.add(id(el))
        out.append(Block(tag=str(getattr(el, "tag", "")), text=text, score=round(s, 4)))
        if len(out) >= max_blocks:
            break
    return out


def bm25_blocks(html: str, query: str, top_k: int = 25, min_score: float = 0.0) -> list[Block]:
    """Keep only the blocks that answer HER question. Prune first, then rank what survived."""
    blocks = prune(html, dynamic=True)
    if not blocks:
        return []
    q = words(query)
    if not q:
        return blocks[:top_k]
    docs = [words(b.text) for b in blocks]
    bm = BM25(docs)
    ranked = sorted(zip(bm.scores(q), blocks), key=lambda x: -x[0])
    out = []
    for s, b in ranked[:top_k]:
        if s <= min_score:
            continue
        out.append(Block(tag=b.tag, text=b.text, score=round(float(s), 4)))
    return out


def as_text(blocks: list[Block], cap: int = 24_000) -> str:
    parts, n = [], 0
    for b in blocks:
        if n + len(b.text) > cap:
            break
        parts.append(b.text)
        n += len(b.text) + 2
    return "\n\n".join(parts)
