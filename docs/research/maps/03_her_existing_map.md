# Her existing Google map — what can actually be reached

Researched 2 Nov 2026, primary sources only. This register answers requirement #1: *"USER CAN USE A EXISTING
GOOGLE MAP MANUALLY, AI WILL DO ALL THOSE THINGS."*

**"Her existing Google map" means one of three different things, and they have three different answers.**

| What she means | Answer |
|---|---|
| **her business's listing on Google Maps** (what most owners mean) | **reachable and writable** — Google Business Profile APIs, after an application. See `02_places_and_business_profile.md`. |
| **a My Maps custom map** she drew (google.com/maps/d/) | **readable once, with her consent. Not writable. Not syncable.** |
| **her saved places / lists** (Want to go, Favourites, starred) | **no API at all.** Takeout export only, by her own hand. |

---

## 1. My Maps (google.com/maps/d/)

**There is no API to write to a My Maps map. None.** Not deprecated — never existed in the current platform.

| Capability | Route | Verdict |
|---|---|---|
| **List** her My Maps files | Drive API, MIME type `application/vnd.google-apps.map` ("Google My Maps", in the official MIME reference) | **USE** — but metadata only: name, id, sharing. Not contents. |
| **Export** a map's contents via Drive | — | **NO ROUTE.** Drive's export-formats reference has no row for the map MIME type and no KML/KMZ format at all. |
| **Read** a map's contents | **Data Portability API**, schema `mymaps.maps` — *"the maps the user created in My Maps, including layers, features, and media"*, *"Object is exported in these formats: KMZ"* | **USE**, one-shot, with her consent. Needs app verification for restricted scopes. |
| **Write / add to** a map | — | **NO ROUTE** |
| **Keep in sync** | — | **NO ROUTE** |
| Map as a live KML URL | `maps/d/kml?mid=…` and the "network link" checkbox | **NO ROUTE — undocumented.** It exists in the UI; it is on no Google documentation page, only community threads. Nothing commits Google to keeping it. |
| Her own manual export | *"click Menu, then Export to KML/KMZ"* | **user-driven only** |
| Her own manual import | CSV, TSV, KML, KMZ, GPX, XLSX, Google Sheet. **KML/KMZ ≤ 5 MB, other files ≤ 40 MB, "Do not import files with more than 2,000 rows"**, photos ≤ 100 per import | **user-driven only** |

**The retired predecessors**, so nobody proposes them again:
- **Fusion Tables** — official notice 11 Dec 2018: *"We plan to turn down Fusion Tables and the API on
  December 3, 2019."* The Maps JS Fusion Tables Layer: deprecated 3 Dec 2018, off 3 Dec 2019, gone from v3.38.
- **Google Maps Data API** (the GData API that did expose My Maps) — Google's own directory: *"Deprecated.
  Replaced by Google Maps API Web Services."* **NOT FOUND:** an official shutdown date. And the replacement
  named does **not** restore My Maps access — Web Services means Geocoding / Directions / Places.
- **Maps Engine / Maps Engine API** — **NOT FOUND:** any primary Google shutdown notice. Third-party reports
  only. Do not cite a date.

**The honest design, therefore:** she exports once (or authorises a Data Portability export), Hoola imports the
KMZ, and **from that moment the app owns the data**. Anything promising *"Hoola will keep editing your My Maps
map"* can only be delivered by driving the web app — scraping — and would break. Say so rather than build it.

## 2. Saved places and lists
- **Read or write by API: NOT FOUND.** Not in Maps Platform, and tellingly **not in Data Portability either** —
  its Maps schema lists 22 exported objects (aliased places, labelled places, commute routes, photos…) and
  **no saved-lists or starred-places object**.
- **Takeout does export them**, by her hand: *"Go to takeout.google.com… Make sure 'Saved' is checked"*.
- **The file format inside the "Saved" export is NOT FOUND on any Google page.** Third-party accounts conflict
  (one CSV per list vs a single `Saved Places.json`). **Do not design against either until a real export has
  been opened.**
- **Adding a place to her list programmatically: NO ROUTE.** The documented method is manual: *"tap Save…
  Select an existing list or create a new one."*

## 3. Where her own geodata CAN live, and be drawn

