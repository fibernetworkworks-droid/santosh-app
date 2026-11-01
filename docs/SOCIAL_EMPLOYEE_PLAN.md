# Hoola Social Media Manager — the ultimate plan

Owner asks (1 Nov 2026): *"Till this we will move to other employee ::: Social Media Manager — first do deep research what
we have"* → *"How user will put their social media details"* → *"GO PLAN"*.

The second hireable AI employee, on the frame the SEO Specialist built (hire → onboard → desk → 24/7 loop → trust →
report; `employee/hire.py`, `seo/desk.py`). It runs a small business's Instagram, Facebook Page, YouTube and Google
Business posts like a good agency would — plan, create, approve, publish, reply, measure, improve — inside her trust.

---

## 1. What a world-class social media agency actually does

A good agency for an Indian small business runs a monthly loop, not "a post a day":

1. **Discovery (week 1).** Business, offers, prices, customers (who, where, language), competitors (3-5 real accounts),
   brand look and voice, what worked before (her last 50 posts), goals (calls, WhatsApp chats, walk-ins, orders, followers).
2. **Strategy.** 3-5 **content pillars** (e.g. a clinic: *before/after*, *tips*, *team & trust*, *offers*, *patient
   stories*), a **format mix** (Reels lead reach; carousels lead saves; Stories keep followers warm; static posts for
   offers), a **posting rhythm** the business can keep (3-5 feed posts + daily Stories beats 2 a day for a month and
   silence after), languages, a **festival & local calendar** (Diwali, Navratri, Eid, Christmas, Pongal, Onam, city events,
   wedding season, exams, monsoon), and the **one number** each month is judged on.
3. **Monthly calendar.** Every slot: date, time, platform, format, pillar, hook, caption, hashtags, visual brief, CTA,
   link — approved by the client **before** production.
4. **Production.** Hooks in the first 1-2 seconds, captions in the client's language, 3-10 targeted hashtags (no
   30-hashtag walls), on-brand visuals in each platform's size, Reel covers, alt text, music only from licensed sources,
   `#ad` / paid-partnership labels when money is involved.
5. **Approval** by the client (agencies lose clients on unapproved posts).
6. **Publishing** at the audience's active hours, cross-posting adapted (not copy-pasted) per platform.
7. **Community management.** Reply to comments within hours, answer DMs, turn price / location / "available?" questions
   into leads (WhatsApp, call, booking link), hide spam, never argue in public, escalate complaints.
8. **Measurement.** Weekly pulse and a monthly report: reach, engagement rate, saves / shares, profile visits, website
   taps, follower growth, top & bottom posts, what to do more / less of. Every claim tied to a real number.
9. **Iteration.** Next month's calendar repeats what worked (formats, hooks, hours, pillars) and drops what didn't;
   small tests (two hooks, two times) instead of guesses.
10. **Never:** buy followers / likes, engagement pods, fake giveaways, misleading claims, posting someone's photo or song
    without rights, hiding that a post is paid.

---

## 2. What Hoola already has (and what is missing)

From the 1 Nov 2026 code inventory (full report in this session; key files below).

**Already built and reused as-is**
- **Writing:** Kalam (`kalam/`, v0.101) — `social` kind writes one piece with captions for Instagram / Facebook /
  LinkedIn / X / WhatsApp, repurpose, festival ideas, brand voice learned from her samples, `#Ad` on paid, claim checks.
- **Design:** Brand (`brand/`, v0.118) — real-Chromium posters in every social size (`rules.SIZES`: insta_post 4:5,
  square, grid, story 1080×1920 with safe zones, fb_post, linkedin, yt_thumb, gbp…), brand kit, WCAG / claims / Emblems
  checks, festival nudges 7 days before (`brand.due_nudges`).
- **Pictures / video:** photo_banao (`photogen.py`, AI label), imagekit background removal, Motion (`motion/`, 9:16 /
  1:1 / 16:9 + music), Video Editor (`videoedit/`, platform reel / short / status + caption), Video Studio, Create Studio.
- **YouTube:** full read + upload / comment reply / edit through cards (`youtube/`), Motion → Shorts.
- **Google Business:** posts drafted (`seo.gbp_post`), review replies via GBP API (`feedback/gbp.py`, her tap).
- **WhatsApp:** official Cloud API campaigns, templates, business inbox (24-hour rule, STOP).
- **Ads:** Ads Sahayak (`ads/`, v0.111) — Meta Marketing API read + tapped pause / budget changes, never creates ads.
- **Frame:** hire / pause / let go, trust seekh / saathi / bharosa, 24/7 `run_due`, KPIs vs frozen baseline, roadmap
  board, monthly Hoola Print PDF, console `employees.js` + phone `employees_screen.dart`.

