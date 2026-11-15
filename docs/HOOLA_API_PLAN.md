# HOOLA AGENT API - companies use Hoola's tools, employees and voice with one key

Owner, 13 Nov 2026: after the "Hoola LLM pipeline" research (OpenRouter-style gateway) -> "means we developed employees, tools etc can
directly be used by different companies via our Hoola API" -> "now let's work on development of different portal endpoints".

## Why this and not a raw token gateway (research done 13 Nov, official terms read)

- Every model provider read (OpenRouter s.7, Anthropic D.4(a), Groq 6.3(c), Together 4.3(d), Fireworks, DeepInfra 11(a)(viii), Mistral 2.2,
  Google Cloud 3.3(c), Alibaba 4.48.1, Moonshot 3.2(6), Z.ai XII.7) forbids RESELLING raw API access without a signed deal, and every one
  allows building your own product on top for your users (Anthropic A.1, Groq 3.1, Mistral "Customer Offering", Google "API Clients").
- So the API sells HOOLA'S WORK (a checked tool result, later an employee's finished job, a voice call), never a "prompt in -> model out"
  pipe. Hoola picks and pays its own model underneath.
- Gateways (OpenRouter, Eden, Requesty...) earn ~5 % on tokens and none shows rupee / UPI / GST / data-in-India. Hoola's ~600 tools,
  Indian employees and Hinglish voice are what they cannot copy.

## Shape (built in v0.877.0 = phase 1)

```
company app --hk_live_ key--> /api/hoola-api/v1/*  --acts as the company's OWN Hoola tenant, actor "api:<key id>"-->  agent.tools.dispatch
                                  |  allowlist catalogue only | rpm / rph / concurrent / daily INR cap per key
                                  |  price charged BEFORE the call (one transaction with its ledger row), refunded on any failure
company login --> /api/hoola-portal/*   keys, wallet, ledger, usage, catalogue
operator      --> /api/hoola-admin/*    overview, credit a wallet (reason required), suspend
```

Files: `server/app/hoolaapi/` (models, catalog, service, api), `server/tests/test_v0877_hoola_api.py`. Switch `hoola_api_enabled` (OFF by default),
`hoola_api_prices` (JSON override of per-call prices). Money = whole micro-INR; wallet == sum of an append-only ledger.

Laws (each has a test): key shown once, sha256 only; allowlist, never "every tool"; no send / pay / delete / PC tool in the catalogue (test
reads the names); a failed / timed-out / `ok:false` call is refunded; parallel calls never overspend; a revoked key or suspended wallet is dead;
arguments and results are never stored.

## Phases

| Phase | What | State |
|---|---|---|
| 1 | Keys, INR wallet + ledger, 6 catalogue tools (api_box, mospi, duniya, reach, scrape_page, pylab), portal + admin endpoints | BUILT v0.877.0 |
| 2 | Top-up by UPI: Razorpay order + signed webhook credits the wallet once (reuse `paygate/gw.py`), GST invoice per top-up, console portal page, docs page | needs owner decisions 1, 3 |
| 3 | Employees as API: `/v1/employees/{role}/run` (Bahi GST first) = a job that returns a finished report; async job id + webhook / poll | needs decision 4 |
| 4 | More tools after a per-tool terms check (WhiteBooks GST, Maps, eCourts, image / audio / video edit by file upload) | each tool = a decision |
| 5 | Voice API (per minute, Hinglish), MCP door (`/mcp/hoola`), AI Apps for the company's own customers | |
| 6 | Own-GPU open models under the hood (gpt-oss, Gemma 4, GLM...) to cut Hoola's own model cost; free tier | after measuring real tokens / second |

## What this phase deliberately does NOT do

- No raw chat-completions endpoint (that is the resale shape every provider forbids).
- No tool that sends, pays, deletes, shares, uses the owner's personal accounts or moves a PC (frozen PC code untouched).
- No wallet top-up route yet: money enters only through the operator's credit (phase 2 adds the signed Razorpay webhook).
- Rate limits are per process (the AI Apps limiter, reused); behind several workers they are per worker.

## Owner decisions still open

1. Prices: the six defaults (Rs 0.25 - Rs 1 per call) are placeholders, not measured costs.
2. Is the first customer group Indian developers / startups, or Hoola's own enterprise customers?
3. A CA's view on GST for prepaid wallet top-ups (reverse charge does not apply here: no USD is paid for the customer's use).
4. Which employee first (suggested: GST & Accounts).
5. API terms of service + privacy policy (lawyer) before real money flows; DPDP: Hoola stores metadata only.
6. Third-party data terms per tool (WhiteBooks, Google Maps - no caching / no resale of map data, eCourts, GSTIN lookups) before phase 4.

## NOT VERIFIED

Phase 1 ran against real `duniya`, `pylab` and `api_box` through the real dispatch on a local database (balance matched the ledger to the
paisa); no real company, no real money, no Razorpay, no Postgres run (the conditional-update debit is plain SQL and should behave the same).
