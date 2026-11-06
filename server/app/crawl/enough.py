"""Item 1: know when it has read ENOUGH, and stop. Hand-built, zero upstream code (the port law).

The gap this closes: Hoola's crawl is a plain FIFO breadth-first walk (`crawl_jobs.run_job`: queue.pop(0)
/ queue.append) that stops at a page cap, never because it has the answer. The research crew (v0.437) runs
on step budgets for the same reason. So a 20-page budget is spent whether the answer arrived on page 2 or
never arrived at all.

The published idea, implemented here from the formula up:

    confidence = 0.4 x coverage + 0.3 x consistency + 0.3 x saturation      (stop at >= 0.7)

  coverage    - how much of HER QUESTION the pages read so far actually speak to (BM25 over the kept
                blocks, normalised; a question term nobody mentions is a hole).
  consistency - do the pages AGREE? Measured as the mean pairwise term overlap of the per-page top terms.
                One page saying something no other page says is not yet knowledge.
  saturation  - diminishing returns: 1 - (new terms in the last batch / new terms in the first batch).
                When a fresh page teaches almost nothing new, reading more pages is spending for nothing.

Link ranking:   score = 0.625 x relevance + 0.375 x novelty

DELIBERATE DIFFERENCE FROM UPSTREAM, said out loud: the published version is
0.5 relevance + 0.3 novelty + 0.2 authority, but its `_calculate_authority` is commented out at the call
site and authority is hard-coded to 1.0 - so a fifth of that score is inert and every link gets the same
0.2. Rather than copy a dead term, the two live weights are renormalised to sum to 1.0, which keeps the
score a true 0..1 and keeps their 5:3 ratio exactly. If a real authority signal is ever wanted, it goes in
as a third term and the weights move together.

No model, no embeddings, no sentence-transformers, no alphashape/shapely: this is the statistical path, and
it is the one that runs on her VPS for free. The embedding path is a later decision, not a dependency.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse

from .bm25 import BM25, words


@dataclass
class EnoughConfig:
    confidence_threshold: float = 0.70   # stop once the three signals together say we have it
    max_pages: int = 20                  # hard ceiling, always
    max_depth: int = 5
    top_k_links: int = 3                 # how many links to take from each page
    min_gain: float = 0.05               # stop if a whole batch moves confidence less than this
    min_pages: int = 2                   # never declare "enough" off a single page
    w_coverage: float = 0.40
    w_consistency: float = 0.30
    w_saturation: float = 0.30
    w_relevance: float = 0.625           # see the module docstring: upstream's third term is inert
    w_novelty: float = 0.375


@dataclass
class Knowledge:
    """What has been read so far, and the history the signals are computed from."""
    query: str = ""
    pages: list[dict] = field(default_factory=list)      # {url, text, terms:set, top:set}
    vocab: set[str] = field(default_factory=set)
    new_per_batch: list[int] = field(default_factory=list)
    confidence_history: list[float] = field(default_factory=list)

    def add(self, url: str, text: str, top_n: int = 40) -> None:
        ts = words(text)
        if not ts:
            self.pages.append({"url": url, "text": text, "terms": set(), "top": set()})
            self.new_per_batch.append(0)
            return
        freq: dict[str, int] = {}
        for w in ts:
            freq[w] = freq.get(w, 0) + 1
        top = {w for w, _ in sorted(freq.items(), key=lambda x: -x[1])[:top_n]}
        term_set = set(ts)
        fresh = len(term_set - self.vocab)
        self.vocab |= term_set
        self.new_per_batch.append(fresh)
        self.pages.append({"url": url, "text": text, "terms": term_set, "top": top})

    @property
    def urls(self) -> set[str]:
        return {p["url"] for p in self.pages}


def coverage(k: Knowledge) -> float:
    """How much of her question the pages speak to. Term presence, weighted by how well the best page
    scores on the whole query, so a page that merely contains a word scores below one that is about it."""
    q = words(k.query)
    if not q or not k.pages:
        return 0.0
    qs = set(q)
    # breadth: query terms answered by ANY page
    seen: set[str] = set()
    for pg in k.pages:
        seen |= (pg["terms"] & qs)
    hit = len(seen) / float(len(qs))
    # depth: the BEST SINGLE page's share of the question - one page that speaks to the whole question is
    # worth more than five that each touch a corner.
    #
    # This deliberately does NOT use BM25, and that is the bug the first version shipped: BM25's idf is
    # log(1 + (N - df + 0.5)/(df + 0.5)), so a term present in EVERY page has df == N and idf collapses to
    # ~0.1. The better the pages agree, the lower the BM25 score - precisely backwards for a "do we have
    # the answer yet" signal. Four pages all stating the same GST rate scored 0.71 and never stopped.
    depth = max((len(pg["terms"] & qs) / float(len(qs))) for pg in k.pages)
    return max(0.0, min(1.0, 0.65 * hit + 0.35 * depth))


def consistency(k: Knowledge) -> float:
    """Do the pages agree? Mean pairwise Jaccard of their top terms. One page alone is 0 by definition -
    a single source is not corroboration."""
    tops = [p["top"] for p in k.pages if p["top"]]
    if len(tops) < 2:
        return 0.0
    tot, n = 0.0, 0
    for i in range(len(tops)):
        for j in range(i + 1, len(tops)):
            a, b = tops[i], tops[j]
            # OVERLAP COEFFICIENT, not Jaccard: |A n B| / min(|A|,|B|). Jaccard divides by the union, so two
            # pages that agree on every key fact but differ in length or surrounding wording scored ~0.33 and
            # held confidence under the bar for ever. Overlap asks the question that matters here - of the
            # smaller page's key terms, how many does the other page also carry?
            m = min(len(a), len(b))
            if m:
                tot += len(a & b) / float(m)
                n += 1
    return max(0.0, min(1.0, (tot / n) if n else 0.0))


def saturation(k: Knowledge) -> float:
    """Diminishing returns. 1 - (new terms last page / new terms first page), floored at 0."""
    hist = [x for x in k.new_per_batch if x >= 0]
    if len(hist) < 2:
        return 0.0
    first = max(1, hist[0])
    last = hist[-1]
    return max(0.0, min(1.0, 1.0 - (last / float(first))))


def confidence(k: Knowledge, cfg: EnoughConfig | None = None) -> dict:
    cfg = cfg or EnoughConfig()
    cov, con, sat = coverage(k), consistency(k), saturation(k)
    c = cfg.w_coverage * cov + cfg.w_consistency * con + cfg.w_saturation * sat
    c = max(0.0, min(1.0, c))
    return {"confidence": round(c, 4), "coverage": round(cov, 4),
            "consistency": round(con, 4), "saturation": round(sat, 4), "pages": len(k.pages)}


def should_stop(k: Knowledge, cfg: EnoughConfig | None = None) -> tuple[bool, str]:
    """(stop?, why). The 'why' is for her card - a crawl that stops must say which rule stopped it."""
    cfg = cfg or EnoughConfig()
    m = confidence(k, cfg)
    k.confidence_history.append(m["confidence"])
    if len(k.pages) >= cfg.max_pages:
        return True, f"page budget reached ({cfg.max_pages})"
    if len(k.pages) < max(1, cfg.min_pages):
        return False, "too few pages to judge"
    if m["confidence"] >= cfg.confidence_threshold:
        return True, (f"enough: confidence {m['confidence']:.2f} "
                      f"(coverage {m['coverage']:.2f}, agreement {m['consistency']:.2f}, "
                      f"new-info {1 - m['saturation']:.2f})")
    h = k.confidence_history
    if len(h) >= 4 and (h[-1] - h[-4]) < cfg.min_gain:
        return True, (f"stalled: three pages moved confidence by {h[-1] - h[-4]:+.3f} "
                      f"(under {cfg.min_gain}) and it is still {h[-1]:.2f}")
    return False, f"keep going: confidence {m['confidence']:.2f}"


# ---------------------------------------------------------------- which link next
def _url_terms(url: str, anchor: str) -> list[str]:
    u = urlparse(url)
    return words(f"{anchor} {u.path.replace('/', ' ').replace('-', ' ').replace('_', ' ')}")


def rank_links(k: Knowledge, links: list[dict], cfg: EnoughConfig | None = None) -> list[dict]:
    """Score candidate links on relevance to her question + novelty against what has been read.

    `links` are {url, text}. Returns them sorted best-first with the score and its parts attached, so a
    card can show WHY a link was followed.
    """
    cfg = cfg or EnoughConfig()
    q = set(words(k.query))
    seen = k.urls
    out = []
    for ln in links:
        url = (ln.get("url") or "").strip()
        if not url or url in seen:
            continue
        terms = set(_url_terms(url, ln.get("text") or ""))
        rel = (len(terms & q) / float(len(q))) if q else 0.0
        # novelty: how much of this link's own wording is NOT already in the vocabulary
        nov = (len(terms - k.vocab) / float(len(terms))) if terms else 0.0
        score = cfg.w_relevance * rel + cfg.w_novelty * nov
        if rel <= 0.0:
            # An OFF-TOPIC link must not beat an on-topic one by being unfamiliar. Upstream has this same
            # flaw (its third weight is a constant, so ranking is effectively relevance:novelty 5:3) and a
            # /careers page outranked the one page whose slug was literally the question. Exploration is
            # still possible - the link keeps a discounted score - it just cannot win on novelty alone.
            score *= 0.4
        out.append({**ln, "score": round(score, 4), "relevance": round(rel, 4), "novelty": round(nov, 4)})
    out.sort(key=lambda x: -x["score"])
    return out[: max(1, cfg.top_k_links)] if out else []
