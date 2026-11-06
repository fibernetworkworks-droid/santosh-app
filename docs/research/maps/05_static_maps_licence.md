# Static Maps / Street View pictures in a PDF or WhatsApp - what the terms say

Read 3 Nov 2026 from the live pages (fetched as HTML, quotes copied from the downloaded text):
- Maps Platform ToS - https://cloud.google.com/maps-platform/terms
- Maps Service Specific Terms (SST, non-EEA) - https://cloud.google.com/maps-platform/terms/maps-service-terms

`developers.google.com` (the Static Maps / Street View docs, pricing) was NOT reachable from the sandbox, so how Google
words the API's own usage notes is unread. What follows is the contract text only.

## The decision
**Plan Phase 7 as first written ("Static Maps in docstudio PDFs and WhatsApp") is not built, because a map picture
saved into a PDF or sent as a file is the thing the ToS forbids.** Links are built instead (`maps_links`).

## Why - the text
ToS 3.2.3(a) **No Scraping**: *"Customer will not export, extract, or otherwise scrape Google Maps Content for use
outside the Services. For example, Customer will not: (i) pre-fetch, index, store, reshare, or rehost Google Maps
Content outside the services; (ii) bulk download Google Maps tiles, Street View images, geocodes, directions,
distance matrix results, roads information, places information, elevation values, and time zone details..."*

ToS 3.2.3(b) **No Caching**: *"Customer will not cache Google Maps Content except as expressly permitted under the Maps
Service Specific Terms."*

SST section A.3 **Google ID Caching** is the only general permission: *"Customer may cache the Google ID values ...
For example, Customer may cache (a) place_id ..., (b) pano_ID, from Street View Static API, and (c) video_ID..."*

The SST's Core Service list is: Address Validation, Air Quality, Android Geocoder, Directions, Distance Matrix,
Geocoding, Geolocation, Google Earth, Maps Datasets, Maps Experience Agent Tools, Navigation Connect, Navigation SDK,
Places Aggregate, Places API, Places UI Kit, Pollen, Roads, Route Optimization, Routes, Solar, Weather. **There is no
section for Maps Static API or Street View Static API**, so nothing carves an exception out of 3.2.3 for their images.

A PDF with a map picture in it is a stored copy of Google Maps Content that is then re-shared. A WhatsApp image is the same.
Silence in the SST is a prohibition (ToS 3.2.3(b)).

## What stays allowed
- **A link** that opens Google's own map (Maps URLs, `https://www.google.com/maps/search/?api=1&query=...`,
  `...maps/@?api=1&map_action=pano&viewpoint=...`). Nothing of Google's is stored or re-hosted; the customer sees it on
  Google. No key, no fee.
- **Street View Metadata** (a free SKU) to learn *whether* a panorama exists before offering the link. `pano_id` is
  cacheable; the image is not.
- A map shown **live** to the person on a page that loads it from Google at view time (not built; needs a restricted
  browser key and is billed per view - a separate decision).

## Not read / not verified
Whether Google's Static Maps docs add a print or offline allowance (they might; only the contract was read), and
whether the Maps URLs parameters are exactly as written above (the scheme is the documented `api=1` one already used in
`maps.nav_link`; the pano parameters come from memory of that scheme).

## Side findings from the same read (confirm earlier phases)
- **Route Optimization SST 18.1-18.3**: usable without a Google map; not with a non-Google map; lat/lng cacheable 30 days -
  matches Phase 5 (nothing stored).
- **Address Validation SST 1.3**: formattedAddress / postalAddress / componentName cacheable 30 days **or** replaced by the
  user's confirmed/corrected value, and only for *Downstream transactions*; the flags and lat/lng have their own limits -
  Phase 6 stores none of it, so it is inside the rules by being outside the cache.
