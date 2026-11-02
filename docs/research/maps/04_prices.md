# Google Maps Platform prices — the table the cap is built on

Read 2 Nov 2026 from Google's own price lists, then **independently re-fetched and re-checked** line by line.
Both checks agreed on every India figure quoted here.

Sources:
- Global list — https://developers.google.com/maps/billing-and-pricing/pricing
- **India list** — https://developers.google.com/maps/billing-and-pricing/pricing-india
- Per-SKU billable events — https://developers.google.com/maps/billing-and-pricing/sku-details/places
- Routes billing — https://developers.google.com/maps/documentation/routes/usage-and-billing
- Billing FAQ — https://developers.google.com/maps/billing-and-pricing/faq

---

## 1. The billing unit — per request, not per result

Each Places SKU's billable event is printed as **"Successful request for &lt;tier&gt; fields"** (and
*"Successful request for only IDs"* for Essentials IDs-Only). The page adds:

> *"your request is billed based on the fields provided in the field mask"*
> *"The request is billed at the highest SKU applicable to the requested fields."*

And the usage-and-billing page: *"You are then billed at the highest SKU applicable to your request."*

**So the field mask selects one tier — the dearest one it touches — and the request is charged once.** A mask
spanning Essentials + Pro + Enterprise bills **one** Enterprise event, not three. One Text Search returning
**20 places** with an Enterprise field in the mask is **ONE** Enterprise event, not twenty. Modelling cost as
`results × rate` overstates a search roughly twentyfold.

Stated honestly: no Google page spells out the 20-results case in words. The answer follows from the billable
event being defined as a *successful request*, plus the field-mask rule above. Supporting analogue, stated
flatly for the UI Kit: *"Users are billed for this SKU only per each Places UI Kit request, regardless of what
fields are displayed."*

**The one exception**, from the Routes page:

> *"Compute Route Matrix requests are billed per ELEMENT returned from the request."*
> *"if a request contains two origins and three destinations, then the request is billed for six elements."*

while *"Compute Routes requests are billed for each Request."* So a 10×10 matrix is **100** billable events.
`mapsbill.UNIT` records this, and `charge()`'s `n` means elements for that SKU alone.

## 2. India is a separate, cheaper list — in USD

The India page says so: *"This page contains pricing tables for Google Maps Platform APIs for India."* Its
usage key reads **"Prices - USD"** and **"Costs - per 1000 events"** — it is **not** an INR list.

Its tier columns are **`Free Usage Cap | Cap - 5,000,000 | 5,000,000+`** — only **two** paid bands, where the
global list has five (`Cap - 100,000`, `100,001-500,000`, `500,001-1,000,000`, `1,000,001-5,000,000`,
`5,000,000+`). So "first tier" means something different on each page.