**Missing (new work)**
1. Meta account connection (Instagram Login + Facebook Login for Business), account / Page picker, token refresh.
2. Publishing to Instagram (feed, carousel, Reels, Stories) and Facebook Pages (posts, photos, Reels / videos).
3. A content calendar + post queue for HER brand (draft → approved → scheduled → published / failed), scheduler.
4. Organic insights (reach, engagement, saves, follower growth, best hours) + weekly / monthly social report.
5. Instagram + Facebook comments and DMs inbox (reply drafts, hide spam, leads).
6. Carousel builder, one combined brand kit (look + voice + hashtag bank + pillars + audience), UGC with permission.
7. Trends / competitor watch through official routes only.
8. Composio `NEVER` blocks linkedin / instagram / facebook / twitter on purpose — social stays on direct official APIs.

---

## 3. The hiring experience (both surfaces)

**Employees → Social Media Manager → Hire** (console + phone), same as SEO. Then the **Social Desk** set-up, ~3 minutes:

1. **About the business** (pre-filled from her SEO desk / Brand kit / Kalam settings when they exist): name, city, what
   she sells, best sellers, customers, languages for posts, goal (calls / WhatsApp chats / walk-ins / orders / followers).
2. **Connect accounts** — tiles with a Connect button each (§8). She logs in on the platform's own page, picks the
   account / Page, comes back to a green tile (`@handle · 2,340 followers`). Hoola never sees a password.
3. **Look and voice** — her Brand kit + Kalam voice, or Hoola reads her last posts and proposes them; she ticks or edits.
4. **Trust level** — Seekh (every post waits for me) / Saathi (approved calendar posts on time, replies to simple
   questions) — Bharosa is offered later, never at hire.
5. **First check** (automatic, minutes): reads her last 50 posts + 90 days of insights per account → **baseline**
   (followers, reach / post, engagement rate, best hours, best formats, top 5 posts) → **strategy card** (pillars,
   rhythm, languages, the monthly goal number) → **first 30-day calendar** for her approval.

Personal Instagram accounts cannot connect through any official API: the tile shows a 3-step "switch to Professional
(free)" guide and checks again.

---

## 4. How it works 24/7 — the employee runtime

Same runtime as SEO (`run_due` from the worker, only for tenants whose Social employee is hired and not paused; one job
failing never stops the rest; every run written on the desk).

| When | Job |
|---|---|
| Every 5 min | **Publisher**: posts whose slot has come and that are approved (or allowed by trust) → publish → check it went live → link on the calendar; failure = one retry, then a card with the reason |
| Every 15 min | **Inbox**: new comments + DMs → classify (question / lead / praise / complaint / spam / abuse) → reply drafts or (trust) replies → leads to her WhatsApp / chat |
| Hourly | **Watch**: token alive, account still connected, posting quota left, a post removed / flagged by the platform, sudden negative comment burst → alert once on change |
| Daily 7 am | **Numbers**: yesterday's insights per post + account; a post doing 2× its usual → "boost-worthy?" note (no spending) |
| Daily 9 am | **Morning note** (only if something needs her): posts to approve today, unanswered complaints, a festival in 7 days |
| Weekly (her day) | **Pulse**: best / worst post, what to repeat, next week's slots filled from the plan; Stories set for the week drafted |
| Monthly (1st) | **Report PDF** (Hoola Print) vs baseline + **next month's calendar** draft for approval |
| Festivals −10 / −7 days | Festival post + Story + WhatsApp Status set (Brand already nudges at −7) |

---

## 5. Everything it does — the capability catalogue

### 5.1 Strategy and planning
- Content pillars, format mix and rhythm from her goal + her own past numbers (not a template).
- **Content calendar** (month grid + list): every slot has platform, format, pillar, hook, caption, hashtags, visual,
  CTA, link, language, status. Drag to move, tap to edit, "fill the empty slots".
- Festival + local calendar (`india.days`), wedding / exam / monsoon seasons, her own offers and launches.
- **Best time to post** from her audience's online hours (insights), not generic charts.

