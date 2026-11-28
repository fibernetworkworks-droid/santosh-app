# Chinese models: resale and self-hosting terms (read 28 Nov 2026)

Two things per company: (A) its paid API's international terms; (B) the licence of its latest open-weight
models. Quotes are short excerpts as the page reader returned them. Not legal advice.

## A. Their paid APIs

| Company | Terms page (date) | Own product for own users | Resell raw API access | Data / training |
|---|---|---|---|---|
| DeepSeek | cdn.deepseek.com/policies/en-US/deepseek-open-platform-terms-of-service.html (effective 29 Apr 2026, PRC law) | Yes - s1.1 "internal and external end users" | No written permission; s2.2 "do not share ... your API key with others"; no reseller program | Stored in mainland China (privacy policy, 10 Feb 2026); personal data may train models, opt-out by email |
| Z.ai (GLM) | docs.z.ai/legal-agreement/terms-of-use.md (14 Apr 2026, Singapore law) | Yes - "downstream systems ... to your end users" | Not allowed - s XII.7 "cannot ... sublicense"; keys not shared; Coding Plan forbids proxying "unless otherwise agreed in writing" | "Generally processed in Singapore"; no training unless she agrees |
| Alibaba Qwen (Model Studio intl) | alibabacloud.com product terms s4.48 (19 Oct 2026) | Yes - end users must accept the terms | No - 4.48.1(d)(v) "resell Model Studio or AI models" without express authorisation | Region she picks (Singapore, US, Frankfurt, Hong Kong, Tokyo); no training; kept <= 30 days |
| Moonshot Kimi | platform.kimi.ai/docs/agreement (30 Jul 2026, Singapore law) | Yes - "offer those Customer Applications to End Users" | No - s3.2 no "selling ... sub-licensing"; s3.4 no selling API keys | Country not stated; content MAY be used to improve services unless an enterprise agreement |
| MiniMax | platform.minimax.io terms - page body would not load | Not read | Not read | Not read |
| Tencent Hunyuan (TokenHub) | tencentcloud.com/document/product/301/78869 (effective 24 Aug 2026) | Yes (assumes end users) | No - 5.2.3 no API token to third parties without prior written consent | Not stated |
| Baidu ERNIE | intl.cloud.baidu.com user agreement (2 Sep 2025, Hong Kong law) | Implied | No - "providing the services to third parties" needs written authorisation | Not stated |
| ByteDance (BytePlus ModelArk) | main terms load by JavaScript, not read; Code of Conduct 27 Nov 2026 | Platforms allowed for Seedance video, with real-name end users | No - "resells or sublicenses the APIs without authorization" = ban | Malaysia / Indonesia / EU (search snippet); no training without consent |

Reseller programs found: Alibaba Cloud Reseller Program (companies with sales + technical teams). None
for the others - ask each in writing.

## B. Their open weights (run on Hoola's own servers, sell access)

| Model (latest) | Licence | Host it and sell access? | Conditions |
|---|---|---|---|
| DeepSeek V4.1-Flash, V4-Pro | MIT | Yes | Keep the licence notice. No limits |
| GLM-5.3 (+ GLM-5.3-Flash tagged MIT) | "GLM-5.3 License" (MIT-based) | Yes | Only a model-hosting business with > US$10 billion revenue a year needs Z.ai's security review |
| Qwen3.8-27B, Qwen3-235B and other Apache models | Apache-2.0 | Yes | No limits |
| Qwen3.8-Max (2.4T) | "Qwen3.8-Max License" | Yes | Hosting business > US$50M revenue in 12 months needs a separate licence; > 100M monthly users or > US$20M monthly revenue must show the model name |
| Kimi K3 / K3.1-Pro | MIT-based Kimi licence | Yes, below the line | Hosting business with revenue over "20 million" (period not shown) needs a separate agreement; big apps show "Kimi K3" |
| Kimi K2 | modified MIT | Yes | Only the name-display rule at 100M users / US$20M a month |
| MiniMax-M3 | MiniMax Community Licence | Yes, after a one-time notice | Notice to api@minimax.io; > US$20M revenue a year needs written authorisation; show "Built with MiniMax M3" |
| MiniMax-M2.7 | Non-commercial | No | Needs a separate licence |
| MiniMax-M2 | modified MIT | Yes | Show "MiniMax M2" above 100M users / US$30M ARR |
| Tencent Hy4 | Tencent Hy License 1.0 | Yes, below the line | Hosting business > US$50M in 12 months or > 100M monthly users needs a licence |
| Older Tencent Hunyuan | Hunyuan Community Licence | Yes, but NOT in the EU, UK or South Korea | Outputs may not improve other models |
| Baidu ERNIE 4.5 | Apache-2.0 | Yes | No limits |
| ByteDance Seed-OSS-36B | Apache-2.0 | Yes | No limits |

## What it means for Hoola

- Their **paid APIs** behave like the American ones: building Hoola's own product is fine; reselling raw
  access needs written permission from each.
- Their **open weights** are the easy door: DeepSeek, GLM, most Qwen, ERNIE, Seed-OSS can be hosted and
  sold with no permission; Kimi K3, Qwen3.8-Max and Tencent Hy4 only above large revenue lines; MiniMax M3
  needs a notice; MiniMax M2.7 cannot be sold.
- **Data:** DeepSeek's own API stores data in mainland China under PRC law - a real issue for business
  users, government work and privacy laws (India DPDP, EU GDPR). Hosting the same weights on Hoola's own
  servers (or a host in her chosen country) keeps the data out of China. Z.ai (Singapore) and Alibaba (she
  picks the region) are easier.
- **Global rule:** some governments and companies ban Chinese-made AI on official devices or in public
  work; a Hoola route should let each customer switch Chinese models off.

Not read: MiniMax's and BytePlus's main API terms (pages would not load), the licences of Qwen3.8-Flash-Next,
Kimi K2.5-K2.7 and GLM-5.2, Z.ai's API data addendum.
