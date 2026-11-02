# Google Maps for Hoola — the plan

Owner's asks:
- 2 Nov 2026: *"BEFORE THIS LETS WORK ON GOOGLE MAPS FOR HOOLA --- MAKE A PLAN"*
- 2 Nov 2026: *"WE WANT MAP FOR ::: 1) USER CAN USE A EXISTING GOOGLE MAP MANUALLY, AI WILL DO ALL THOSE THINGS
  2) API FOR NEAR BY THINGS 3) GOOGLE MAP LEAD GENERATION SCRAPER ------- ETC OBJECTIVE HOOLA AI CAN PERFORM
  ALL MAP TASK"*

Plan only. Nothing is built until she says GO on a phase.

Everything below rests on `docs/research/maps/` — three registers read out of Google's own documents on 2 Nov,
with every load-bearing quote re-verified by hand. Read `docs/research/maps/00_INDEX.md` first.

---

## 1. Her three requirements, answered straight

| # | What she asked for | Answer |
|---|---|---|
| **1** | *use an existing Google map manually, AI does all those things* | **Yes for her business listing** (after an application). **Read-once for a My Maps map.** **No route for saved lists.** |
| **2** | *API for nearby things* | **Yes, in full, this week.** No permission needed from anyone. |
| **3** | *Google Map lead generation scraper* | **Cannot be built as asked.** Refused by two separate Google documents and by her own non-negotiable rules. **The objective is reachable another way** — §5. |

### Requirement #1 splits three ways, and only she knows which she meant
- **Her business's listing on Google Maps** — reviews, posts, photos, hours, Q&A, the numbers on how people
  found her. **Fully operable** through the Google Business Profile APIs. This is what a business owner usually
  means by "my Google map", and it is the richest of the three. Gated: see §4.
- **A My Maps custom map** she drew herself (google.com/maps/d/). Hoola can read its contents **once**, with her
  consent, via the Data Portability API (KMZ), and can list her maps via Drive. **There is no API to write to it
  or keep it in sync — none.** So the honest shape is: she hands it over once, and from then on Hoola owns the
  data and draws it itself. Anything promising "Hoola will keep editing your My Maps map" could only be done by
  driving the web app, which is scraping, and would break.
- **Her saved places and lists** (Want to go, Favourites, starred). **No API at all**, not even in Data
  Portability. Takeout export by her own hand, and even the export's file format is undocumented. The honest
  answer here is to say there is no route.

---

## 2. What exists today, measured

`server/app/maps.py` is 10 KB, is the single door to Google, and calls **three** APIs:

| In use | Endpoint | What it gives |
|---|---|---|
| Places API (New) | `places:searchText` | text search near a point |
| Routes API | `directions/v2:computeRoutes` | one origin → one destination, live traffic |
| Geocoding API | `maps/api/geocode/json` | address → coordinates |
| (no key needed) | `google.com/maps/dir/`, `/maps/search/` | deep links that open her Google Maps app |

Three agent tools: `maps_search`, `maps_directions`, `maps_navigate`. Six modules use them: `propagent`,
`fleet`, `helpdesk`, `phonedoc`, `bazar_tools`, `main`.

**And no cache, no daily cap, no budget anywhere in the file.** Every call is billed; the field mask is set
correctly so the per-call SKU is not reckless, but the *number* of calls is unbounded, and a loop over a list of
addresses bills every row.

---

## 3. Every manual Google Maps task, and whether Hoola can do it

This is requirement #1 read as *"Hoola AI can perform all map tasks"* — the full inventory, so nothing is
quietly left out.