### 5.2 Content creation (reusing Kalam, Brand, Motion, Video Editor, photo_banao)
- Captions per platform in her language (Hinglish / Hindi / Marathi / English…), hook first, CTA last, 3-10 hashtags
  from her **hashtag bank** (local + niche + brand, rotated, no banned / spammy tags).
- **Carousel builder** (new): 3-10 slides from one idea (tips, before/after, menu, price list), on-brand, first slide = hook.
- Posters / Story frames in every size (Brand), Reels from her clips (Video Editor) or Motion, Reel cover + on-screen text.
- Product photos cleaned (imagekit), AI pictures only when she allows, always labelled as AI (IT Rules 2026 labels already in code).
- Alt text on every image; music only from the platform's licensed library or her own.
- Repurpose: one Reel → Short + Story + WhatsApp Status + GBP post + carousel.

### 5.3 Publishing
- Instagram: single image / video, **carousel (one post in the quota)**, Reels, Stories (single image / video, no caption).
- Facebook Page: text + link, photo(s), video / Reel.
- YouTube Shorts (existing upload), Google Business post (GBP API), LinkedIn (later), WhatsApp Status / Channel =
  **made by Hoola, posted by her** (no official API) with a one-tap share sheet on the phone.
- Platform-specific adaptation (aspect, caption length, hashtags, link handling: "link in bio" on Instagram).
- Quota guard: Instagram API posting ≈ 50 posts / 24 h per account (Meta's docs say 50 in the reference, 100 in the
  guide — Hoola reads the live `content_publishing_limit` and never plans near it).

### 5.4 Community management
- Unified inbox: Instagram comments + DMs, Facebook comments + Messenger, YouTube comments, Google reviews (existing).
- Auto-sorted: **lead** (price / availability / location / booking) → reply with the answer from her facts + a WhatsApp /
  call / booking link, and a lead card for her; **question** → answer from her FAQ / facts or ask her; **praise** → thanks
  in her voice; **complaint** → never argued in public: a short apology + "DM / call us", she is told at once;
  **spam / abuse** → hidden (trust) or suggested to hide; never deleted without her.
- Messaging window rules respected (Instagram / Messenger 24-hour reply window; no promotional messages outside it).
- Facts only from her data (prices, timings); "I'll check and reply" when it doesn't know.

### 5.5 Analytics and reporting
- Per post: reach, views, likes, comments, saves, shares, profile visits, follows, link taps.
- Per account: followers (net), reach, engagement rate, top formats / pillars / hours, audience city / age / language
  (where the platform gives it).
- Weekly pulse in chat (2 lines) + monthly PDF: Key takeaways, KPIs vs baseline, top / bottom 5 posts with why, what we
  change next month, work done. "How we'll know" envelope on every next step (like SEO PRO).
- Leads counted end to end: comment / DM → WhatsApp chat → order (from her sales data where Hoola has it).

### 5.6 Growth and paid (with Ads Sahayak)
- "Boost-worthy" flags on posts doing 2× normal; a boost plan written for her to run in Meta (Hoola does not create or
  pay for ads, as today), or handed to the Ads desk to watch.
- Collaborations: local partners / creators via the Influencer desk (ASCI `#ad` checks already there).
- UGC: customers' posts that tag her → ask permission by DM (her tap) → repost with credit; permission stored.

### 5.7 Listening (official routes only)
- Her mentions and tags (Instagram mentions / tags endpoints), hashtag search for her niche (Instagram hashtag search API,
  rate-limited), competitors' public business data via Business Discovery (followers, recent posts, engagement) — **no
  scraping, no logins as others**.
- Trend ideas from reels she shares (existing `reel` tool) and festival / season calendars.

---

## 6. 24/7 automations — what runs without her (by trust)

| Action | Seekh | Saathi | Bharosa |
|---|---|---|---|
| Read insights, comments, DMs, mentions | auto | auto | auto |
| Draft calendar, captions, designs, reply drafts, reports | auto | auto | auto |
| Publish a post / Story she approved for a slot | at the slot | at the slot | at the slot |
| Publish a post from the approved monthly plan she did not see individually | asks | does, tells her same day | does, weekly summary |
| Reply to a lead / question / praise comment or DM with facts she gave | asks | does | does |
| Hide spam / abusive comment | asks | does, tells her | does |
| Reply to a complaint, delete anything, post about price / offer not in her facts, anything paid / boosted, DM someone first, repost UGC | asks | asks | asks |
| Fake engagement, buying followers, pods, misleading claims, unlicensed music / photos | refused | refused | refused |