| SKU | India, first tier | India free/month | Global, 0–100k | Global free/month |
|---|---|---|---|---|
| Text Search Pro | **$9.60** | 35,000 | $32.00 | 5,000 |
| Text Search Enterprise | **$10.50** | 7,000 | $35.00 | 1,000 |
| Text Search Enterprise + Atmosphere | $12.00 | 7,000 | $40.00 | 1,000 |
| Text Search Essentials (IDs Only) | **free** | Unlimited | free | Unlimited |
| Nearby Search Pro | **$9.60** | 35,000 | $32.00 | 5,000 |
| Nearby Search Enterprise | **$10.50** | 7,000 | $35.00 | 1,000 |
| Place Details Essentials (IDs Only) | **free** | Unlimited | free | Unlimited |
| Place Details Essentials | $1.50 | 70,000 | $5.00 | 10,000 |
| Place Details Pro | $5.10 | 35,000 | $17.00 | 5,000 |
| Place Details **Enterprise** | **$6.00** | 7,000 | $20.00 | 1,000 |
| Place Details Enterprise + Atmosphere | $7.50 | 7,000 | $25.00 | 1,000 |
| Place Details Photos | $2.10 (per photo) | 7,000 | $7.00 | 1,000 |
| Places Details – ID Refresh | **free** | Unlimited | free | Unlimited |
| Autocomplete Requests | $0.85 | 70,000 | $2.83 | 10,000 |
| Autocomplete Session Usage | **free** | Unlimited | free | Unlimited |
| Geocoding | $1.50 | 70,000 | $5.00 | 10,000 |
| Compute Routes Essentials | $1.50 | 70,000 | $5.00 | 10,000 |
| Compute Routes Pro | $3.00 | 35,000 | $10.00 | 5,000 |
| Compute Routes Enterprise | $4.50 | 7,000 | $15.00 | 1,000 |
| Compute Route **Matrix** Essentials / Pro / Enterprise (**per element**) | $1.50 / $3.00 / $4.50 | 70,000 / 35,000 / 7,000 | $5.00 / $10.00 / $15.00 | 10,000 / 5,000 / 1,000 |
| Route Optimization – SingleVehicleRouting | $0.80 | 35,000 | $10.00 | 5,000 |
| Route Optimization – FleetRouting | $2.40 | 7,000 | $30.00 | 1,000 |
| Address Validation Pro / Enterprise | $5.10 / $7.50 | 35,000 / 7,000 | $17.00 / $25.00 | 5,000 / 1,000 |
| Dynamic Maps (a map load) | $2.10 | 70,000 | $7.00 | 10,000 |
| Static Maps | $0.60 | 70,000 | $2.00 | 10,000 |
| Street View Static | $2.10 | 70,000 | $7.00 | 10,000 |
| **Street View Metadata** | **free** | Unlimited | free | Unlimited |
| Elevation | $1.50 | 35,000 | $5.00 | 5,000 |
| Time Zone | $1.50 | 70,000 | $5.00 | 10,000 |
| Air Quality | $0.50 | 70,000 | $5.00 | 10,000 |
| Solar – Building Insights | $4.00 | 70,000 | $10.00 | 10,000 |
| Solar – Data Layers | $30.00 | 7,000 | $75.00 | 1,000 |
| Roads – Nearest Road / Route Travelled | $3.00 | 35,000 | $10.00 | 5,000 |
| Roads – Speed Limits | $12.00 | 35,000 | $20.00 | 5,000 |

**Using the global numbers for Indian traffic overstates most Places SKUs about threefold**, and Route
Optimization FleetRouting by **12.5×** ($30.00 against $2.40). `mapsbill` defaults to the India list.

**NOT FOUND** as single SKUs — they do not exist under those names: "Solar API" (it is Building Insights +
Data Layers), "Roads API" (Nearest Road / Route Travelled / Speed Limits), "Route Optimization API"
(SingleVehicleRouting + FleetRouting), and **"Nearby Search Essentials (IDs Only)"** — Nearby has **no**
IDs-only tier, so there is no free id-harvesting pass on it.

## 3. Free caps are per SKU, and belong to the billing account

The FAQ describes the change from the old credit:

> *"modifying the USD $200 monthly recurring credit by offering a free monthly usage threshold for each Core
> Services SKU"*

So: **per SKU, not one pooled allowance**, and **the $200 credit no longer exists** — neither price page
mentions it at all. **Do not build a cap against a $200 cushion.**

Read the row, not the tier: Elevation is 35,000 (India) though it is an Essentials-priced SKU, and India's
caps are uniformly **7×** the global ones.

And the unit is the **billing account**, not the project:

> *"Google aggregates service usage for all projects linked to the customer billing account"*

That is why `mapsbill.MapsFree` counts the free allowance **globally** across tenants. Splitting work across
projects buys nothing, and one noisy project burns the shared allowance.

## 4. What is assumed rather than sourced

Routes is tiered Essentials / Pro / Enterprise, and **no page we found maps a particular field mask to a
tier**. Hoola's `route()` asks for `TRAFFIC_AWARE` plus `navigationInstruction`, so `mapsbill` charges it at
**Enterprise** — the dearest plausible tier, which can only make the cap fire early. `ASSUMED_TIER` is
reported by `GET /api/maps/usage` so the guess is visible, and it is the first thing to correct against her
first real bill.
