# Google Maps Platform — what may be stored, and what a "lead list" may be

Researched 2 Nov 2026 from Google's own documents. Every claim below was read out of the live page and the
four load-bearing quotes were re-verified by hand against the downloaded HTML, not trusted to a summary.

**Scope caveat recorded up front:** everything here is the **non-EEA** Terms. The Service Specific Terms open
with *"These Service Specific Terms apply to Customers who do not have a billing account address in the
European Economic Area."* If the billing address is ever in the EEA, re-run this against
`https://cloud.google.com/terms/maps-platform/eea/maps-service-terms`.

Sources, all primary:
- Maps Platform ToS — https://cloud.google.com/maps-platform/terms
- Maps Service Specific Terms (SST) — https://cloud.google.com/maps-platform/terms/maps-service-terms
- Acceptable Use Policy — https://cloud.google.com/maps-platform/terms/aup
- Places API policies — https://developers.google.com/maps/documentation/places/web-service/policies
- Place IDs guide — https://developers.google.com/maps/documentation/places/web-service/place-id
- Google Maps End User Additional Terms (consumer), last modified 27 Jan 2026 — https://www.google.com/help/terms_maps/
- Google Terms of Service — https://policies.google.com/terms · https://www.google.com/robots.txt

---

## 1. The one sentence that decides the whole thing

**Maps Platform is licensed as a live lookup service, not as a data source.**

ToS §3.2.3(b): *"**No Caching.** Customer will not cache Google Maps Content except as expressly permitted
under the Maps Service Specific Terms."*

So storage is forbidden **unless a specific permission exists**, and silence is a prohibition. That makes the
question "what does the SST expressly permit for Places?" — and the answer is short.

## 2. What may be stored, exactly

The Places section of the SST is **§14.1, §14.2, §14.3 and nothing else** (verified: §15 is the next heading).

| Field | May it be stored? | Authority |
|---|---|---|
| `place_id` | **Yes, indefinitely** (refresh if over 12 months old — a documentation recommendation) | SST §A.3; Places policies: *"the place ID ... is exempt from the caching restrictions. You can therefore store place ID values indefinitely."* |
| `location` (lat/lng) | **30 consecutive calendar days**, then must be deleted | SST §14.3 |
| name, address, phone, website, rating, review count, hours, reviews, photos | **No permission exists at all** | SST §14 is exhaustive; ToS §3.2.3(b) makes absence a prohibition |

ToS §3.2.3(a) *No Scraping* then names those very fields: *"(ii) bulk download ... places information;
(iii) copy and save business names, addresses, or user reviews."*

**The "30 days" belief is a trap.** There is no global 30-day allowance to store business data under. 30 days
is the recurring period for **lat/lng only**, repeated per-API (Geocoding §6.3.1, Directions §4.3, Roads §17.3,
Routes §19.3, Route Optimization §18.3…). Other APIs have their own clocks — Air Quality 1 hour, Pollen 24 h or
365 days by content type, Weather tiered 1 h / 24 h / 240 h / 30 days. A business name does not get 30 days;
it gets zero.

### The real escape hatch: data the user herself typed
- **Geocoding §6.3.2** permits indefinite caching of `lat`, `lng`, `formatted_address` and the structured
  address — but *"solely to support the direct, End User facing functionality of the Customer Application that
  initiated the request"*, *"only where the cache is not used as a replacement for making an additional call"*,
  and *"logically isolated to the specific End User ... must not be used across multiple End Users."* A shared
  prospect table fails the third condition outright.
- **Address Validation** Table 1.3.2 permits 30 days **or** replacement *"with End User data provided through
  End User confirmation or correction"* — once the user confirms or corrects an address it is **her** data, not
  Google Maps Content, and the deletion clock stops.
- **Solar §20.2** shows the same principle: the deletion duty *"does not apply to Solar Data incorporated into
  fixed media (e.g. energy system design, feasibility study, commercial proposal...)"*.

**Generalisable rule: what the user typed, confirmed or corrected is hers and may be kept. What Google returned
may not.** And **NOT FOUND**: any Places equivalent of §6.3.2 or the Address Validation carve-out. The
Geocoding allowance does **not** carry across to Places.

## 3. A Google-Maps-sourced lead list — the answer, clause by clause

| The thing | Verdict | Clause |
|---|---|---|
| Store business names / addresses / phones in our DB | **Prohibited** | §3.2.3(b) + §3.2.3(a)(iii) |
| Bulk-pull places to assemble a list | **Prohibited** | §3.2.3(a)(ii) |
| Run stored coordinates through territory / point-in-polygon analysis | **Prohibited** — named as an example | §3.2.3(c)(iv) |
| Train or fine-tune a model on any of it | **Prohibited** — named as an example | §3.2.3(c)(vii) |
| Build a directory / listings product, or an advertising product | **Prohibited** | §3.2.3(d)(iii): *"use the Google Maps Core Services in a listings or directory service or to create or augment an advertising product"* |
| Hand the extracted data to her own customers, or resell it | **Prohibited twice** | §3.2.3(a)(i) *"reshare, or rehost"*; §3.2.1(b) *"sell, resell, sublicense, transfer, or distribute"* |
| Bulk outreach off such a list | **Prohibited** | AUP: *"to generate, distribute, publish or facilitate unsolicited mass email, promotions, advertisements, or other solicitations ('spam')"* |
| Enrich a Places record against her own contact DB to derive more personal data | **Prohibited without consent** | AUP: *"to combine any Google data with any personal information held by You to derive additional personal information without user consent"* |
| A human reads one result and rings that business there and then | **Genuinely unaddressed** — arguably fine; stops being ambiguous the moment the number is saved for later | — |

