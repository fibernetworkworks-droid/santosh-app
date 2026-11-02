# Google Maps for Hoola — the plan

Owner's ask (2 Nov 2026): *"BEFORE THIS LETS WORK ON GOOGLE MAPS FOR HOOLA --- MAKE A PLAN"*.

Plan only. Nothing is built until she says GO on a phase.

---

## 1. What exists today, measured

`server/app/maps.py` is 10 KB and calls **three** Google Maps Platform APIs:

| In use | Endpoint | What it gives |
|---|---|---|
| Places API (New) | `places:searchText` | text search near a point |
| Routes API | `directions/v2:computeRoutes` | one origin → one destination, live traffic |
| Geocoding API | `maps/api/geocode/json` | address → coordinates |
| (no key needed) | `google.com/maps/dir/`, `/maps/search/` | deep links that open her Google Maps app |

Plus `where_am_i` / `save_location` against the `UserLocation` table, and three agent tools:
`maps_search`, `maps_directions`, `maps_navigate`.

**Who actually uses it:** `propagent`, `fleet`, `helpdesk`, `phonedoc`, `bazar_tools`, `main`. Six modules.

---

## 2. The three gaps, in the order they matter

### Gap 1 — she pays Google per call, and nothing controls it
**There is no cache, no daily cap and no budget anywhere in `maps.py`.** Every search, every route, every
geocode goes to Google and is billed. The field mask is set correctly (that is what picks the SKU), so the
per-call cost is not reckless — but the *number* of calls is unbounded, and a chatty job or a loop over a
list of addresses bills every row.

This is first in the plan because it is the only gap that can cost her money while she sleeps.

**What a fix looks like:** a `maps` budget like the Studio and Arena already have (`SITE_ARENA_MAX_INR`,
`studio_project_usd` are the precedent), a per-call price table so a result can carry its own cost, a daily
cap that refuses rather than overspends, and a cache.

**The cache has a legal shape, not just a technical one.** Google's Maps Platform terms restrict what may be
stored and for how long — place IDs are treated differently from the rest of a place's content, and there are
limits on retaining geocodes. **I will not design the cache until I have read the current terms**, and the
plan will quote them. Caching the wrong field for too long is a licence breach, not a clever saving.

### Gap 2 — Hoola never shows her a map
MapLibre GL is vendored in `static/vendor/maplibre/`, and it is used in exactly one place:
`console/build.js` — the **website builder**, for the maps that go on *her customers'* sites.

So in Hoola's own surfaces — the chat, the console, the phone — **every geographic answer is text plus a link
that leaves Hoola.** "Teen godown yahan hain" with three addresses and a Google link. She has to leave to see
where anything is.

That is the biggest product gap and the most visible fix.

### Gap 3 — thirteen roles are geographic; Maps serves six modules thinly
These exist already and all of them are about *where things are*:

`fleet_manager` · `courier_desk` · `driver_coordinator` · `logistics_coordinator` · `field_service` ·
`warehouse_manager` · `site_supervisor` · `site_manager` (Theka sahayak) · `property_manager` ·
`travel_agent` · `tour_guide` · `homestay_host` · `event_planner`

What they need and `maps.py` cannot do:
- **many-to-many distances** (which of my 8 technicians is nearest to this complaint?) — needs Routes matrix
- **multi-stop ordering** (12 deliveries, best sequence) — needs route optimisation; today v0.346 NAKSHA only
  sorts "nearest first" inside a generated app, which is not the same thing and is often much worse
- **a map image in a report or PDF** — needs Static Maps; `docstudio` prints beautiful PDFs with no maps in them
- **address validation** before a delivery is promised — needs Address Validation
- **a place's details** (phone, hours, rating, photo) — Places details, not just text search

---

## 3. What Google Maps Platform offers that Hoola does not touch

Each line is a real product she already has a key for, or can enable on the same key.

| API | What it would unlock in Hoola | For whom |
|---|---|---|
| **Routes: computeRouteMatrix** | nearest technician / nearest godown / nearest driver, properly | field_service, fleet, courier, helpdesk |
| **Route Optimization** | the day's stop order for a van, with time windows | courier_desk, logistics, driver_coordinator |
| **Places: details, photos, autocomplete** | a real place card — hours, phone, rating, photo; typing an address with suggestions | bazar, propagent, travel, tour_guide |
| **Address Validation** | "is this a deliverable Indian address?" before she promises a date | courier, ecommerce, app backends |
| **Static Maps** | a map **picture** inside a PDF, a report, a WhatsApp message, a site plan | docstudio, SEO local, propagent, site reports |
| **Roads / snap-to-road** | clean a GPS trail into a real route travelled | fleet, drivers, field_service |
| **Elevation** | slope for a site, a route's climb | design/construction work, cycling/trek routes |
| **Time Zone** | correct local time for a coordinate | travel_agent |
| **Solar API** | rooftop solar potential, roof segments, annual kWh from a building's address | **ties straight into the solar O&M and rooftop-solar design work** |
| **Air Quality / Pollen** | a real health answer for a location | seva, homestay, travel |
| **Places aggregate / area insights** | how many competitors of a type are near a plot | propagent, feasibility, SEO local |

