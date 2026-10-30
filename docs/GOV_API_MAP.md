# Indian government portals: official APIs, MCPs and routes (research, 30 Oct 2026)

Step 1 of the owner's "one by one" plan. No code changed. Today all 17 Hoola government packs in
`server/app/bazar/packs/manifests` (digilocker, epfo, gst-portal, parivahan-dl-rc, umang, income-tax-e-filing,
abha, passport-seva, mca21, udyam, pm-kisan, irctc, echallan...) are `executor: handoff`, meaning info + pre-fill +
deep link, with no API behind them.

Access levels:
- A = open now (free key or none), Hoola can build it today
- B = official, but Newtika must register / sign an agreement / pass a sandbox test
- C = only licensed entities (GSP, AUA/KUA, FIU, ERI), so use a licensed partner's official API
- D = no API for outsiders, so keep handoff (deep link + pre-fill)

## Government MCP servers (live)
| Server | Owner | What | Level | Route |
|---|---|---|---|---|
| eSankhyiki MCP `https://mcp.mospi.gov.in/` | MoSPI / NSO (beta, 6 Feb 2026) | GDP, CPI inflation, PLFS jobs, IIP industry, energy, environment, trade | A | Connect as a featured remote MCP. Already in `mcp_directory.json.gz`; pin it in `featured_mcp.json` |

No official MCP was found for data.gov.in, API Setu, DigiLocker, GST or any other portal. Route: Hoola wraps the
official APIs below in its own MCP (`bazar/commerce/mcp_server.py` is the pattern).

## Official APIs
| Portal | API | Level | Route for Hoola |
|---|---|---|---|
| data.gov.in (OGD) | REST datasets API (resource id + free API key) | A | Free key on data.gov.in. Covers mandi prices, pincode directory, weather, schemes, census... |
| Bhashini (MeitY) | ASR / translation / TTS / transliteration (Dhruva / ULCA pipeline) | A | Free key from bhashini.gov.in profile. Useful for 22 languages in voice and chat |
| IMD (mausam.imd.gov.in) | Observation + forecast API (api.imd.gov.in) | B | Apply to the IMD nodal officer with an IP whitelist |
| API Setu (apisetu.gov.in) | Gateway for 2,000+ government APIs: DigiLocker issued docs (DL, RC, CBSE marksheets, PAN...), verification APIs | B | Register Newtika as an API Setu / DigiLocker Requester partner (official domain email, India server, Onboarding Committee, no sandbox) |
| DigiLocker | Requester / Pull APIs: user consents, Hoola fetches her issued documents | B | Same partner onboarding. Best single unlock: DL, RC, PAN, Aadhaar XML, marksheets with her consent |
| ABDM / ABHA (NHA) | ABHA create/verify, PHR app (M1-M3), consent-based health records | B | Register on sandbox.abdm.gov.in as a PHR app, pass milestone tests, go live |
| ULIP (goulip.in, logistics) | Vahan (RC), Sarathi (DL), FASTag, e-way bill, rail, port | B | Register on goulip.in. Access is for logistics businesses, so Newtika's use case must fit |
| ONDC | Beckn buyer app APIs | B | Already built (`bazar/commerce/ondc/`); finish registry onboarding |
| GST (GSTN) | Taxpayer returns / ledgers APIs | C | Only via a licensed GSP (Masters India, ClearTax, Cygnet...) as an ASP, with her consent OTP |
| e-Invoice (IRP) + e-Way Bill (NIC) | Generate IRN / e-way bill | B / C | Her own API user on einvoice1.gst.gov.in / ewaybillgst.gov.in with a GSP, or direct if turnover > ₹100 cr |
| Income Tax e-filing | ERI Type 2 APIs (prefill, ITR status, refund, file with her consent) | B | Newtika registers as an ERI Type 2 (Protean + portal, bank guarantee, audit report, sandbox via erihelp@incometax.gov.in) |
| Account Aggregator (RBI) | Bank statements, MF, insurance, EPF via consent | C | Become an FIU (RBI-regulated) or use Setu / Finvu / OneMoney's official AA APIs; Sahamati onboarding |
| UIDAI Aadhaar | Auth / eKYC | C | AUA/KUA licence only. Open part: offline paperless XML / secure QR verification, done locally (fits Pehchaan Locker) |
| NPCI BBPS / UPI | Bill pay, UPI intent | C | Already via BBPS agent institution + UPI intent (`connectors/bbps.py`, `upi.py`) |
| EPFO | Passbook / UAN | D | Not open. AA network covers EPF later; until then, handoff + UMANG |
| UMANG | 2,000+ services in one app | D | No partner API for outside apps. Handoff deep link |
| Passport Seva, MCA21, Udyam, PM-Kisan, e-Challan, eCourts, IRCTC | Portals | D / B | MCA21 + Udyam verification exist through API Setu (B). IRCTC only via an authorised partner. Others stay handoff |

## Suggested order (for the owner's next "GO")
1. A-level, build now: MoSPI MCP featured + data.gov.in tool + Bhashini engine. No paperwork.
2. Paperwork for Newtika, started in parallel (weeks): API Setu / DigiLocker partner, ABDM PHR app, IMD access.
3. Licensed partners (contract + per-call cost): a GSP for GST / e-invoice, an AA (Setu / Finvu) for bank data.
4. Bigger paperwork: ERI Type 2 (bank guarantee), ULIP if the logistics use fits.

Every row was checked on the web on 30 Oct 2026, mostly from official pages (PIB, incometax.gov.in, NeGD SOP,
DigiLocker FAQ, ABDM guidelines, IMD API doc). Fees, quotas and lead times were not published and must be confirmed
at sign-up.
