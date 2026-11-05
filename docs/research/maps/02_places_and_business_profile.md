# Places API (New) and the Google Business Profile APIs — what we can switch on, and what needs applying for

Researched 2 Nov 2026 from Google's own documentation. Sources are listed per section.

**The one-line split:**

| | Access | What it covers |
|---|---|---|
| **Places API (New)** | **enable it and go** — no form, no review | finding places: nearby, text search, details, photos, autocomplete |
| **Google Business Profile APIs** | **a human application, with a 60-day-old verified profile as a precondition** | operating HER OWN listing on Google Maps: reviews, posts, photos, hours, Q&A, insights |

Those are two different products and the second is the one a business owner usually means by *"my Google map"*.

---

## PART A — Places API (New)

### A1. Nearby Search — the shape, and its two hard ceilings
`POST https://places.googleapis.com/v1/places:searchNearby` (POST only).
Headers: `Content-Type`, `X-Goog-Api-Key`, `X-Goog-FieldMask`. The field mask is **mandatory** — *"If you omit the
field mask, the method returns an error."* No spaces allowed in the list.

| Thing | Limit |
|---|---|
| Area | **circle only** (centre + radius). No rectangle — that exists only on Text Search. It is a `locationRestriction`, a hard limit, not a bias. |
| Radius | **0.0–50,000 m (50 km)**, inclusive. Default 0.0, so it must be set. |
| Results | **`maxResultCount` 1–20.** 20 is the ceiling. |
| Paging | **none documented.** So 20 per request, full stop — wider areas mean tiling circles. |
| Ranking | `POPULARITY` (default) or `DISTANCE` |
| Type filter | `includedTypes` / `includedPrimaryTypes` / the two `excluded*`, **up to 50 per category**, values from **Table A only** (Table B types are response-only) |

Table A is the legal filter vocabulary and it is large and India-usable: `pharmacy`, `hospital`, `doctor`,
`bank`, `atm`, `hardware_store`, `electrician`, `plumber`, `real_estate_agency`, `hindu_temple`,
`south_indian_restaurant`, `wholesaler`, `building_materials_store`, `courier_service`, `tailor`, `travel_agency`,
`school`, `gym` … (full list: https://developers.google.com/maps/documentation/places/web-service/place-types)

Source: https://developers.google.com/maps/documentation/places/web-service/nearby-search

### A2. Text Search — when it beats Nearby
`POST .../places:searchText`.
- `locationBias` takes **circle or rectangle**; `locationRestriction` takes **rectangle only** and is for
  *"categorical queries only"*. One or the other, never both.
- **It has paging:** `pageSize` 1–20, `nextPageToken` → `pageToken`, up to **60 results across all pages**
  (*"although this limit is subject to change"*). Every other parameter must stay identical between pages.
- Type filter is **one** type (`includedType`) + optional `strictTypeFiltering`.

**Use Nearby** for a point + a category with no typed words ("chemists within 2 km"). **Use Text Search** when
she typed something, when more than 20 results are needed, or when a rectangle/viewport is the area.
They are **separate SKUs**, and Text Search has an **IDs-only tier that Nearby does not** — which matters below.

Source: https://developers.google.com/maps/documentation/places/web-service/text-search

### A3. THE COST TRAP, and the pattern that avoids it
Billing rule, verbatim: ***"You are then billed at the highest SKU applicable to your request."***

**And the billable event is the REQUEST, not the result.** Each Places SKU's event is *"Successful request for
&lt;tier&gt; fields"*, and *"The request is billed at the highest SKU applicable to the requested fields."* So the
field mask selects one tier and the request is charged once: **20 places in one answer is ONE billable event.**
Counting results would overstate a search roughly twentyfold. The one exception is `computeRouteMatrix`,
*"billed per ELEMENT returned from the request"* (origins x destinations). Full rates: `04_prices.md`.

So **one** Enterprise field in a request bills the **whole** request at Enterprise. And the fields a useful
result card wants are exactly the Enterprise ones:

| Field | Tier |
|---|---|
| `id` (place_id), `name` | Essentials (IDs Only) on Details/Text Search — but **Pro** on Nearby |
| `displayName`, `businessStatus`, `primaryType`, `googleMapsUri` | Pro |
| `formattedAddress`, `location`, `types` | Essentials on Details, **Pro** on Text/Nearby |
| **`nationalPhoneNumber`, `websiteUri`, `rating`, `userRatingCount`, `regularOpeningHours`** | **Enterprise** |
| `reviews`, `editorialSummary`, `generativeSummary` | Enterprise + Atmosphere |

**Nearby Search has no Essentials tier at all** — every field on it is Pro or above.

**The pattern, and it must be in from day one:**
1. **List pass at Pro** — name, address, location, type. India: $9.60/1,000, **35,000 free a month**.
   (Essentials IDs-Only is free and unlimited but returns no `displayName` at all — only the resource name and
   id — so it cannot render a list on its own.)
2. **Details pass at Enterprise** — `GET .../places/PLACE_ID`, only for a place she actually opens.
   India: $6.00/1,000, **7,000 free a month**.

**The gain is the free allowance, not the unit price.** Enterprise's allowance is five times scarcer (7,000
against 35,000), so keeping browsing on Pro sits far further from ever paying. Honestly stated: if she opens a
place on *every* search, the split costs slightly **more** than one rich Enterprise search
(9.60 + 6.00 against 10.50 per 1,000). Pro-first is the right default because most searches end without
opening one particular place — but it is a judgement, not a free lunch.