This is the part that replaces My Maps properly, and it is better than My Maps.

### Option A — Maps Datasets API (Google hosts it)
*"Maps Datasets API lets you create and manage datasets using a REST API"* — create, upload, list, get, patch,
download, delete, `fetchDatasetErrors`. Data-driven styling then renders it on a Google map: points, polylines,
polygons, click events; **vector maps only, a map ID is required**.

Documented limits: **CSV, GeoJSON and KML only**; **max file size 500 MB**; display names unique per project and
**under 64 bytes**; **no 3-D geometries**; unsupported KML includes `<NetworkLink>`, `<GroundOverlay>`,
`<LookAt>`, styles defined inside the file and icons/`<styleUrl>` defined outside it; CSV geometry columns may be
lat/long, x/y, WKT or address and **every row must have non-empty geometry**.
**NOT FOUND:** any per-feature count limit, or any cap on datasets per project.

**Price: *"There is no charge for using the Maps Datasets API."*** Rendering is the ordinary **Dynamic Maps** SKU
(`FAF4-3B2D-51B2`): 10,000 free a month, then $7.00 per 1,000 descending to $0.53. No separate Datasets or DDS
pricing row exists.

A few thousand customer or site locations fits comfortably. The catch: Google hosts it, so a change means
uploading a new dataset version rather than editing in place.

### Option B — Maps JS Data layer (her data never leaves her server)
*"The Google Maps Data layer provides a container for arbitrary geospatial data."* `map.data.loadGeoJson()`
fetches a URL; **`map.data.addGeoJson(obj)` loads a FeatureCollection "without fetching an external URL"**.
Only stated constraint: a cross-domain JSON file needs CORS enabled. **NOT FOUND:** any size or feature limit.

Because it renders client-side, **nothing has to be public** — `addGeoJson` fed from Hoola's own authenticated
backend is fully supported. **This is the route that keeps her data out of Google.**

### What is NOT available: KmlLayer
*"The `KmlLayer` functionality in the Maps JavaScript API is no longer available."* The deprecation register
says *"Deprecated as of April 30, 2026… no longer available"*, while the migration guide says *"The last
version which supports KmlLayer is 3.65, to be decommissioned in May 2027."* Two Google pages that do not
quite agree — read it as **retired on current versions, pinnable to v3.65 until May 2027. Do not build on it
either way.**
**NOT FOUND:** KmlLayer's old numeric size/feature limits — the section went with the feature. Do not quote
remembered figures.
KmlLayer also always required a **publicly reachable** URL (Google fetched it server-side), so a private file
never worked with it. The Data layer has no such problem.

## 4. Street View — both directions are official
- **Street View Static API** — *"embeds a static (non-interactive) Street View panorama or thumbnail into a web
  page without the use of JavaScript"*; plain HTTP URL, returns an image; a key is required. SKU
  `9BD0-A2EE-44C3`, 10,000 free a month then $7.00/1,000 → $0.53. **"Street View Metadata" (`3168-48A9-5C8C`)
  is unlimited and free** — which is how to check a panorama exists before paying for the image.
- **Street View Publish API** — separate, official, **no deprecation notice anywhere**, and it does more than
  upload: `photo` create / delete / get / startUpload / update, `photos` batchDelete / batchGet / batchUpdate /
  list, `photoSequence` create / delete / get / startUpload, `photoSequences.list`. So **her own 360 photos can
  be read, written, updated and deleted.** Its terms require pointing users at Street View Studio for removal
  and appeals, and warn images may surface across Maps, Search and YouTube.

---

## The verdict in one line

If "the map she already has" is her **business listing**, it is fully operable — after an application. If it is
a **My Maps map**, she can hand its contents over once and then Hoola owns them, drawn through the Data layer
(her server) or the Datasets API (Google's). If it is her **saved lists**, there is no route at all and the
honest answer is to say so.

### The NOT FOUND list — do not fill these from memory
- A shutdown date for the Google Maps Data API (GData).
- Any primary Google notice for the Maps Engine shutdown.
- KmlLayer's numeric size and feature limits.
- A per-feature limit, or a per-project dataset limit, for the Datasets API.
- The exact file format of the Takeout "Saved" export.
- **Any write path at all for My Maps, or for saved lists.**