| What she does by hand | Official route | In Hoola now | Phase |
|---|---|---|---|
| search a place by name | Places Text Search | **yes** | — |
| "chemist near me" | Places **Nearby Search** | partial | **3** |
| type an address, get suggestions | Places Autocomplete | no | **6** |
| a place card: hours, phone, website, photos | Place **Details** + Photos | partial | **3** |
| directions, car / bike / walk / transit | Routes computeRoutes | **yes** | — |
| compare times to several places | Routes **computeRouteMatrix** | no | **4** |
| add stops and reorder them | **Route Optimization API** | no | **5** |
| start navigation on the phone | maps deep link (free) | **yes** | — |
| drop a pin, read coordinates | Geocoding + **reverse** geocoding | partial | **6** |
| **see the map, pan and zoom** | **Dynamic Maps** (Google's own) | **no** | **2** |
| a map picture in a PDF or WhatsApp | **Static Maps** | no | **7** |
| look at a street | **Street View Static** (metadata free) | no | **7** |
| traffic now vs typical | Routes + `departureTime` | partial | **4** |
| is this address deliverable | **Address Validation** | no | **6** |
| **reply to reviews of her business** | **Business Profile v4** | no | **8** |
| **update her listing, post, photos** | **Business Profile** v1 + v4 | no | **8** |
| **how people found her business** | **Performance API** | no | **8** |
| her own pins and areas on a map | **Datasets API** or **Data layer** | no | **9** |
| read a My Maps map she drew | **Data Portability** (KMZ, once) | no | **9** |
| rooftop solar potential | Solar API | no | 10 |
| elevation / slope | Elevation API | no | 10 |
| air quality, pollen | Air Quality / Pollen | no | 10 |
| clean a GPS trail | Roads snap-to-road | no | 10 |
| her saved lists | **no route** | — | **never** |
| write to her My Maps map | **no route** | — | **never** |
| delete a bad review | **no route** (reply only) | — | **never** |

Three rows say **never**, and they say it on Google's authority, not ours. Those are the only gaps in "all map
tasks", and the plan names them rather than hiding them.

---

## 4. The two halves have very different lead times

**Finding places** — Places API (New). Enable it, attach billing, create a key, go. No form, no review.
(Without a billing account the quota is **1 request per day**, which is the whole quota.)

**Operating her own listing** — every Business Profile API is behind a **human application**:
1. *"Manage a Google Business Profile that is verified and active for 60+ days."*
2. *"Have a website representing the business listed on the GBP."*
3. An Organization account; then the **"Application for Basic API Access"** form, from an email that is an
   owner/manager on the profile and matches the website domain, carrying the Cloud **Project Number**.

**No published review turnaround.** Approval appears as the Cloud Console quota going from **0 QPM** to
**300 QPM**. The API itself is **free**.

**So: the application is submitted in week one, and the code is written against the documented shapes while it
waits.** Nothing we build shortens that queue, and it must not be promised on a date.

---

## 5. Requirement #3 — what is refused, and what replaces it

### What is refused, and why
| The thing | Clause |
|---|---|
| store business names / addresses / phones | ToS §3.2.3(b) + §3.2.3(a)(iii) *"copy and save business names, addresses, or user reviews"* |
| bulk-pull places to build a list | §3.2.3(a)(ii) |
| territory / point-in-polygon analysis on stored coordinates | §3.2.3(c)(iv) — named as an example |
| train a model on any of it | §3.2.3(c)(vii) |
| build a directory, listings or advertising product | §3.2.3(d)(iii) |
| hand the data to her customers, or resell it | §3.2.3(a)(i), §3.2.1(b) |
| bulk outreach from it | AUP, *"unsolicited mass email, promotions, advertisements"* |
| use `GoogleLocations` for it | GBP policies: *"lead generation or other analysis … will result in immediate revocation of your API access"* |
| scrape maps.google.com instead | consumer terms *"copy the content"* / *"mass download or create bulk feeds"*; `robots.txt` `Disallow: /maps/` |

**The cost of ignoring this is not a fine.** ToS §5.2(d) allows **immediate suspension with no notice and no
cure period** for any §3.2 breach — the Maps key dying mid-business-day across every Hoola feature that uses it.
Plus §14: the customer **indemnifies Google**. And it breaks the first line of Hoola's own NON-NEGOTIABLE RULES:
*"Official routes only: no scraping, no unofficial MCP."*

### What replaces it — the live search-and-act desk
**The limit is on keeping, not on getting.** Places returns name, address, phone, website, rating and hours, and
§14.1 expressly permits showing all of it **without** a Google map. So:

1. She searches — by trade and area ("hardware shops in Akola"), using the 50-type filters.
2. Results show on screen, **with Google attribution**, every field visible.
3. She acts **in the session** — ring it, open the website, or write her own note.
4. Hoola persists **only** the `place_id` (permitted indefinitely) **plus what she herself typed, confirmed or
   corrected**. That is her own CRM row; Google's terms do not touch it.
5. Google's fields are **re-fetched on every view**, never read back from a table. The dedicated
   **"Places Details - ID Refresh"** SKU exists for exactly this and is free.

She loses the exportable spreadsheet. She keeps the workflow: find the businesses, work through them, remember
which ones she has spoken to and what was said.

### Two guards this needs, and one of them is in her own code
- **`server/app/campaigns.py:99`** reads `if ll.has_consent_column and only_opted_in:` — so a list **with** a
  consent column is filtered to opted-in rows, but a list with **no** consent column is **not filtered at all**.
  Any list Hoola generates itself must be marked no-consent **and explicitly blocked** from the campaign path.
  It must not inherit "no consent column = send to everyone". **This matters more than Google's terms do**,
  because it is the path that would actually send the messages.
- **TRAI's UCC / DLT regime and the DPDP Act** gate the outreach regardless of where the names came from. A
  separate check, not covered by this research.

### If she wants the exportable list anyway
Then it has to come from a **licensed B2B data vendor whose terms permit resale** — not from Google. That is a
real option and a commercial decision; it is not something code can route around.

---

## 6. The cost trap, and the pattern that avoids it

Billing rule, verbatim: ***"You are then billed at the highest SKU applicable to your request."***
One Enterprise field bills the **whole** request at Enterprise — and the fields a useful result card wants are
exactly the Enterprise ones: **phone, website, rating, review count, opening hours**.
**Nearby Search has no cheap tier at all** — every field on it is Pro or above.

**So the split goes in from the first line of code:**
1. **List pass** — Text Search at **Essentials (IDs Only)** (free cap **Unlimited**) or Pro: ids, names,
   addresses.
2. **Details pass** — one `GET places/PLACE_ID` at **Enterprise**, only for the place she actually opens.

Asking for phone and rating across a 20-row page bills 20 rows at Enterprise; asking on the one row she tapped
bills one. Same screen, a twentyfold difference.

Ceilings to design around: **Nearby Search = circle only, radius ≤ 50 km, 20 results, no paging.**
**Text Search = 60 results across pages**, and it is the only one with an IDs-only tier.

---

## 7. The map card — and the correction to the first version of this plan

**The first draft of this plan recommended MapLibre with free OpenStreetMap tiles plus Google data. That is a
licence breach and the recommendation is withdrawn.**

ToS §3.2.3(e): *"Customer will not use the Google Maps Core Services with or near a non-Google Map … For
example, Customer will not (i) display or use Places content on a non-Google Map."*
SST §14.2: *"Customer must not use Google Maps Content from the Places API in conjunction with a non-Google
map."*

There are exactly **two** legal shapes, and the choice between them is the one real decision here:

| | What she sees | Cost |
|---|---|---|
| **A — no map** | results as rich cards, with distance and attribution; a tap opens Google Maps | **free** (§14.1 expressly allows it) |
| **B — a Google map** | pins and route lines on a real Google map inside Hoola | **Dynamic Maps** SKU: 10,000 loads free a month, then $7.00/1,000 down to $0.53 |

MapLibre stays where it is — in `console/build.js`, drawing maps on *her customers'* websites, where no Google
data is involved. It must not be reused for Google results.

**My recommendation: A first, B behind her switch.** Option A is free, ships immediately and covers most asks;
Option B is worth real money for fleet, courier and site work where seeing the pins *is* the answer. Building A
first costs nothing if she later wants B.

---

## 8. Build phases

| Phase | What ships | Why here |
|---|---|---|
| **1 — PAISA PEHLE** | the priced / capped / cached client: per-call SKU price table, `MAPS_DAILY_INR` cap that **refuses** rather than overspends, a cache that stores **only `place_id` (kept) and lat/lng (30-day TTL, auto-deleted)**, and a usage line she can see | the only gap that can cost her money while she sleeps — and the cache's shape is now set by the terms, not guessed |
| **2 — NAKSHA DIKHE** | the result card: rich place cards with attribution and distance, **no map** (Option A). Google map (Option B) behind a setting, off by default | the biggest visible gap, at zero licence risk and zero cost |
| **3 — PAAS KYA HAI** | **requirement #2**: Nearby Search with the 50-type filters + Place Details on open, on the IDs-first/Details-on-open split; new tools `maps_nearby`, `maps_place` | her literal second ask, and the foundation of #3's replacement |
| **4 — SABSE PAAS** | Routes **computeRouteMatrix** → "nearest of these N" as a first-class answer, into field_service / fleet / courier / helpdesk | the most asked geographic question in her business |
| **5 — DIN KA RASTA** | **Route Optimization**: the day's stop order with time windows and capacity, as a card she approves | turns courier/logistics from a list into a plan; replaces v0.346's "nearest first" where it is wrong |
| **6 — PATA PAKKA** | Autocomplete (session-billed), reverse geocoding, **Address Validation** with Indian address reality (landmark addresses, PIN checks) | stops a bad address becoming a failed delivery |
| **7 — KAAGAZ PAR** | **Static Maps** in `docstudio` PDFs and WhatsApp, + **Street View Static** (check with the **free** metadata SKU before paying for an image) | a map in a document beats a link, and needs no app |
| **8 — APNI DUKAAN** | **requirement #1, the real one**: Business Profile — reviews read + **drafted** replies, posts, photos, hours, Q&A, and the Performance numbers. **Every write is draft-plus-her-tap**, per the policy's *"prior specific and express consent"* | the richest half of her ask; starts the day the quota reads 300 QPM, so the application goes in at Phase 1 |
| **9 — APNA NAKSHA** | her own pins and areas: **Data layer** (`addGeoJson` from Hoola's own backend — her data never leaves her server) with the **Datasets API** as the Google-hosted alternative; + one-shot My Maps import via Data Portability KMZ | replaces My Maps properly, and better, since writing to My Maps has no route |
| **10 — BAAKI SAB** | Solar, Elevation, Air Quality / Pollen, Roads snap-to-road, Time Zone | the remaining "all map tasks", once the daily ones work |
| **11 — PROOF** | a maps card like the coding and tool cards: fixed geographic questions with known answers, scored, **and the rupees each answer cost** | the only honest way to claim it works and to see the bill |

---

## 9. What it will not do

- **Official routes only.** No scraping of Google Maps pages, no undocumented endpoints (the
  `maps/d/kml?mid=` link included), no screenshotting tiles to dodge a licence.
- **No storing what the terms forbid.** Only `place_id` and a 30-day lat/lng. Names, addresses, phones,
  ratings and hours are **shown live and never written down**.
- **No Places data on a non-Google map.** §3.2.3(e). Either a Google map or no map.
- **No exportable, sellable list of businesses.** §3.2.3(d)(iii).
- **No unattended writes to her listing.** *"you must not automate or trigger review replies, Q&As, listing
  creations, listing edits … without the user's prior specific and express consent."* Draft, then her tap.
- **Never a guessed distance, ETA or stop order.** If the API cannot answer, Hoola says so. A wrong ETA looks
  exactly as confident as a right one.
- **No live tracking of a person without their knowing.** A driver's trail is a work record on her own fleet.
- **Her key is hers.** CLAUDE.md stands: *don't modify her FNW Flow Maps key.* This plan uses
  `GOOGLE_MAPS_API_KEY` and touches nothing else.

---

## 10. Decisions I need from her

1. **Which "existing Google map" did she mean** — her **business listing** on Google Maps (the rich one, needs
   the application), a **My Maps** map she drew, or her **saved lists** (no route)? This picks Phase 8 vs 9 and
   is the one answer I cannot infer.
2. **Map card: Option A (no map, free) or Option B (Google map, paid)?** I recommend A now, B behind a switch.
3. **A daily rupee cap for Maps**, for Phase 1 to enforce. Studio and Arena have one; Maps does not.
4. **Does she have a Google Business Profile that is verified and 60+ days old, with a website?** If yes, the
   application can go in this week and Phase 8 becomes real. If not, that clock starts first.
5. **On requirement #3**: accept the live search-and-act desk (§5), or does she want a licensed data vendor
   priced instead? If she wants the exportable list from Google anyway after reading §5, that is her call to
   make explicitly — it will be recorded here as her decision, not built quietly.

---

## 11. What I would do first if she just says "GO"

**Phases 1, 2 and 3 as one version** — the bill gets a cap and a terms-shaped cache, she finally sees results
as proper cards, and "what's near here" works properly with the cheap/expensive split built in.

That is her requirement #2 delivered in full, requirement #3's replacement standing up, and it depends on **none
of the decisions above except §10.2** — and even that one defaults safely to the free option.

**And on day one, in parallel: submit the Business Profile API application.** It is the long pole for
requirement #1 and no amount of code shortens it.