§3.2.3(d)(iii) is the single most relevant sentence: a sellable prospect list **is** a listings service and
**is** an advertising product. Reinforced by the licence's own scope — it runs only to a *"Customer
Application"*, defined in §20 as something *"that has material value independent of the Services"*, restated in
§3.2.3(d) as *"substantial, independent value and features beyond the Google products or services."* A product
whose value **is** the Google data fails that definition.

Note on citation hygiene: the phrase *"business listings database, mailing list, or telemarketing list"* is
**not** in the Platform ToS — it is in the **consumer** Maps terms. Do not cite a "no database" clause to the
Platform ToS; cite §3.2.3(a) and §3.2.3(c).

## 4. Scraping maps.google.com instead — closes, it does not open

Consumer Maps terms §2, a **condition of the licence**: *"copy the content"* and *"mass download or create bulk
feeds of the content (or let anyone else do so)"* — both **unconditional**. (The fourth bullet, which names
*"business listings database, mailing list, or telemarketing list"*, carries a trailing qualifier *"for use in a
service that is a substitute for, or a substantially similar service to, Google Maps"* — so cite bullets 2 and 3,
not bullet 4 alone.)

Google ToS forbids *"using automated means to access content from any of our services in violation of the
machine-readable instructions on our web pages (for example, robots.txt files...)"*, and
`https://www.google.com/robots.txt` carries, verified on the day: **`Disallow: /maps/`**, **`Disallow: /maps?`**
(narrow `Allow:` exceptions only for `/maps?q=`, `/maps?daddr=`, `/maps?hl=`), **`Disallow: /mapslt?`**.

Every modern place page lives under `/maps/`. So the website route breaches **two** documents rather than one,
and headless-browser automation of Maps is squarely inside it. There is no "the API is restrictive so we scrape
the site" road.

## 5. What happens on breach — immediate, not a warning

- ToS §5.2(d): Google *"may **immediately** Suspend Customer's use of the Services if ... Customer violates
  Section 3.2 (License Requirements and Restrictions)"*. Every clause above lives in §3.2. **No notice, no cure
  period.** (The 24-hour notice in §5.1 is only for AUP violations.)
- §10.2: *"Google may terminate Projects or Customer's access to Services"*.
- §3.2.2(c): *"At Google's request, Customer will submit Customer Application(s) and Project(s) to Google for
  review"*; SST §A.4(b) adds an independent audit on 30 days' notice.
- §14: the customer **indemnifies Google** for *"Customer's use of the Services in breach of any use or license
  restrictions"*.
- §18.13: §3.2 **survives termination**, and §10.6(c) requires deletion by the termination date.

The practical cost is not a fine — it is the Maps key dying mid-business-day across every Hoola feature that
uses it, with no warning.

## 6. What IS allowed — and it is more than it first appears

- **Query as often as she likes, and show every field.** Text Search returns `displayName`,
  `formattedAddress`, `location`, `primaryTypeDisplayName` (Pro) and `internationalPhoneNumber`,
  `nationalPhoneNumber`, `rating`, `userRatingCount`, `websiteUri` (Enterprise). **The constraint is on
  retaining, not on showing.**
- **No Google map needed.** SST §14.1: *"Customer may use Google Maps Content from the Places API in Customer
  Applications without a corresponding Google Map."* Geocoding §6.1 the same. The prohibition is the
  opposite one — §14.2 / §3.2.3(e) forbid showing it **with a competitor's** map.
- **`place_id` stored indefinitely is the architectural answer.** Keep the ID as a persistent handle, re-fetch
  the details live on every view. There is a dedicated **"Places Details - ID Refresh"** SKU and the guide says
  *"You can refresh Place IDs at no charge"*; *"To refresh results in the event of an obsolete place ID, store
  the original request that returned that place ID."*
- **Attribution is mandatory and specific:** ToS §3.2.2(b) *"Customer will not modify, obscure, or delete such
  attribution"*; without a map the **Google logo** must appear; attributions for details, photos and reviews
  must be retrieved and displayed with author information and links; placement *"near the top or bottom of the
  content, and within the same visual container"*; and *"Don't misrepresent Google Maps by attributing it with
  non-Google Maps Platform content"* — so the UI must visibly separate Google-sourced rows from her own.
- **Required plumbing:** ToS §3.2.2(a)(i) — her app's terms must say it includes Google Maps features and that
  their use is subject to the Google Maps End User Additional Terms and the Google Privacy Policy.

## 7. The compliant shape of a "lead" feature

A **live search-and-act tool**, not a list:

1. She searches. Results show with attribution, every field visible.
2. She acts **in the session** — ring it, open it, write her own note.
3. The product persists only the **`place_id`** plus **what she herself typed, confirmed or corrected** — her
   own CRM row, which the terms do not touch.
4. Google's fields are **re-fetched on every view**, never read back from storage.

Everything persistent in that pipeline is her own data. Nothing exportable or sellable is built.

If she needs an **ownable, exportable B2B contact dataset**, it must come from a **licensed data vendor whose
terms permit resale** — not from Google.

## 8. One gate this research did not cover

Whether the **outreach itself** is lawful: TRAI's UCC / DLT regime for SMS and voice, WhatsApp Business policy,
and the DPDP Act. Those bite **regardless of where the data came from** and are a separate check.

Hoola's own code already encodes part of this and is stricter than it looks — see
`server/app/campaigns.py:99`: a list **with** a consent column is filtered to opted-in rows, but a list with
**no** consent column is **not filtered at all**. So any Hoola-generated list must be marked no-consent **and
explicitly blocked** from the campaign path; it must not inherit the "no consent column = send to everyone"
behaviour.
