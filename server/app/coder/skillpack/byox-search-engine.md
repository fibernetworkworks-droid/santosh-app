---
name: byox-search-engine
description: Build a search engine: crawler, inverted index, BM25
---
GOAL: a local search engine that indexes 1000 HTML pages and returns ranked results.

PHASES
1. In-memory inverted index: term → sorted list of (doc_id, tf); query AND/OR.
2. BFS crawler for a local set of HTML pages; parse links; robots.txt check.
3. TF-IDF scoring; rank top-10 results for a query.
4. BM25 scorer; positional index for phrase queries ("exact match").
5. Persist index to disk (SSTable); serve via HTTP; query time < 50 ms.

CORE CONCEPTS
- Inverted index: for each term, a postings list of (doc_id, positions[]).
- BM25: TF component saturates; IDF penalises very common terms; k1=1.5, b=0.75.
- PageRank: iterative rank = (1-d)/N + d·sum(rank[in]/out_degree[in]).

VERIFY: query "python web server" returns relevant pages in top-3; latency < 50 ms.
