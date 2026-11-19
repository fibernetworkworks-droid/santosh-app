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
- World: price before sales tax / VAT; card fee 4.4% + $0.30; $0.40 a user a month for servers. App stores: 15%.
- Credits = (money left after tax, fees and servers) x 60% / $0.001, rounded down to 100.

## 4. The plans

### India (UPI / web, price includes GST)

| Plan | Price a month | Credits | Messages: ULTRA / HIGH / MEDIUM / LOW | Tiers allowed |
|---|---|---|---|---|
| Free | Rs 0 | 25 a day (about 750 a month) | - / - / - / about 4 a day | LOW |
| Lite | Rs 399 | 2,000 | 8 / 22 / 66 / 333 | LOW, MEDIUM, Normal |
| Plus | Rs 999 | 5,400 | 22 / 60 / 180 / 900 | + HIGH |
| Pro | Rs 1,999 | 11,100 | 46 / 123 / 370 / 1,850 | + ULTRA |
| Max | Rs 7,999 | 44,900 | 187 / 498 / 1,496 / 7,483 | all |

Through Google Play the same prices give 1,700 / 4,700 / 9,600 / 39,100 credits.

### Worldwide (card / web, price before tax)

| Plan | Price a month | Credits | Messages: ULTRA / HIGH / MEDIUM / LOW |
|---|---|---|---|
| Free | $0 | 25 a day | LOW only |
| Lite | $8 | 4,100 | 17 / 45 / 136 / 683 |
| Plus | $20 | 11,000 | 45 / 122 / 366 / 1,833 |
| Pro | $100 | 56,900 | 237 / 632 / 1,896 / 9,483 |
| Max | $200 | 114,200 | 475 / 1,268 / 3,806 / 19,033 |

App stores: 3,800 / 9,900 / 50,700 / 101,700.

### Extra credits (top-ups) and yearly plans

- 1,000 credits: Rs 213 in India, $2.39 worldwide (50% kept: bought when needed, little goes unused). Top-ups never
  expire for 12 months; plan credits reset each month (up to one month carries over on Pro and Max).
- Yearly = 10 months' price for 12 (about 17% off).
- Business: Plus or Pro per seat, credits pooled for the team.

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
