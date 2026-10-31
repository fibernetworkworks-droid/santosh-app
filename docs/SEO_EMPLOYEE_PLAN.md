# Hoola SEO Employee — the ultimate plan

Owner ask (31 Oct 2026): *"EMPLOYEE ::: SEO HANDLER END TO END. User will choose AI employee by visiting the web console
or app, then only it will appear in the main app / console for work. It will do end-to-end SEO work, 24/7, manage all
SEO tasks, automations, workflows, features. Deep research how a world-class SEO company works. Very powerful, intact
with owner trust, real SEO optimisation, reliable and robust."*

This is the first **hireable AI employee**. Everything built here (hire → onboard → desk → 24/7 loop → trust → report)
becomes the frame every later employee uses. SEO goes first.

---

## 1. What a world-class SEO company actually does

Researched from agency retainers, SOW templates and Google's own guidance. Every serious agency runs the same
engine: **audit and baseline first, then monthly sprints over five workstreams, with reporting and governance around
them**.

| Phase / cadence | What the agency does | Hoola SEO Employee does the same |
|---|---|---|
| **Onboarding (week 1)** | Discovery call, access to GSC / GA4 / CMS / GBP, full technical + content + backlink audit, baseline, competitor set, 90-day roadmap | Onboarding interview in the app, connects the accounts, runs the full audit, writes the baseline and a 90-day roadmap she approves |
| **Implementation (months 2-3)** | Fix technical issues, rewrite titles / meta, schema, internal links, page speed | Applies fixes itself where it has write access (with her trust level), otherwise hands a developer-ready brief |
| **Monthly retainer** | Content (2-8 pieces), on-page tuning, local (GBP posts, reviews), links / digital PR (3-15), technical monitoring | The same, every week, as a sprint board she can see |
| **Reporting** | Weekly recap, fortnightly call, monthly report with baseline vs now | Weekly note in chat, monthly PDF (Hoola Print, with charts), live dashboard |
| **Governance** | KPIs agreed up front (rankings, traffic, conversions), who does what, change log | KPIs set at hire, every change logged with before / after, measured impact after 28 days |

**The five workstreams:**
1. **Technical:** crawl, indexing, sitemaps, robots, canonicals, redirects, Core Web Vitals, structured data, mobile, hreflang, broken links.
2. **On-page and content:** keyword research, topic clusters, briefs, new pages, refreshing decaying pages, titles / meta, internal linking, E-E-A-T.
3. **Local:** Google Business Profile completeness, posts, reviews and replies, photos, NAP consistency, citations, local landing pages (never doorway pages).
4. **Authority (off-page):** digital PR, local citations, partner / supplier links, unlinked brand mentions. **Never bought links.**
5. **AI search visibility (GEO):** being cited in Google AI Overviews / AI Mode, ChatGPT, Gemini, Perplexity and Claude. The playbook: answer-first content, factual density, consistent entity naming, schema, freshness. GEO is a layer on top of SEO, not a replacement.

Plus **analytics and reporting** and **strategy** around all five.

**Hard lines from Google's spam policies** (scaled content abuse, site reputation abuse, expired domains, doorway pages,
link schemes, fake reviews), which apply to AI Overviews / AI Mode too. The SEO Employee is built so it *cannot* do
these, whatever it is asked.

---

## 2. What Hoola already has (and what is missing)

**Already built (v0.103 SEO Sahayak, `server/app/seo/`, tools `seo` / `seo_dekho`, `lib/ui/seo_screen.dart`):**
- crawl audit of her site (≤ 60 pages, robots honoured, safe URLs): title / description / H1 / thin / alt / canonical / noindex / lang / LocalBusiness schema;
- PageSpeed + CrUX Core Web Vitals;
- Search Console read-only: clicks / impressions / CTR / position vs the last period, striking distance, low CTR, cannibalisation, intent mix, 25 % drop alert;
- drafts (page brief, JSON-LD, GBP post, review reply, keyword plan) approved only by her "Haan";
- Excel report and a weekly morning note;
- Employee frame (v0.58): role `seo_specialist`, preset `seo_agency`, duty `seo_work`, trust levels seekh → saathi → bharosa, approval asks, audit log, pause.