Not all are worth building. The plan picks by what her existing roles are already trying to do.

---

## 4. The shape I would build — one engine, every surface

`maps.py` stays the single door to Google (every other module already imports it, which is the right shape
and should not change). It grows:

1. **A priced, capped, cached client.** One place that knows what each call costs, keeps a daily budget,
   caches what the terms allow, and **refuses with a reason** instead of silently spending.
2. **A map Hoola can draw.** MapLibre is already vendored — reuse it, do not add a second map library.
   A `maps` result becomes a **card with a real map** in the console and the phone: pins, a route line, a
   fitted viewport. Where tiles come from is a decision below (§7).
3. **The missing calls**, in the order the roles need them: matrix → optimisation → static image → place
   details → address validation.
4. **Every number from the API, never from the model.** The v0.374/v0.375 rule applies here too: a distance,
   an ETA, a stop order is computed by Google or by our own code over Google's matrix — never produced in a
   sentence. A wrong ETA looks exactly as confident as a right one.

---

## 5. Build phases

| Phase | What ships | Why here |
|---|---|---|
| **1 — PAISA PEHLE** | the priced/capped/cached client: a per-call price table, `MAPS_DAILY_INR` cap that refuses, a cache whose field and TTL rules are **quoted from Google's terms**, and a usage line she can see | the only gap that can cost her money unattended |
| **2 — NAKSHA DIKHE** | a real map card in the console and the phone (MapLibre, reused): pins, route line, fitted bounds, tap to open Google Maps | the biggest visible gap; every geographic answer stops being a wall of addresses |
| **3 — SABSE PAAS** | Routes **computeRouteMatrix** → "nearest of these N" as a first-class answer, wired into field_service / fleet / courier / helpdesk | the single most asked geographic question in her business |
| **4 — DIN KA RASTA** | **Route Optimization**: the day's stop order with time windows, service durations and vehicle capacity, as a card she approves | turns courier/logistics from a list into a plan; v0.346's "nearest first" is replaced where it is wrong |
| **5 — NAKSHA KAAGAZ PAR** | **Static Maps** images inside `docstudio` PDFs, reports and WhatsApp messages | a map in a document is worth more than a link, and it needs no app |
| **6 — JAGAH KA PATA** | Places **details / photos / autocomplete** + **Address Validation**, with Indian address reality (landmark-based addresses, PIN checks) | stops a bad address becoming a failed delivery |
| **7 — CHHAT PAR SOORAJ** | **Solar API** on a building's address → roof segments, annual kWh, panel count | feeds the solar O&M role and the building-design work already planned |
| **8 — ASLI RASTA** | **Roads/snap-to-road** + trip trails for fleet, and geofence arrive/leave events | the fleet roles' real daily need |
| **9 — PROOF** | a maps card like the coding/tool cards: fixed geographic questions with known answers, scored, and the **rupees each answer cost** | the only honest way to claim it works and to see the bill |

---

## 6. What it will not do

- **Official routes only.** Google Maps Platform APIs with her key. No scraping of Google Maps pages, no
  unofficial endpoints, no screenshotting map tiles to dodge a licence.
- **No storing what the terms forbid**, and no cache TTL I have not read the terms for.
- **Never a guessed distance, ETA or stop order.** If the API cannot answer, Hoola says so.
- **No live tracking of a person without their knowing.** A driver's trail is a work record on her own fleet,
  shown to her, and that is where it stops.
- **Her key is hers.** CLAUDE.md's rule stands: *don't modify her FNW Flow Maps key.* This plan uses
  `GOOGLE_MAPS_API_KEY` and touches nothing else.

---

## 7. Decisions I need from her

1. **Tiles for the map card — this is the one real cost decision.** Google's **Map Tiles / Dynamic Maps** are
   billed per map load. MapLibre can instead draw **free OpenStreetMap-based tiles** (or MapTiler/Protomaps on
   a cheap plan) while *all the data* — places, routes, ETAs — still comes from Google. That keeps Google for
   what it is unbeatable at and makes showing a map nearly free. **I recommend free tiles + Google data**, and
   I need her yes because it changes what the map looks like.
2. **A daily rupee cap for Maps.** Pick a number for Phase 1 to enforce. Studio and Arena have one; Maps does
   not.
3. **Which role first after the map card** — field_service/helpdesk ("who is nearest?") or courier/logistics
   ("what order today?"). I would do nearest-first because it is one call and immediately useful.
4. **Is Solar API wanted now or later?** It is the most interesting one for the building/design work, but it
   is a different audience from her delivery and field roles.
5. **Does the phone need offline maps?** Expensive to do properly. My recommendation: no — show the map when
   there is signal, and always keep the "open in Google Maps" button that works offline-ish and costs nothing.

---

## 8. What I would do first if she just says "GO"

Phase 1 and Phase 2 together, as one version: **the bill gets a cap and a cache, and she finally sees a
map.** Those two are independent of every decision above except the tiles question, which is why §7.1 is the
one answer I actually need to start.