Place Details adds **no field** that search cannot return (the only documented exclusivity runs the other way —
`routingSummaries` is search-only). Its value is purely **economic**: it has the cheap tiers Nearby lacks, and it
buys the expensive fields one place at a time.

Sources: https://developers.google.com/maps/documentation/places/web-service/data-fields ·
https://developers.google.com/maps/billing-and-pricing/sku-details/places

### A4. Autocomplete and its session billing
`POST .../places:autocomplete`. `sessionToken` *"groups the query and selection phases ... into a discrete
session for billing purposes"*; **v4 UUID recommended**; **single use** — *"Once a session has concluded, the
token is no longer valid"*, and reusing one means *"each request being billed individually"*. Omitting it bills
each request separately.

Two SKUs, and the choice is a real one:
- `Autocomplete Requests` — Essentials, free cap **10,000** (per request)
- `Autocomplete Session Usage` — Essentials, free cap **Unlimited** (per session)

Google's own guidance: per-request is cheaper when users pick a prediction within about **four** keystrokes'
worth of requests; per-session is recommended above roughly **100,000** calls a month.

### A5. Quotas and the free allowance
- **6,000 QPM for Places**, and *"The rate limit per minute is per API method per project"* — each method has
  its own quota (unlike legacy Places, which shared one).
- **No billing account attached = 1 request per day.** That is the whole quota.
- **Free caps are per SKU per month, not one pooled credit:** commonly 10,000 Essentials / 5,000 Pro /
  1,000 Enterprise, and **Unlimited** for Place Details Essentials (IDs Only), Text Search Essentials (IDs Only)
  and Autocomplete Session Usage.
- **NOT FOUND:** any mention of the old $200 monthly credit, or a replacement for it, on the current pricing
  page. Do not assume it still exists.
- Volume tiers for Places (New): 0–100k / 100,001–500k / 500,001–1M / 1,000,001–5M / 5M+, aggregated across all
  projects on the billing account. India and Global price lists are **separate** — read the India one.

Sources: https://developers.google.com/maps/faq · https://developers.google.com/maps/billing-and-pricing/pricing

---

## PART B — Google Business Profile APIs (her own listing)

### B1. It is eight APIs, and half the useful ones are still on the legacy v4 endpoint

