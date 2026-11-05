# Phase 10 "BAAKI SAB" - what each remaining Google API's terms allow

Read 3 Nov 2026 from the live Service Specific Terms (non-EEA): https://cloud.google.com/maps-platform/terms/maps-service-terms
and the Maps Platform ToS. API shapes for Solar and Roads come from their discovery documents
(`solar.googleapis.com/$discovery/rest?version=v1`, `roads.googleapis.com/...`), also reachable. Prices: `04_prices.md`.

| API | Built? | Why |
|---|---|---|
| **Solar** | **YES** `solar_check` | SST 20.1: *"Customer may use the Solar API only (a) to determine the feasibility of installing energy systems for a particular address or geographic area, (b) to design or install an energy system, or (c) for a Downstream Transaction"* (a design, a commercial proposal, or marketing the user opted in to). 20.2: cache Building Insights / Data Layers up to 30 days; the deletion duty does not apply to data inside fixed media for a Downstream Transaction. We store nothing. A plain feasibility answer for one address is exactly use (a). |
| **Roads** | **YES** `maps_snap` | SST 17.1 usable without a Google map; 17.2 never with a non-Google map; 17.3 lat/lng may be cached 30 days, nothing else. We store nothing. |
| **Air Quality** | **NO** | SST 2.1: *"Customer may only use the data retrieved from Air Quality API in (a) air quality based routing solutions developed by Customer, and (b) Customer environmental risk indices and correlational research."* A chat answer "what is the AQI here?" is neither a routing solution nor an index/research - building it would be outside the permitted use. Caching 1 h (current/forecast). Needs her decision on a narrow use (e.g. an AQI-aware route plan) before any code. |
| **Pollen** | **NO** | SST 16.1: same shape - *"(a) pollen based routing solutions ... and (b) Customer environmental risk indices, insights, and forecasts."* Same reasoning. (Also unverified that India is covered.) |
| **Elevation** | **NO** | Has no SST section at all (so ToS 3.2.3(b) no-caching applies in full) and ToS 3.2.3(c)(iii) forbids *"build terrain models based on elevation values from the Elevation API"*. No sourced price in our table. A single "height above sea level" lookup has no business use in her work that we found. |
| **Time Zone** | **NO** | India has ONE time zone (IST); the agent already knows it. No sourced price either. Nothing to buy. |

## Not verified
Whether the Solar API covers her city (it answers NOT_FOUND where Google has no imagery - handled, not billed); the Roads
billing unit (per request vs per element - the rate is the sourced "Roads - Nearest Road / Route Travelled" $3.00); the
100-point ceiling for snapToRoads is the documented limit from memory of the prose docs (blocked) - the discovery document
does not state it.
