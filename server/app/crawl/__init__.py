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
  tables.py  Item 5 — a <table> as DATA: colspan/rowspan expanded into a dense grid, and a scorer that
             tells a data table from a layout table (handing a layout table to the Data Desk is worse
             than returning nothing).
  chunks.py  Item 6 — six chunking strategies for page text (identity/regex/sentence/fixed/sliding/topic).
  blocked.py Item 7 — tell a block from a page BY VENDOR (Cloudflare, Akamai, PerimeterX, DataDome,
             Imperva, Sucuri, Kasada, AWS WAF), in three tiers, plus the empty-shell check.
  frontier.py Item 3 — best-first instead of FIFO: a priority queue, five URL scorers, five URL filters
             that say WHY they refused, and a bounded Bloom membership filter.
  seed.py    Item 4 — find URLs without fetching pages: robots.txt -> Sitemap: -> sitemap XML, following
             indexes and .gz, plus the Common Crawl index. The ONLY module here that touches the network,
             and it takes the SSRF guard from its caller rather than having its own idea of safe.
  proxies.py Item 8a — proxy rotation as policy: round-robin, a DIRECT sentinel, sticky sessions, failure
             resting, and credentials that never appear in anything printable.
  steps.py   Item 8b — a six-verb step script compiled to JavaScript. Closed command set (no EVAL), every
             selector and value emitted as a JSON literal with < and > escaped, and a compile-time refusal
             to type into a password / OTP / PIN / CVV / card field.

TWO THINGS DELIBERATELY NOT BUILT, recorded here so a later session does not "complete" them by accident:

  * robots.txt `Disallow:` mining as a URL-discovery source. crawl4ai's DomainMapper offers it - reading
    the file where an operator wrote down what they do not want crawled, and using it as a map. Hoola reads
    robots.txt to OBEY it (`scrape_respect_robots`, default True, unchanged). Only `Sitemap:` lines are read.
  * minting rotating residential proxies from a commercial provider's API (crawl4ai's `set_nstproxy`).
    Whether Hoola ever pays to get through a site that said no is the owner's call, not a default.

The inertness law: importing app.crawl starts no thread, opens no socket and writes no file.
"""
from . import (  # noqa: F401  (the package-export law, v0.478)
    blocked, bm25, chunks, enough, frontier, prune, proxies, seed, steps, tables,
)

__all__ = ["blocked", "bm25", "chunks", "enough", "frontier", "prune", "proxies", "seed",
           "steps", "tables"]