Daily caps per trust level (e.g. 0 / 6 / 15 posts, 0 / 40 / 150 replies), quiet hours (no posts 11 pm - 7 am unless she
sets), a **pause all posting** switch on the desk, and an emergency "stop" that also pauses every queued post.

---

## 7. Trust — how it stays safe with her brand

- **Hash-bound approval:** what she approved is exactly what goes out (caption + media hash, like Brand / Feedback today);
  any change after approval re-asks.
- **Preview = the real post:** platform-accurate preview (crop, caption cut-off, first comment) before approval.
- **Undo:** published posts can be deleted / archived on one tap where the API allows (Facebook: delete; Instagram: the API
  cannot edit media — so approval matters more, and captions are checked twice).
- **Facts guard:** prices, timings, offers, claims checked against her facts (Kalam `claims_of`, ASCI rules, Emblems Act);
  health / finance / education claims flagged.
- **Disclosure:** `#ad` / paid partnership whenever money or free product is involved; AI-made media labelled.
- **Rights:** her own media, licensed libraries, or AI she allowed; customer photos only with recorded permission.
- **Crisis mode:** a burst of negative comments or a platform warning → posting pauses, she gets one clear note.
- **Honesty:** reports show real numbers with dates; no promised "viral"; "this did not work" is allowed.
- **Data:** tokens sealed (like SEO / Ads tokens), least permissions, staff see only what she allows.

---

## 8. Connections — official routes only

