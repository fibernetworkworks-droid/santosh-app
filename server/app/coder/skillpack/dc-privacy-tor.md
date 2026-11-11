---
name: dc-privacy-tor
description: Privacy lane - outsider checks, no blockchain detours
when_to_use: privacy, tor, anonymous browsing, vpn, is my data safe, tracking, blockchain, crypto, decentralized
---
GOAL: Tor / privacy catalogs like awesome-tor are the syllabus - the
curated lists hold onion routing, anonymity tooling and privacy
guides. But the STANCE comes first: Hoola takes nothing from the
decentralized / blockchain part - no token, no chain, no web3 infra;
that angle is skipped entirely, and that is final. Hoola takes only
the Tor / privacy angle: looking at the tenant from outside, keeping
guardrails default-ON, evidence in print. The doors of this lane: in
the tool lane prayog, browser_check, api_call, dpo, consent_jaanch,
cyber; the module lanes app/pii.py, app/fence.py, app/idvault.py.

STANCE (everything else comes after this):
decentralized / blockchain lists hold privacy tools too - only those
are taken. The answer to "shall we build a blockchain from this
catalog?" is always no. Tor here is a checking instrument, not a
product; the outcome of the lane is the tenant's privacy, not a new
network.

1. OUTSIDE VIEW (what shows from outside is the truth):
look at our own public endpoints through a Tor exit. Route it in the
prayog lab (the proxy stays inside the tenant), then read the page
with browser_check and the status / headers with api_call. Baseline
without Tor + the Tor route - the difference of the two in print.
The exit relay can change on every run: do two or three runs; a leak
that shows on every exit = a real leak. An inside log or "it seems
safe" is not evidence.

2. GUARDRAILS DEFAULT-ON:
the app/pii.py scrub keeps running on every printed line; ask the
purpose of every data use through the dpo door; no new collection
without consent_jaanch; identifiers go in the id_locker of
app/idvault.py - raw ids never in output. These lanes are not
reduced in the name of debugging; the limits of app/fence.py stay on
too - if the fence was lowered the test is invalid, start again from
zero.

3. FINDINGS LEDGER (only print is evidence):
the result of every check goes in the ledger - which endpoint, which
route, what showed, leak or no leak. There is no evidence other than
printed output. Scrubbed text in the ledger too: never the tenant's
name, raw PII or a token. If something looks suspicious, use the
cyber door - do not break in yourself.

THE LAWS: ask_approval before anything unusual on the network (a new
relay, a custom proxy, choosing an exit, a request outside the
tenant) - with the reason; printed output = the only evidence;
private data never leaves the tenant, not on any unknown route
either.

NEVER: send tenant data over an unknown relay / route; Tor is only
for our own checks - never route user traffic through it or use Tor
for anything else (other asks = ask_approval + reason); PII logging
in the name of "debug"; run a test with app/fence.py or the pii
scrub off; say "the public endpoint is safe" without a printed
outside view; skip dpo / consent_jaanch and assume the data purpose.

ALSO ASKED AS (Hinglish asks this skill answers): mera data safe hai kya,
privacy check karo, bahar se kya dikhta hai, tracking band karo