**Missing to be a real employee:**
1. **No hiring.** Employee mode is one switch with presets; nothing appears or disappears per employee.
2. **No hands.** It only drafts: it can't change a title, publish a post, submit a sitemap or reply to a review.
3. **No 24/7 loop.** Only a weekly note; no monitoring, no sprint, no follow-through.
4. **No memory of its own work.** No change log with before / after, no impact measurement, no roadmap.
5. **No content engine, authority work, AI-visibility tracking, GA4 conversions, Bing or competitor view.**

---

## 3. The hiring experience (both surfaces)

**Employee Hub:** a new screen in the web console (sidebar "Employees") and the phone app (Home → "Hire an
employee").
- Cards for each employee. Today: **SEO Specialist** (live). Later: Social media, Accounts, Telecaller, Support… shown as "coming".
- Each card: what it does, what it needs (website, Google sign-in), what it will never do, monthly cost.
- **Hire** → onboarding. **Pause** / **Let go** later (letting go stops all its jobs and keeps its history read-only).

**Only hired employees appear.** A new per-tenant table `hired_employees` (employee key, status hired / paused / left,
hired_at, settings). The console sidebar, the phone home and the agent's tool families read it:
- not hired → no SEO desk, no SEO cards, `seo_*` tools admitted only for a one-off question (as today);
- hired → an **SEO Desk** entry (console sidebar + phone home tile), its cards in the feed, its 24/7 jobs running.

**Onboarding interview** (conversational, about 5 minutes, in her language):
1. Website(s) (one, or several for an agency), business name, what she sells, cities / areas, who her customers are.
2. Goals: more calls / leads / orders / footfall; target cities; 3-5 competitors (or Hoola suggests some from Search Console queries she shares).
3. Connections, one tap each, all official sign-ins:
   - Google Search Console (read now; a separate "manage sitemaps" scope later);
   - Google Analytics 4 (read);
   - Google Business Profile;
   - the site's CMS: Hoola-built site = already connected; WordPress = Application Password; Shopify / Webflow / Wix = their own OAuth / API key, entered in the app, never in chat.
4. Trust level to start at (default **Seekh**: everything that changes the outside world waits for her tap).
5. Reporting: weekly note day / time, monthly report, who else gets it (staff / client email, with her approval).

Output: the **baseline** (today's numbers, frozen) and a **90-day roadmap** she approves.

---

## 4. How it works 24/7 — the employee runtime

```
 Worker loop (app/worker.py) ── every 5 min ──> Employee Scheduler
        │                                         │ due jobs per hired employee
        ▼                                         ▼
  Playbooks (SEO)  ──>  Task queue (seo_tasks)  ──>  Executor
  daily / weekly /       state: planned → doing →     reads: GSC, GA4, PSI, crawl, GBP, Bing
  monthly / triggers     waiting_her → done /         writes: Hoola site, WordPress, Shopify,
                         failed / rolled_back         GBP, sitemaps, IndexNow, email drafts
                                  │                         │
                                  ▼                         ▼
                        Trust gate (employee.service)   Change log (before / after, undo)
                        seekh / saathi / bharosa         + impact check after 7 / 28 days
                                  │
                                  ▼
                 Her surfaces: SEO Desk board, feed cards, weekly note, monthly PDF, approvals
```

- **Playbooks:** a playbook is code plus an Opus planning step: what to check, what to do, what counts as done. Each one runs as a task with steps (the existing `kaam_plan` job style), so a long job survives a restart and reports honestly.
- **One brain per employee.** The SEO Employee keeps its own memory per site: goals, roadmap, decisions she made ("never touch the /blog titles"), what it changed and what happened next. Every run reads it first.
- **Budget and limits:** model-spend cap per month per tenant, crawl politeness (robots, ≤ 1 request / 0.3 s, ≤ 500 pages / day), API quotas (GSC URL Inspection ≤ 2,000 / day / property). It stops and tells her when a cap is hit.
- **Kill switch:** Pause on the desk stops every job at once. "Let go" ends it.

---

## 5. Everything it does — the capability catalogue

Legend: **A** = does it automatically · **T** = depends on trust (asks at Seekh, does + tells at Bharosa) ·
**H** = always her tap · **D** = draft or brief only (she or her developer applies it).

### 5.1 Technical SEO
| Capability | Source (official only) | Mode |
|---|---|---|
| Full crawl of her site (up to 500 pages / day, robots honoured): status codes, redirect chains, broken links (internal + outbound), orphan pages, depth, duplicate titles / descriptions, canonical conflicts, noindex mistakes, mixed content, hreflang, image size / alt, render-blocking | own crawler (extends `seo.service.crawl`) | A |
| Indexing coverage: which important URLs are not indexed, and why | GSC URL Inspection API (≤ 2,000 / day), sitemaps API | A |
| Submit / refresh sitemaps; ping Bing / IndexNow on changed URLs | GSC Sitemaps API, IndexNow, Bing Webmaster API | T |
| Core Web Vitals, field + lab, per template; fix list with the biggest wins first | PageSpeed Insights + CrUX API | A (report), D / T (fixes) |
| Structured data: LocalBusiness / Organization / Product / FAQ / Article / Breadcrumb, validated before adding | own validator + schema.org rules | T on Hoola / CMS sites |
| robots.txt / redirects / canonical changes | CMS write | **H** (high blast radius) |
| Daily watch: site down, robots blocks everything, sudden noindex, sitemap 404, traffic drop ≥ 25 % | crawl + GSC | A (alert within the hour) |

### 5.2 On-page and content
| Capability | Mode |
|---|---|
| Keyword universe: her services × cities × intents, sized with Google Ads Keyword Planner (official), current positions from GSC; clustered into topics and mapped to pages (one main page per intent, which kills cannibalisation) | A |
| Striking distance (positions 4-20) and low CTR in the top 3 → title / description rewrites tested one page at a time | T |
| Content decay: pages losing clicks for 8 weeks → refresh brief or refresh draft | A (find), T (apply) |
| New page / blog post: brief → draft from HER facts (services, prices, photos, cases), FAQ, internal links, schema, author box (E-E-A-T) → her review → publish | **H** to publish (always, at every trust level, in phase 3) |
| Internal linking: suggest and add contextual links from strong pages to pages that need a lift | T |
| Image SEO: alt text, file names, compression suggestions | T |
| Quality gate before anything goes live: fact-check against her data, no made-up claims, readability, no duplicate of another page, spam-policy check (no thin / templated / scaled pages) | A (blocks itself) |

### 5.3 Local SEO (Google Business Profile)
| Capability | Mode |
|---|---|
| Profile audit: categories, services, hours, attributes, photos, description, NAP match with the site and citations | A |
| Weekly GBP posts (offers, updates, events) from her real news / photos | T |
| Every review gets a reply draft within the hour; 4-5 stars → posted at Saathi+, 1-3 stars → always her tap and an offline follow-up suggestion | T / H |
| Review requests: a ready message / QR for HER customers (never gated, never incentivised, never fake) | D |
| Local landing pages only where she really serves and has real content (no doorway city pages) | H |
| Citations: NAP consistency check across the major Indian directories she lists; corrections as a to-do with links | D |

### 5.4 Authority (off-page)
| Capability | Mode |
|---|---|
| Backlink picture from Bing Webmaster API (free, official) + her own Ahrefs / Semrush key if she has one | A |
| Opportunities: suppliers, partners, associations, local press, unlinked brand mentions, broken links on relevant sites | A (list) |
| Outreach emails / digital-PR pitches from her email, personalised, with her approval | **H** (each send) |
| Toxic-link watch (report only; disavow only on her decision with an explanation) | A / H |
| **Never:** buying links, PBNs, link exchanges at scale, paid guest posts without rel="sponsored" | refused by code |

### 5.5 AI search visibility (GEO)
| Capability | Mode |
|---|---|
| A panel of 20-50 real buyer questions per business ("best AC repair in Nagpur", "GST consultant near Dharampeth") asked every week to ChatGPT, Gemini, Claude and Perplexity **through their official APIs**: is she mentioned, cited, what is said, which competitor wins | A |
| AI-visibility score and trend in the dashboard | A |
| Fixes: answer-first openings, FAQ blocks, facts and numbers, consistent business name / address / services everywhere, schema, fresh dates on updated pages, reviews | T / D |
| Google AI Overviews / AI Mode: tracked inside GSC "Web" totals (no separate filter exists), plus the long conversational queries | A |

### 5.6 Analytics, reporting and strategy
| Capability | Mode |
|---|---|
| KPI dashboard on the SEO Desk: organic clicks, impressions, average position, top queries / pages, **leads / calls / orders from organic (GA4 conversions)**, Core Web Vitals, indexed pages, GBP calls / directions / website clicks, AI-visibility score, tasks done | A |
| Weekly note in chat: two halves (what moved, what it is doing next), in her language | A |
| Monthly report PDF (Hoola Print: cover, Key takeaways, charts, baseline vs now, work done, impact of each change, next month's plan) | A, sent to others only with her tap |
| Quarterly strategy review: what worked, roadmap update, budget asks | D (she approves) |
| Every change → impact check at 7 and 28 days (clicks / position / CTR of that page vs before, with a seasonality note); losers are flagged and offered a rollback | A |

---

## 6. 24/7 automations — the schedule

| When | Job |
|---|---|
| Every hour | Uptime + robots + noindex + sitemap watch; new GBP reviews → reply drafts |
| Every day 6:00 (her time) | GSC + GA4 pull (final data is 3 days old; Hoola says so), anomaly check, URL Inspection for new / changed pages, crawl the changed parts |
| Every Monday | Sprint plan for the week: top 5-10 tasks by impact × effort, shown on the board; at Seekh she approves the list |
| Mon-Fri | Execute the sprint (titles, schema, internal links, alt text, GBP post, refresh drafts…) within trust and caps |
| Every Friday | Weekly note: what changed, what moved, what's next; approvals waiting |
| Weekly | AI-visibility panel run; competitor snapshot (their pages / topics she's missing, via public pages only, robots honoured) |
| 1st of the month | Monthly report PDF + KPI review against the baseline; roadmap progress |
| Quarterly | Strategy review + roadmap v2 |
| Triggers | Clicks ↓ 25 % → incident mode (find cause: indexing, update, technical, seasonality); new page published → inspect + sitemap + internal links; Google core / spam update announced → watch and report |

---

## 7. Trust — how it stays safe with her business

Built on the existing Employee frame (`employee/roles.py` `kind_of`, `DutyTrust`, `EmployeeAsk`, `AuditEntry`), with SEO
action classes:

| Class | Examples | Seekh (start) | Saathi | Bharosa |
|---|---|---|---|---|
| **Read** | crawl, GSC, GA4, PSI, Bing, AI panel | auto | auto | auto |
| **Internal** | drafts, briefs, reports, board, memory | auto | auto | auto |
| **Small reversible** | title / description, alt text, schema, internal link, GBP post, 4-5★ review reply, sitemap submit | asks | does, tells her the same day | does, weekly summary |
| **Big / public / hard to undo** | publish a new page, delete / redirect / noindex / robots, 1-3★ review reply, outreach email, anything sent to others | asks | asks | asks (unless she allow-lists that exact action) |
| **Never** | buy links, fake reviews, review gating, cloaking, doorway / mass AI pages, keyword stuffing, editing outside her sites, promising ranks | refused | refused | refused |

- **Every change is undoable:** before / after stored, one-tap rollback (Hoola sites have versions already; WordPress through revisions; Shopify through the stored old value).
- **Daily cap** per trust level (like the employee CAP 0 / 40 / 150), **per-site allow-list** ("only /services/*"), and **frozen areas** she names.
- **Promotion is earned and offered, never automatic:** after N approvals in a row with no rollback and positive impact, it *suggests* moving up a level.
- **Honesty rules:** reports show real numbers with their date lag; it never claims a ranking result it can't measure; "I don't know why" is allowed.
- **Data safety:** tokens encrypted (as GSC today), least scopes, staff see only what she allows, client sites (agency mode) fenced per client.

---

## 8. Connections — official routes only

| Need | Route | Status / notes |
|---|---|---|
| Search performance, indexing, sitemaps | Google Search Console API (search analytics, URL Inspection 2,000 / day / property, sitemaps) | read scope already used; add `webmasters` (sitemaps write) as a separate consent |
| Conversions from organic | Google Analytics 4 Data API | new OAuth scope `analytics.readonly` |
| Speed | PageSpeed Insights v5 + CrUX API | have it |
| Local | Google Business Profile APIs (v1 accounts / locations; v4 localPosts, reviews) | **Newtika must apply for API access** (quota is 0 until approved; days to weeks) |
| Keyword volumes | Google Ads API Keyword Planner | Newtika developer token (basic access) |
| Bing + backlinks + IndexNow | Bing Webmaster Tools API, IndexNow | free |
| Write to her site | Hoola-built sites: direct (`site/edit.py` versions) · WordPress REST + Application Password (+ a small "Hoola SEO Connector" WP plugin we ship so Yoast / Rank Math title, description and schema fields are writable) · Shopify Admin GraphQL (`seo` fields, redirects) · Webflow / Wix APIs | phase 2 |
| AI visibility | OpenAI, Gemini, Anthropic, Perplexity official APIs | Newtika keys, cost-capped |
| Optional licensed data | her own Ahrefs / Semrush / DataForSEO key | owner opt-in |
| **Not allowed** | scraping Google results for rank tracking, unofficial GBP tools, browser-automating Search Console | rule: official routes only |

---

## 9. Data model (new tables, all nullable-safe)

- `hired_employees` (tenant, key `seo`, status, hired_at, left_at, settings JSON, trust, caps).
- `seo_roadmap` (site, item, workstream, impact, effort, status, due, why).
- `seo_jobs` / reuse `seo_tasks` + new `kind`, `plan`, `steps`, `trust_class`, `state` (planned / doing / waiting_her / done / failed / rolled_back).
- `seo_changes` (site, url, field, before, after, applied_by, applied_at, channel, undo_ref, impact_7d, impact_28d, verdict).
- `seo_baseline` (frozen numbers at hire).
- `seo_ai_panel` (question, engine, date, mentioned, cited_url, competitor, snippet).
- `seo_memory` (site, kind: goal / decision / frozen_area / fact, text).
- Existing: `seo_sites`, `seo_pages`, `seo_stats`, `seo_drafts`, `seo_google`, `seo_settings` stay.

---

## 10. Build phases (each one ships as a version, with tests)

| Phase | Ships | Done when |
|---|---|---|
| **0 · Hire frame** | `hired_employees`; Employee Hub (console + app); SEO card; onboarding interview; SEO Desk appears only after hire; Pause / Let go; tool admission follows hire | a tenant without SEO hired sees no SEO desk; hiring shows it on both surfaces; letting go stops its jobs |
| **1 · Eyes and brain** | full crawl ≤ 500 pages, GSC + GA4 + PSI + Bing reads, baseline, 90-day roadmap (Opus), SEO Desk board + KPI dashboard, daily watch + incident alerts, weekly note, monthly Hoola Print report | onboarding produces a baseline + roadmap; alerts fire on a simulated drop; report PDF has real charts |
| **2 · Hands (reversible)** | change log + undo; executors: Hoola sites, WordPress (+ connector plugin), Shopify; titles / meta / alt / schema / internal links; sitemaps + IndexNow; trust gate per class; impact checks at 7 / 28 days | a title change applies at Saathi, shows in the log, rolls back in one tap, and is measured 7 days later |
| **3 · Content and local** | keyword universe + clusters (Keyword Planner), briefs → drafts from her facts → quality gate → her tap to publish; decay refresh; GBP posts + review replies (after Google approves API access) | a refreshed page goes live only after her tap; review replies follow star rules |
| **4 · Authority and AI search** | Bing backlinks, opportunity finder, outreach drafts (her tap per send), AI-visibility panel + score + fixes, competitor snapshot | the panel shows mention / citation per engine weekly; no email leaves without her tap |
| **5 · Autonomy and scale** | Bharosa autonomy with allow-lists, earned-promotion suggestions, experiments (title A/B over time), agency mode (many client sites, client reports), staff access | 4 weeks at Bharosa with zero unwanted changes on a test site |

Phase 0 + 1 make it *feel* like a hired specialist on day one. Phase 2 is where it starts doing real work.

---

## 11. How we know it is world-class

- **For her:** organic clicks / leads up against the baseline at 90 days; tasks done per week; time to fix a critical issue (< 24 h); every review answered within a day; the monthly report lands on the 1st.
- **For trust:** approval rate, rollback rate (target < 5 %), "wrong" flags on the audit log, zero spam-policy violations.
- **For quality:** a fixed test bench of sites (like the Design Arena) re-audited every version; known faults must be found, known-good pages must not be "fixed".

---

## 12. Decisions needed from the owner

1. **Price:** SEO Employee per month (₹), and what is included (sites, pages / day, AI-panel questions).
2. **API applications in Newtika's name:** Google Business Profile API access, Google Ads developer token (Keyword Planner), Bing Webmaster, and model keys for the AI-visibility panel.
3. **Default trust at hire:** Seekh (recommended) or Saathi.
4. **WordPress connector plugin:** OK to publish a small official Hoola plugin on WordPress.org?
5. **Agency mode in v1** (many client sites per account) or later?
6. **Order:** Phase 0 + 1 together as the first build (recommended), then 2, 3, 4, 5.

---

Sources (research, 31 Oct 2026): agency retainer / SOW patterns ([justwords.in](https://www.justwords.in/blog/what-does-an-seo-agency-do/),
[contextbolt.com](https://contextbolt.com/blog/seo-retainer/), [taskade SOW](https://www.taskade.com/templates/statement-of-work/seo-services-sow),
[organicarbitrage](https://organicarbitrage.pages.dev/articles/seo-agency-pricing-decoded)); Search Console API limits
([singhamandeep.com](https://singhamandeep.com/?p=1590)); GEO ([llmrefs.com](https://llmrefs.com/generative-engine-optimization),
[stackmatix](https://www.stackmatix.com/blog/generative-engine-optimization-best-practices)); Business Profile API access
([slashpost.ai](https://slashpost.ai/blogs/google-business-profile/google-business-profile-api-documentation-2026),
[unified.to](https://docs.unified.to/guides/how_to_set_up_google_business_profile_api_access_and_get_oauth_2_credentials));
spam policies ([ppc.land](https://ppc.land/scaled-content-abuse/), [searchenginejournal](https://searchenginejournal.com/in-depth-look-at-google-spam-policies-updates/511005),
[gsqi.com](https://gsqi.com/marketing-blog/august-2026-google-spam-update-case-studies/)). Third-party sources; Google's own
docs are checked again at build time for exact quotas and scopes.