| Job | API |
|---|---|
| accounts, admins, invitations | **Account Management API** v1 |
| locations, hours, categories, attributes | **Business Information API** v1 |
| impressions, calls, website clicks, search keywords | **Business Profile Performance API** v1 (read only) |
| verification | **Verifications API** v1 |
| booking / order / delivery links | **Place Actions API** v1 |
| hotel amenities and policies | **Lodging API** v1 |
| Pub/Sub notification settings | **Notifications API** v1 |
| **reviews, local posts, Q&A, photos, food menus** | **Google My Business v4.9** — `https://mybusinessaccountmanagement…`/`mybusiness.googleapis.com/v4/...` |

**NOT FOUND:** any standalone "Reviews API", "Posts API", "Q&A API", "Media API" or "Food Menus API". All four
live under v4.9. Build against v4 for those and expect it to stay that way until Google says otherwise.

Source: https://developers.google.com/my-business/ref_overview

### B2. The access gate — this is the long pole, and it is not ours to shorten
A Cloud project is **not** enough. (The phrase "not available to all users" is **not** on the page — checked. What the page actually sets out is a list of eligibility requirements and an application.)

Preconditions:
1. *"Manage a Google Business Profile that is verified and active for 60+ days."*
2. *"Have a website representing the business listed on the GBP."*
3. An **Organization account** in Business Profile.

(Both quotes verified verbatim on the page, 2 Nov 2026.)

Then: submit **"Application for Basic API Access"** at `https://support.google.com/business/contact/api_default`
with the Cloud **Project Number**, from an email that is an **owner or manager** on the profile and **matches the
website domain**. Then a human reviews it.

**How to tell if it worked:** the Business Profile quota in Cloud Console, in the page's own words —
*"If your quota is 0 QPM (Queries Per Minute), your project has not yet been approved."* /
*"If your quota is set to 300 QPM, your project is approved."* The limits page adds that at 0 you must **not**
request an increase, but apply for Basic API Access instead.

**NOT FOUND: any published review turnaround.** So this cannot be promised on a date, and nothing in Part B can
start until the quota flips.

**Cost: none.** The API is *"available to registered users at no charge."*

Sources: https://developers.google.com/my-business/content/prereqs ·
https://developers.google.com/my-business/content/limits

### B3. What it can and cannot do once approved

**Reviews** (v4): read one, read a page, or `batchGetReviews` across many locations at once. **Reply** —
`updateReply` (PUT) creates or replaces; `deleteReply` removes the reply.
**A review itself cannot be deleted. No such method exists.** Promise replying and reporting, never removal.

**Local posts** (v4): create / patch / delete, `topicType` EVENT or OFFER, CTA `actionType` one of BOOK, ORDER,
SHOP, LEARN_MORE, SIGN_UP, CALL, plus photo media. But: ***"Product Posts cannot be created using the Google My
Business API at this time."***

**Q&A** (v4): read everything; **write only your own** — `questions.patch`/`delete` are scoped to *"a question
written by the current user"*, and answers upsert/delete only the user's own. A customer's question cannot be
deleted.

**Media** (v4): upload, patch, delete **own** media. **Customer-contributed photos are read-only.**

**Locations** (v1): `readMask` is **required** on get; `updateMask` **required** on patch. A location must be
**verified to appear on Search and Maps** (unverified ones work in Ads only). Google may edit a listing itself —
reconcile through `:googleUpdated` and the accept/reject flow.
**Hard cap: "Edits: 10 per minute per Google Business Profile (cannot be increased)."** Create Location and
SearchGoogleLocation are **300/day**; Update Location 10,000/day. Everything else defaults to **300 QPM**.

