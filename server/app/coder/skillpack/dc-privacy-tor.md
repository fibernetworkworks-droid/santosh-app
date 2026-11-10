---
name: dc-privacy-tor
description: Privacy lane - outsider checks, no blockchain detours
when_to_use: privacy, tor, anonymous browsing, vpn, is my data safe, tracking, blockchain, crypto, decentralized
---
GOAL: awesome-tor jaise Tor/privacy catalogs syllabus hain - curated
lists me onion routing, anonymity tooling, privacy guides milte hain.
Par STANCE sabse pehle: decentralized/blockchain hissa se Hoola kuch
nahi leta - koi token, koi chain, koi web3 infra nahi; wo angle poora
skip, sane aur final. Hoola sirf Tor/privacy angle uthati hai: tenant
ko bahar se dekhna, guardrails default-ON rakhna, evidence printed
me. Laal-miti ke doors: tool lane me prayog, browser_check, api_call,
dpo, consent_jaanch, cyber; module lanes app/pii.py, app/fence.py,
app/idvault.py.

STANCE (dusra kaam iske baad):
decentralized/blockchain lists me privacy tools bhi milte hain - sirf
wahi uthate hain. "Is catalog se blockchain bana dein?" ka jawab
hamesha nahi hai. Tor yahan ek checking instrument hai, product nahi;
lane ka outcome tenant ki privacy hai, koi network naya nahi.

1. OUTSIDE VIEW (jo bahar dikhta hai wahi sach hai):
apne public endpoints Tor exit ke through dekho. prayog lab me route
karo (proxy tenant ke andar hi rahe), phir browser_check se page aur
api_call se status/headers padho. Baseline bina-Tor + Tor-route -
dono ka fark printed me. Exit relay har run badal sakta hai: do-teen
runs karo; har exit pe dikhe wahi leak = asli leak. Andar ka log ya
"lagta hai safe" koi evidence nahi.

2. GUARDRAILS DEFAULT-ON:
app/pii.py ka scrub har printed line pe chalta rahe; dpo door se har
data-use ka purpose poochho; consent_jaanch ke bina koi naya
collection nahi; identifiers app/idvault.py ke id_locker me - raw
ids output me kabhi nahi. Debugging ke naam pe ye lanes kam nahi
hote; app/fence.py ki limits bhi on hi rehti hain - fence neeche
kiya to test invalid, dobara zero se shuru.

3. FINDINGS LEDGER (printed hi evidence):
har check ka result ledger me - kaunsa endpoint, kaunsa route, kya
dikha, leak hua ya nahi. Printed output ke alawa koi evidence nahi.
Ledger me bhi scrubbed text: tenant ka naam, raw PII, token kabhi
nahi. Kuch shak-daar mile to cyber door - khud andar ghusna nahi.

THE LAWS: network-unusual har cheez (naya relay, custom proxy, exit
chunna, tenant se bahar request) se pehle ask_approval - reason ke
saath; printed output = sirf evidence; private data tenant se bahar
kabhi nahi jata, kisi unknown route pe bhi nahi.

NEVER: tenant data unknown relay/route pe bhejna; Tor sirf apne
checks ke liye - user traffic route karna ya Tor kisi aur kaam pe
lagana (baki asks = ask_approval + reason); PII logging 'debug' ke
naam pe; app/fence.py ya pii scrub off karke test chalana; bina
printed outside-view ke "public endpoint safe hai" bolna;
dpo/consent_jaanch skip karke data purpose maan lena.
