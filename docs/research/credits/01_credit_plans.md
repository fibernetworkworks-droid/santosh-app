# Hoola credit plans, India and worldwide (19 Nov 2026)

Owner's ask: "LETS WORK ON CREDIT AS PER HOOLA AI SUBSCRIPTION. FIRST CALCULATE THE PERFECT CREDIT PLANS BASED ON TOKEN
CONSUMED FOR HOOLA AI" -> "NEED BOTH GLOBAL AND INDIA". Nothing is built yet; this is the calculation.

## 1. The credit

**1 Hoola credit = $0.001 (0.1 US cent) of AI cost at the maker's own price = Rs 0.088.** One unit everywhere.

A credit is spent from what a job REALLY used: the server already counts every model call's tokens and dollar cost
(`usage.record`), and the media price cards already know their price before her Haan. Credits charged = that dollar
cost / $0.001, rounded up per message. So the margin is safe whatever the message size; only the number of credits put
in a plan is a guess about how people use it.

## 2. What things cost in credits (from docs 11-15, `tiers.py` PRICE / COST)

A chat message = 2 writer steps + 1 checker step (a step = 20k tokens read + 800 written). MEDIUM / Normal uses
GLM-5.3 at Rs 1.00 a step (it is Rs 0.22 at the cheapest provider and Rs 2.77 at Z.AI; Rs 1.00 is a middle guess).

| Action | ULTRA | HIGH | MEDIUM / Normal | LOW |
|---|---|---|---|---|
| A chat message | 240 | 90 | 30 | 6 |
| A voice-call minute | 98 | 45 | 31 | 30 |
| A picture | 39 | 12 | 3 | 3 |
| An AI-employee / Hoola Code job | 9,023 | 875 | 136 | 80 |
| A website build | 3,602 | 1,795 | 943 | 239 |
| A 30-second reel | 6,250 | 2,091 | 898 | 693 |

## 3. How the plan sizes are worked out

- Kept margin: **40% even if she uses every credit.** Most people use about 60% of what they buy; then the margin is
  about 64%.
- India: price includes 18% GST; Razorpay / UPI fee 2.36%; Rs 25 a user a month for servers, storage and free work
  (PDFs, OCR, embeddings, search). Through Google Play: 15% instead of 2.36% (credits about 14% fewer).
- World: price before the buyer's tax; the payment company's fee 7% + $0.50 (5% + $0.50, +1.5% for a card from
  another country, +0.5% for a subscription); $0.40 a user a month for servers. App stores: 15%.
- Credits = (money left after tax, fees and servers) x 60% / $0.001, rounded down to 100.

## 4. The plans