**Performance** (v1, read only): `BUSINESS_IMPRESSIONS_*` (desktop/mobile × maps/search), `CALL_CLICKS`,
`WEBSITE_CLICKS`, `MESSAGING_CLICKS`, `BUSINESS_DIRECTION_REQUESTS`, `BUSINESS_BOOKINGS`,
`BUSINESS_FOOD_MENU_CLICKS`, plus **the search keywords people used to find her**. (`BUSINESS_CONVERSATIONS` and
`BUSINESS_FOOD_ORDERS` are deprecated.) **NOT FOUND:** date-range limits.

### B4. The policies that are product requirements, not legal boilerplate
From https://developers.google.com/my-business/content/policies:

Every quote below was re-verified verbatim against the live page on 2 Nov 2026.

- ***"you must not automate or trigger review replies, Q&As, listing creations, listing edits, or other actions
  without the user's prior specific and express consent."*** And twice over: *"If you respond to reviews on
  behalf of your end-client, you must receive their authorization first."* / *"If you post or respond to
  questions on behalf of your end-client, you must receive their authorization first."*
  The word **"AI" does not appear anywhere on the page** — checked. The binding words are **"automate"**,
  **"prior specific and express consent"** and **"authorization"**. So: **an AI that drafts is fine; an AI that
  posts unattended is a violation.** Draft-plus-her-tap, per reply — which is exactly Hoola's existing
  confirm-card rule.
- **`GoogleLocations` is for merchants you already have a relationship with**: *"You're only allowed to use the
  GoogleLocations endpoint to find the status of locations of merchants that already have a business relationship
  with your company, and only to use the endpoint to create or claim those locations on Business Profile."* Then
  the sentence that settles requirement #3 from a second direction entirely:
  ***"Use of this endpoint for any other purpose, which includes lead generation or other analysis, is against
  Google's policies and will result in immediate revocation of your API access."***
- **Caching:** *"You cannot pre-fetch, cache, index, or store any content provided through the Business Profile
  APIs ("Content") for use outside of your Business Profile project except for limited amounts of Content."*
  *"It must be stored temporarily for no more than 30 calendar days."* *"It cannot be manipulated or aggregated
  in any way."* So no long-lived mirror of GBP data, and no aggregating it.
- *"provide notice to the end-client of the change within 48 hours after the change is made."*
- Offboarding: *"you have seven business days to provide them the ability to disassociate their Business Profile
  account from your services and developer project, and regain exclusive control of their Business Profile
  account(s)."*
- **One approved project serves all clients** — *"you cannot require them to apply for their own Business Profile
  project"* — and *"You cannot provide indirect access to your Business Profile project."*
- The tool *"must not replicate the Business Profile interface's look and feel"*; attribution unaltered; no
  implying a Google partnership without written approval.
- A live or equivalent **demo account within seven days** of Google asking.

### B5. The agency shape
`Account Management API` is the mechanism: the client **invites** Hoola's account as manager or owner →
`accounts.invitations.list` / `accept` → her locations are then operated under that account or location group.
`accounts.admins.*` and `locations.admins.*` manage who holds what. Only `accountName` is editable on an account,
and only for `BUSINESS`-type accounts.

---

## What this means for the build

1. **Everything about *finding* places can ship now**, on Places API (New), with no one's permission — provided
   the IDs-first / Details-on-open split is built in from the first line, because the useful fields are all
   Enterprise.
2. **Everything about *operating her own listing* is gated** behind a human application with a 60-day-old
   verified profile. Start that application the same week; it is the long pole and no amount of code shortens it.
3. **Build Part B against the documented shapes while waiting** — they are stable (v1 for accounts / locations /
   performance / verifications, v4 for reviews / posts / Q&A / media / menus) — with the approval tap wired in
   from the start, so the day the quota reads 300 QPM it deploys rather than gets redesigned.
4. **Lead generation is named twice now.** The Platform ToS forbids building a listings or advertising product
   (§3.2.3(d)(iii) — see `01_terms_caching_and_leads.md`), and the Business Profile policies say using
   `GoogleLocations` for lead generation causes immediate revocation. Two independent documents, same answer.
