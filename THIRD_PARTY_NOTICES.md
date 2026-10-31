# Third-party notices

## claude-seo (ideas and thresholds for Hoola SEO PRO, v0.319)

Hoola's SEO checks in `server/app/seo/pro.py` (and the SEO PRO parts of `seo/service.py`, `seo/desk.py` and
`site/sitemap.py`) were designed after studying the open-source project **claude-seo** by AgriciDaniel
(https://github.com/AgriciDaniel/claude-seo, v2.5.0, commit 6be93f4). No code was copied: the checks, texts and lists are
Hoola's own, re-written for Indian small businesses. These ideas and numbers came from that project:

- the 7-part health score weights (technical 22, content 23, on-page 20, schema 10, performance 10, AI readiness 10,
  images 5) and the critical / high / medium / low buckets
- the 17 page-drift comparison rules
- the AI crawler split (search bots vs training bots vs user-triggered fetchers)
- page-type word-count floors, image weight bands, scaled-content gates (30-40% unique; 100 / 500 pages; location
  pages 30 / 50), templated-metadata detection
- the E-E-A-T (20 / 25 / 25 / 30) and local search (25 / 20 / 20 / 15 / 10 / 10) scorecard weights
- the retired / no-rich-result structured data types and the Google updates ledger (dates from Google's own Search
  Status Dashboard and Search Central)
- the report envelope: first principle, how we would know it failed, leading indicator

Not used on purpose (Hoola works through official routes only): Google results scraping (site: lookups, SERP / competitor
scoring, briefs from results), paid third-party SEO data providers, crawler impersonation, AI-text "humanising", the
Indexing API for ordinary pages, and the project's CC BY-SA phrase lists and CC BY prompts.

claude-seo is licensed under the MIT License:

```
MIT License

Copyright (c) 2026 agricidaniel

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
