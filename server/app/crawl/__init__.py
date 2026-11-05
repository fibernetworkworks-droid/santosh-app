"""v0.533 CRAWL BRAIN — the crawl4ai ideas, hand-built for Hoola (the port law).

Owner read github.com/unclecode/crawl4ai and said "give this all to hoola ai". None of its code is here,
and that is not only house style: crawl4ai vendors a fork of html2text (declaring upstream's own release
2024.2.26) with no copyright line and no licence header, while upstream html2text is distributed under the
GPLv3 — and `markdown_generation_strategy.py` plus `utils.py` both import it, so every page-to-markdown
conversion in that library runs through GPL'd code inside an Apache-2.0 repo. `agent/crawl_jobs.py` already
keeps Firecrawl's AGPL engine out of this tree for the same reason. So the published ALGORITHMS are
re-implemented here from their formulas, and measured.

What lives here (every module is pure computation — no network, no browser, no model):

  bm25.py    BM25 Okapi, hand-built, so there is no rank_bm25 dependency.
  prune.py   Item 2 — what to CUT from a page: one-pass bottom-up node scoring + a hard chrome gate, and a
             BM25 filter that keeps only the blocks answering her question.
  enough.py  Item 1 — when to STOP: confidence = 0.4 coverage + 0.3 consistency + 0.3 saturation, plus
             link ranking on relevance + novelty.

The inertness law: importing app.crawl starts no thread, opens no socket and writes no file.
"""
from . import bm25, enough, prune  # noqa: F401  (the package-export law, v0.478)

__all__ = ["bm25", "enough", "prune"]
