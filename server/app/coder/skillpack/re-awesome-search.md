---
name: re-awesome-search
description: awesome-search over our index - the lists shelf
when_to_use: awesome list, curated list, best tools list, find a list of tools, resources list, github awesome
---
GOAL: the awesomelists.top pattern - "the Related lists": under one
curated list other curated lists are attached, and search runs over
those curated indexes, not the raw web. In this skill Hoola builds
ITS OWN awesome-search: the ingested index (which came in through
the crawl / scrape lanes) + zoo (app/zoo_catalog.json) + publicapis
+ app/datasets.py = ONE searchable shelf. The index lives in the
TOOLS LANE - this skill is the proof of that design.

THE DOORS (all real Hoola operator tools):
1. INGEST (crawl lane): give crawl_start a seed of curated lists -
   public awesome repos, an index of indexes like awesomelists.top.
   Watch progress with crawl_status, pick up rows with
   crawl_results. For one or two pages use scrape_site /
   scrape_many / scrape_page. To find a new source start with
   google_search / web_sources - "which list is there?" is the
   first question.
2. SHELF (what is already filled): the catalogs in zoo
   (app/zoo_catalog.json), the APIs in publicapis, the datasets in
   app/datasets.py - the three together with the ingested index
   make ONE index. To cover an API use api_find + api_docs; for
   stored rows use data_read / data_fetch.
3. RANK: awesomeness = maintenance + freshness + license. Stars are
   only a rough signal, not a verdict; paid placement NEVER - rank
   comes only from public criteria, the same formula for every row.
4. SERVE: print the TOP-3 for a query - each row with name + source
   + fetched-date. Do not dump the whole list; the three best, and
   one line "ask if you want more".
5. REFRESH: a shelf goes stale like code - run crawl_start again on
   a schedule, write the new fetched-date, replace the old row;
   freshness feeds the rank directly, so refresh before the rank
   drops, not after.
6. skill_manage: save the ingest / rank / refresh recipe you built
   as a skill - the recipe itself becomes part of the shelf (the
   recursive part of Related lists).

THE LAWS: printed output is the only evidence - saying "found it"
without printing what was served from the shelf is not allowed;
private data never leaves the tenant (not in ingest, not in hosting,
not in results); a fetched-date is required on every row - a row
without a date is stale and is not served; the index stays inside
Hoola's tools lane.

NEVER: ingest a login-walled index (the shelf is public-only); serve
a stale row with no fetched-date; paid or sponsored ranking - rank =
maintenance + freshness + license only; dump the whole list - no
more than the top-3, the rest "on request"; host the index outside
(it stays inside the tenant); put the tenant's private data into the
index or carry it out in results; claim "result found" without
printing it.

ALSO ASKED AS (Hinglish asks this skill answers): is topic ki awesome list
dhoondo, best tools ki list chahiye, curated list batao