| Platform | How she connects | Her account must be | Permissions (Meta names as of Nov 2026) | Newtika's one-time work |
|---|---|---|---|---|
| Instagram | "Continue with Instagram" (Instagram API with **Instagram Login**) | Business or Creator (free switch) | `instagram_business_basic`, `instagram_business_content_publish`, `instagram_business_manage_comments`, `instagram_business_manage_messages`, `instagram_business_manage_insights` | Meta app + App Review per permission (screencast each) + Business Verification of Newtika |
| Facebook Page | "Continue with Facebook" (**Facebook Login for Business**, configuration ID) → pick Page | Page admin | `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `pages_manage_engagement`, `read_insights`, `pages_messaging`, `publish_video` (+ `business_management` if Pages sit in a Business portfolio) | Same Meta review |
| YouTube | Google sign-in (built) | Owner of the channel | `youtube.upload`, `youtube.force-ssl`, `yt-analytics.readonly` (built) | In the Google OAuth app (sensitive scopes → demo video like Analytics) |
| Google Business | Google sign-in (built) | Owner / manager | `business.manage` (built) | GBP API access form |
| WhatsApp Business (her own number) | Meta **Embedded Signup** (v4; v2 retires 15 Oct 2026) | WhatsApp Business number | business token via Tech Provider | Become a Meta **Tech Provider** (verification + review) |
| LinkedIn (later) | Sign in with LinkedIn | Profile now; Company Page needs approval | `w_member_social`; Company: Community Management API | LinkedIn partner approval |
| X (later, only if asked) | Sign in with X | any | paid API tier | Monthly API cost |

Rules: one Meta app for all of Hoola (users connect to it); tokens long-lived and refreshed by the worker; pinned Graph API
version (config `meta_graph_version`, today v26.0 used by Ads); media for Instagram must sit at a public HTTPS URL during
publishing → Hoola serves short-lived signed URLs (exist for brand / motion files) and deletes them after publishing.
Until App Review passes, the Meta app runs in development mode: only people added as testers can connect — enough to
build and test everything.

---

## 9. Data model (new tables, all nullable-safe, registered in `db.init_db` + `ensure_table`)

| Table | Holds |
|---|---|
| `social_accounts` | tenant, platform, account id, handle, name, picture, token (sealed), expires, scopes, status, connected_at |
| `social_desk` | tenant, goals, pillars, rhythm, languages, hashtag bank, audience notes, baseline, latest, stamps, state (like `seo_desk`) |
| `social_posts` | the calendar + queue: slot, platforms, format, pillar, hook, caption per platform, media refs, alt text, status (idea → draft → approved → scheduled → publishing → published / failed / cancelled), approved_hash, platform post ids, permalink, errors |
| `social_metrics` | per post per day + per account per day (reach, views, likes, comments, saves, shares, follows, profile visits, link taps) |
| `social_inbox` | comment / DM id, platform, author (handle only), text, class, status, reply draft, replied text, lead link |
| `social_events` | alerts, runs, approvals, publishes (the desk feed, like `seo_events`) |
| `social_ugc` | tagged posts, permission asked / given (who, when, wording) |

Reuse: `brand_kits` (look), `kalam_settings` (voice + facts), `hired_employees` (hire + trust), `chatfiles` (reports).

---

## 10. Build phases (each ships as a version, with tests, console + phone)

| Phase | What ships | Needs |
|---|---|---|
| **0 — Meta app (Newtika, start today)** | Meta developer app "Hoola", Instagram Login + Facebook Login for Business products, privacy URL, data-deletion URL, Business Verification submitted | Owner: company documents; 1-2 weeks |
| **1 — Hire, connect, read** (SHIPPED v0.353.0) | Hire the Social Media Manager; Social Desk; Connect Instagram + Facebook Page (dev mode testers); reads last 50 posts + insights → baseline; strategy card; first 30-day calendar (Kalam + Brand drafts); everything **draft-only** | Phase 0 app in dev mode |
| **2 — Publish with her tap** (SHIPPED v0.355.0) | Approve → publish now / at a slot (IG feed, carousel, Reels, Stories; FB posts / photos / Reels); carousel builder; platform previews; quota guard; publish log; YouTube Shorts + GBP posts from the same calendar | App Review for content_publish / pages_manage_posts (screencasts) |
| **3 — Inbox** (SHIPPED v0.368.0: Instagram + Facebook; YouTube comments + Google reviews stay on their own desks for now) | Comments + DMs (IG + FB + YouTube + Google reviews) sorted; reply drafts; trust-based replies; spam hide; leads to WhatsApp / chat | Review for manage_comments / manage_messages / pages_messaging |
| **4 — 24/7 + reports** (SHIPPED v0.369.0) | Scheduler + Saathi auto-publish of the approved plan, weekly pulse, monthly PDF vs baseline, best-time engine, boost-worthy flags, crisis pause | — |
| **5 — Growth** (SHIPPED v0.370.0; Ads desk hand-off = the written boost plan, the Influencer desk serves talent managers so its checks are reused instead) | Mentions / tags / hashtag search / Business Discovery competitor watch, UGC permission flow, Influencer + Ads desk hand-offs, A/B hooks | Review for any extra permission |
| **6 — More platforms** | WhatsApp Embedded Signup (her own number), LinkedIn, X if asked | Tech Provider / LinkedIn approvals |

---

## 11. How we know it is world-class

- **Her numbers vs her baseline** after 30 / 60 / 90 days: reach per post, engagement rate, saves + shares, profile visits
  → WhatsApp / calls, followers. Shown honestly, including what did not move.
- **Response time** on comments / DMs (target: leads answered within 15 minutes in working hours).
- **Zero unapproved public mistakes** (wrong price, wrong post, wrong account) — tracked; any one is a P0 bug.
- **Effort saved:** posts she approved without editing (goal > 70% by month 2).
- **Consistency:** the planned rhythm actually kept (posts published / posts planned).
- A test bank of 50 real Indian small-business briefs (clinic, salon, tailor, bakery, coaching, kirana, gym…) scored on
  calendar quality, caption quality in Hinglish / Hindi, brand fit and claims safety (like the Design Arena).

---

## 12. Decisions needed from the owner

1. **Start Phase 0 now?** Create the Meta developer app and submit Newtika's Business Verification (I give exact steps).
2. **Platforms for launch:** Instagram + Facebook Page first (recommended); LinkedIn / X later?
3. **Default trust:** Seekh for everyone at hire (recommended), Saathi offered after 10 approvals without edits.
4. **Posting caps per day** (suggested 0 / 6 / 15 posts and 0 / 40 / 150 replies for Seekh / Saathi / Bharosa).
5. **AI pictures in posts:** allowed by default with the AI label, or only when she switches it on?
6. **WhatsApp per-user numbers (Tech Provider)** now or after Instagram + Facebook are live?
7. **Pricing:** is the Social Media Manager part of a plan, or a separate monthly hire (like a real employee's salary)?

Sources checked 1 Nov 2026: Meta Instagram Platform — Content Publishing and `content_publishing_limit`
(developers.facebook.com/docs/instagram-platform/content-publishing), Pages API posts
(developers.facebook.com/documentation/pages-api/posts), WhatsApp Embedded Signup overview + Tech Provider get-started
(developers.facebook.com/documentation/business-messaging/whatsapp/...). Graph API version and exact permission names
to be re-checked in the App Dashboard when Phase 1 starts.