**The rule (owner, 19 Nov: "FREE TIER WORKS ON NORMAL TIER ONLY. ALL OTHER WILL BE LOCKED --- ONCE CREDIT PURCHASED
--- USER CAN CHOOSE ANY TIER -- BASED ON CHOOSEN TIER USER CREDIT WILL DEDUCT"):**

- **Free = Normal only.** Ultra, High, Medium and Low are locked (shown in the tier sheet with a lock and "Buy credits
  to use this"). Free gives **60 credits a day** on Normal = about 2 messages a day (at most Rs 158 a month for
  someone who uses it every day); unused free credits do not carry over.
- **Any purchase unlocks all five tiers** - a plan or a single top-up. She picks any tier; each message takes the
  credits of the tier it ran on (Ultra up to 70x Medium). Hoola says when credits run low and offers a top-up or a
  cheaper tier; it never moves her down by itself. When paid credits run out, she is back on Free (Normal only) until
  she buys again.
- **AI Employees are not paid from these credits** - each employee has its own package (section 4b).

### India (UPI / web, price includes GST)

| Plan | Price a month | Credits | Messages: ULTRA / HIGH / MEDIUM / LOW |
|---|---|---|---|
| Free | Rs 0 | 60 a day, Normal only | about 2 Normal messages a day |
| Lite | Rs 399 | 2,000 | 8 / 22 / 66 / 333 |
| Plus | Rs 999 | 5,400 | 22 / 60 / 180 / 900 |
| Pro | Rs 1,999 | 11,100 | 46 / 123 / 370 / 1,850 |
| Max | Rs 7,999 | 44,900 | 187 / 498 / 1,496 / 7,483 |

Through Google Play the same prices give 1,700 / 4,700 / 9,600 / 39,100 credits.

### Worldwide (price before the buyer's own tax, which the payment company adds and pays)

| Plan | Price a month | Credits | Messages: ULTRA / HIGH / MEDIUM / LOW |
|---|---|---|---|
| Free | $0 | 60 a day, Normal only | about 2 Normal messages a day |
| Lite | $8 | 3,900 | 16 / 43 / 130 / 650 |
| Plus | $20 | 10,600 | 44 / 117 / 353 / 1,766 |
| Pro | $100 | 55,200 | 230 / 613 / 1,840 / 9,200 |
| Max | $200 | 111,000 | 462 / 1,233 / 3,700 / 18,500 |

App stores: 3,800 / 9,900 / 50,700 / 101,700.

Cheaper countries (prices set by what people there can pay; the same credits are worth the same everywhere):

| Plan | Regional price | Credits |
|---|---|---|
| Lite | $4.50 | 1,900 |
| Plus | $11 | 5,500 |
| Pro | $23 | 12,200 |
| Max | $90 | 49,600 |

Which countries pay the regional price is a list the owner keeps (for example Pakistan, Bangladesh, Nepal, Sri Lanka,
Indonesia, Philippines, Vietnam, Nigeria, Kenya, Egypt). India keeps its own rupee list above.

### 4b. AI Employees: a package per employee

Each AI employee (SEO, Social Media, Accounts, Leads, Developer ...) is bought on its own, by the month, not from chat
credits. A package = a number of jobs a month at a set tier; the employee always runs on its package's tier (her chat
tier does not change it). A job's real cost is from the agent board (docs 13-14: LOW Rs 7, MEDIUM Rs 12, HIGH Rs 77,
ULTRA Rs 497-794 a job), with the same 40% kept, fees, tax and Rs 25 / $0.70 a month for servers.

| Package | Jobs a month | Tier | India (GST incl.) | World |
|---|---|---|---|---|
| Starter | 60 (2 a day) | MEDIUM | Rs 1,499 | $16 |
| Standard | 150 (5 a day) | MEDIUM | Rs 3,699 | $39 |
| Pro | 60 | HIGH | Rs 9,499 | $99 |
| Ultra | 30 | ULTRA (Claude Opus 5.5) | Rs 29,999 | $309 |

- These are the starting prices for an employee whose job costs what the board measured. Each employee gets its own
  numbers once its real job cost is measured on her server (an SEO audit and a GST return are not the same size): the
  job count changes, the four prices stay.
- Jobs past the package wait for next month, or she buys 20 more jobs at the package's price per job.
- An employee's chat replies inside its desk come from its package, not her chat credits.
- For comparison: a human executive in India costs Rs 20,000-40,000 a month.

### Extra credits (top-ups) and yearly plans

- 1,000 credits: Rs 213 in India, $2.39 worldwide (50% kept: bought when needed, little goes unused). Top-ups never
  expire for 12 months; plan credits reset each month (up to one month carries over on Pro and Max).
- Yearly = 10 months' price for 12 (about 17% off).
- Business: Plus or Pro per seat, credits pooled for the team.

## 4c. Payments from every country (owner: "WHAT EVER WE BUILD WE WILL BUILD IT FOR ENTIER WORLD. THUS PAYMENT WILL COME FROM ANY COUNTRY TO US")

One product, one credit, one wallet for the whole world; only the way the money comes in differs:

| Buyer | Paid through | Who handles the tax | Fee | Money reaches Newtika |
|---|---|---|---|---|
| India | Razorpay (UPI, cards, net banking, wallets) | Newtika charges and files 18% GST | about 2.36% | Indian bank, INR |
| Any other country | a merchant of record (Dodo Payments or Paddle): local cards, Apple Pay / Google Pay, PayPal, local methods, local currency | the merchant of record charges and pays every country's VAT / GST / sales tax | about 5-7% + $0.40-0.50 | payout to Newtika's Indian bank |
| Inside the phone app (Android / iPhone), any country | Google Play / App Store billing | the store | 15% (subscriptions) | the store pays out |

Why a merchant of record abroad: sold directly, Newtika itself would owe VAT in the EU, the UK, Australia, Japan and
many US states, each with its own registration. A merchant of record is the legal seller in those countries, so one
contract covers the world. Sales abroad are an export of services from India (GST 0% with a Letter of Undertaking,
paid in foreign currency - the CA files it). Stripe takes new Indian businesses by invitation only; Razorpay can take
foreign cards (about 3%) but then the foreign tax is Newtika's to handle.

To check before choosing (all from third-party pages, not the providers' own): Dodo Payments' fee (4% + $0.40, +1.5%
international, +0.5% subscriptions), Paddle's fee (5% + $0.50) and whether it takes a company of Hoola's size, payout
fees to an Indian bank, and whether either allows credit top-ups (one-off payments) beside subscriptions.

Built into Hoola: one credit wallet whatever the route; prices shown in the buyer's currency; each country's price
level read from the owner's list; refunds and failed renewals from the provider's signed webhooks only (never from the
browser); a plan or top-up counts only after the provider confirms the payment.

## 5. What the market charges (third-party trackers, Oct-Nov 2026 - not checked on the makers' own pages)

| | India | World |
|---|---|---|
| ChatGPT Go / Plus / Pro | Rs 399 / Rs 1,999 / Rs 19,900 | $8 / $20 / $200 |
| Claude Pro / Max | Rs 1,999-2,399 / - | $20 / $100 / $200 |
| Google AI Plus / Pro / Ultra | Rs 399 / Rs 1,950 / - | $7.99 / $19.99 / $99.99-199.99 |
| Manus (credits) | - | $20 = 4,000, $40 = 8,000, $200 = 40,000 |
| Genspark (credits) | - | $24.99 = 10,000, $249.99 = 125,000 |
| Lovable (credits) | - | $25 = 100 + 5 a day |

Hoola's prices sit on the same steps ($8 / $20 / $100 / $200, Rs 399 / Rs 1,999), with Plus at Rs 999 between Go and
Plus for India.

## 6. The weak spot, and the three things that fix it

At Rs 399 a MEDIUM / Normal user gets about 66 messages a month. ChatGPT Go feels unlimited at the same price. The
cost of a Normal message is too high for India's entry plan because of three things, each fixable:

1. **GLM-5.3's provider.** Rs 0.22 a step at the cheapest provider, Rs 2.77 at Z.AI (12x). The writer today asks
   OpenRouter for the FASTEST provider (`pipeline_provider_sort` latency) under a ceiling of 1.25x Z.AI's price, so it
   can pay the top price. Asking for the cheapest provider that is fast enough would make a Normal message about 12
   credits instead of 30 (Lite: about 166 messages).
2. **Prompt caching.** Most of the 20k tokens read each step are the same system prompt and tools every time. Cached
   reads cost 10-25% of the normal price at most providers; that cuts a step by about half again.
3. **The checker on every message.** Since v0.999.15 every chat has a writer + a checker. Checking only replies that
   state figures, prices or dates (the checker's own rule already) would save a third of each message.

With all three, a Normal message is about 5-8 credits and Lite gives 250-400 messages a month.

## 7. Not known yet (must be measured before launch)

- Real tokens per message on her server since v0.999 (the only live number: the parity card, 10 Nov, Rs 328.7 for 60
  asks on GLM-5.3-Flash = Rs 5.5 an ask, from before the small prompt and the Box). vps-ops can print a week of
  `usage` per feature and tier; that number replaces the "2 writer steps + 1 checker" guess.
- How much of a plan people really use (the 60% is the usual figure for credit plans, not Hoola's).
- Google Play's fee in India today (15% under Play billing, 4% less under user choice billing: Google's 2023 pages).
- The market prices in section 5 come from third-party trackers, not the makers' own pages.

## 8. Built in v0.999.26, and how to switch it on

Built (`server/app/credits/`): the wallet (every model call's real cost becomes credits through `usage.record`; free
first, then the plan, then top-ups), Free = Normal only (`tiers.locked`), the turn refused only when the day's free
credits and the paid credits are both gone, one line when credits run low / run out, AI-employee packages (hire needs
the package; each turn that runs a hired employee's tool is one job; the rest of that turn is the package's cost and
runs on the package's tier), orders through Razorpay / Cashfree (India) and Dodo Payments / Paddle (every other
country), paid only from a signed webhook or a server read of the provider's own record, each order given once,
subscription renewals (Dodo / Paddle), refunds taken back; console Credits page + locked tiers; phone Settings > Credits
+ locked tiers.

To switch it on (VPS `.env`, then deploy):

1. Payment keys - Newtika's own accounts, never a user's:
   `HOOLA_RAZORPAY_KEY_ID`, `HOOLA_RAZORPAY_KEY_SECRET`, `HOOLA_RAZORPAY_WEBHOOK_SECRET`;
   `HOOLA_CASHFREE_CLIENT_ID`, `HOOLA_CASHFREE_CLIENT_SECRET`; `DODO_API_KEY`, `DODO_WEBHOOK_SECRET`;
   `PADDLE_API_KEY`, `PADDLE_WEBHOOK_SECRET`. Which one is used first: `CREDITS_INDIA_GATEWAY` (razorpay | cashfree),
   `CREDITS_WORLD_GATEWAY` (dodo | paddle); the other one is the fallback.
2. Webhook addresses to enter in each dashboard:
   - Razorpay: `https://<server>/api/credits/webhook/razorpay` (payment.captured, payment.failed, refund.processed)
   - Cashfree: `https://<server>/api/credits/webhook/cashfree` (payment success, failed, refund)
   - Dodo: `https://<server>/api/credits/webhook/dodo` (payment.succeeded, payment.failed, subscription.renewed,
     subscription.cancelled, refund.succeeded)
   - Paddle: `https://<server>/api/credits/webhook/paddle` (transaction.completed, transaction.payment_failed,
     subscription.canceled, adjustment.created, adjustment.updated); also set Paddle's default payment link.
3. The products abroad: make one product (Dodo) / price (Paddle) per SKU, plans and packages as monthly subscriptions,
   top-ups as one-time: `plan_{lite,plus,pro,max}_{world,regional}`, `topup_{t1k,t5k,t20k}_{world,regional}`,
   `pack_{starter,standard,pro,ultra}_{world,regional}` (22), and list them as JSON in `DODO_PRODUCTS` /
   `PADDLE_PRICES` (`{"plan_plus_world": "pdt_..."}`). India needs no products: Razorpay / Cashfree take the amount.
4. `CREDITS_EXEMPT=<your own tenant id>` so your account is never charged, then `CREDITS_ON=true`.

Not built yet: India auto-renewing plans (an India plan is a 30-day pass bought again; UPI AutoPay mandates later),
Google Play / App Store billing inside the app, GST tax invoices for Indian buyers (Newtika must issue them; the
provider's receipt is not one), a way for her to change the country the prices come from, and media engines'
own charges (pictures, video, music, voice-over) as credits - only model calls that `usage.record` sees are charged.
NOT VERIFIED: no live payment with any of the four providers; Dodo's payload fields `metadata` / `subscription_id` on
payment events are not shown in its docs (the order is also found from the provider's own record on her return page).
