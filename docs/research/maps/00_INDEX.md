# Google Maps for Hoola — the research register

Owner's ask (2 Nov 2026): *"WE WANT MAP FOR ::: 1) USER CAN USE A EXISTING GOOGLE MAP MANUALLY, AI WILL DO ALL
THOSE THINGS 2) API FOR NEAR BY THINGS 3) GOOGLE MAP LEAD GENERATION SCRAPER ------- ETC OBJECTIVE HOOLA AI CAN
PERFORM ALL MAP TASK"*

Three registers, researched the same day from Google's own documents. Read the one you need; the plan built on
them is `docs/MAPS_PLAN.md`.

| # | File | Answers |
|---|---|---|
| 1 | `01_terms_caching_and_leads.md` | What may be stored, for how long, and what a "lead list" may be. Requirement **#3**. |
| 2 | `02_places_and_business_profile.md` | Places API (New) in detail + the Business Profile API family and its access gate. Requirement **#2**, and the real answer to **#1**. |
| 3 | `03_her_existing_map.md` | Her My Maps map, her saved lists, where her own geodata can live, Street View. Requirement **#1**. |

---

## The four findings that decide the build

### 1. Maps Platform is licensed as a live lookup service, not a data source
The Places section of the Service Specific Terms is exactly §14.1–14.3 and permits storing **two** things:
`place_id` (indefinitely) and lat/lng (30 days). **Nothing** permits storing a business name, address, phone,
website or rating — and ToS §3.2.3(b) makes the absence of a permission a prohibition. Every field may be
**shown**; almost nothing may be **kept**. That one distinction shapes every feature here.

### 2. Requirement #3 is refused by two independent Google documents
- Platform ToS §3.2.3(d)(iii): no using the services *"in a listings or directory service or to create or
  augment an advertising product."*
- Business Profile policies, on `GoogleLocations`: *"Use of this endpoint for any other purpose, which includes
  lead generation or other analysis, is against Google's policies and will result in immediate revocation of
  your API access."*

Breach of §3.2 is **immediate suspension, no notice, no cure period** (ToS §5.2(d)). Scraping maps.google.com
instead is worse, not better: the consumer terms ban *"copy the content"* and *"mass download or create bulk
feeds"* unconditionally, and `robots.txt` carries `Disallow: /maps/`.

**But the objective survives**, because the limit is on keeping, not getting. See `01`, §7.

### 3. A map card may NOT use free tiles — this reverses an earlier recommendation
ToS §3.2.3(e): *"Customer will not use the Google Maps Core Services with or near a non-Google Map in a
Customer Application. For example, Customer will not (i) display or use Places content on a non-Google Map."*
SST §14.2: *"Customer must not use Google Maps Content from the Places API in conjunction with a non-Google
map."*

So **MapLibre + OpenStreetMap tiles + Google Places data is a licence breach**, not a clever saving. There are
exactly two legal shapes: Places data on a **Google** map (Dynamic Maps SKU), or Places data with **no map at
all** — which §14.1 expressly allows: *"Customer may use Google Maps Content from the Places API in Customer
Applications without a corresponding Google Map."*

### 4. The two halves of "all map tasks" have completely different lead times
- **Finding places** — Places API (New). Enable it and go. No form, no review, no one's permission.
- **Operating her own listing** — every Business Profile API is gated behind a human application whose
  precondition is a profile *"verified and active for 60+ days"*. **No published review turnaround.** Approval
  shows up as the Cloud Console quota moving from **0 QPM to 300 QPM**.

So the application gets submitted in week one and the code gets built against documented shapes while it waits.

---

## Method note

Every load-bearing quote in these registers was re-verified by hand against the downloaded page, not trusted to
a summary. Two things were caught that way: a sentence attributed to the prerequisites page that **is not on
it**, and the free-tiles recommendation above, which the terms forbid. Each register carries its own
**NOT FOUND** list — things no primary source would confirm, left empty on purpose rather than filled from
memory. Among them: any write path for My Maps or saved lists, the Business Profile review turnaround, the
format of the Takeout "Saved" export, and whether the old $200 monthly Maps credit still exists.
