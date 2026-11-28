# Can Hoola resell model access? The companies' own terms (read 28 Nov 2026)

Two questions per company: (1) may a business build its own product on the API and charge its own users;
(2) may it resell raw API access (give customers keys / a pass-through API like OpenRouter).
Quotes are short excerpts from the live pages; a few came back from the fetch tool in pieces. Not legal
advice - a lawyer should confirm before any resale business.

| Company | Terms page (date shown) | (1) Own product for own users | (2) Resell raw access | The way to get permission |
|---|---|---|---|---|
| OpenAI | openai.com/policies/services-agreement (1 Dec 2025, effective 1 Jan 2026) | Yes - s2.2 "make Customer Applications available to End Users" | No - s3.1 "may not resell or lease access to its Account"; s3.3(g) "buy, sell, or transfer API keys" | Direct deal; authorised resellers exist (s6.1, s17); OpenAI Partner Network openai.com/business/partners |
| Anthropic | anthropic.com/legal/commercial-terms (effective 17 Jun 2025) | Yes - A.1 "power products and services Customer makes available to its own customers and end users" | Only with approval - D.4 "resell the Services except as expressly approved by Anthropic" | Anthropic's express approval; Claude Partner Network claude.com/partners (mainly services / channel) |
| Google Gemini API | aistudio.google.com/docs/terms (effective 23 Mar 2026) + developers.google.com/terms (9 Nov 2021) | Yes - "make API Clients available to users" | No - APIs Terms s4a(1) "Sublicense an API for use by a third party ... create an API Client that functions substantially the same as the APIs"; Search grounding not resold | Through Google Cloud reseller channel only |
| Google Vertex AI | cloud.google.com/terms (24 Mar 2026) | Yes - s1.1 app "that has material value independent of the Services" | No - s3.3(c) "sell, resell, sublicense, transfer, or distribute" | Google Cloud Reseller Agreement + Partner Advantage (partners.cloud.google.com) |
| xAI (Grok) | x.ai/legal/terms-of-service-enterprise (no date) + AUP (14 Aug 2026) | Yes - only "as part of a Bundled Service" (her own product) | No - "non-sublicensable"; AUP bars "selling, reselling, distributing" | A written agreement; no public reseller program found |
| Mistral | legal.mistral.ai/terms/commercial-terms-of-service (25 Sep 2026) | Yes - s1.4 "Customer Offering", sublicensable "to its End Users" | No - s2.2(h) "buy, sell, or transfer API keys"; third-party access "without our prior written authorization" | Prior written authorisation; mistral.ai/partners |
| AWS Bedrock (incl. Claude) | aws.amazon.com/agreement (29 Oct 2026), service-terms s50.12 (23 Nov 2026) | Yes - Anthropic-on-Bedrock A.1 same as Anthropic | No - Customer Agreement s6.4(c) "resell the Services"; keys "for your internal use only"; Anthropic D.4 still applies | AWS Solution Provider Program, AND Anthropic's approval for Claude |
| Microsoft Azure OpenAI / Foundry | microsoft.com/licensing/terms (Product Terms, MCA) | Yes - third parties "solely in connection with ... that Customer Solution" | No - "may not ... resell or redistribute the Microsoft Azure Services" | Cloud Solution Provider (CSP) program |
| OpenRouter | openrouter.ai/terms (31 Aug 2026) | Yes - s5.1 "incorporate the Service into your own products and services" (model makers' terms pass to her customers) | No, outright - s7.4 "reselling API access to Models or otherwise developing a competing service"; credits non-transferable | No published exception; ask their enterprise team. Management API keys (a key per customer inside her own product) are allowed |
| Groq | console.groq.com/docs/legal/services-agreement (22 Jun 2026) | Yes - s3.1 "make the Cloud Services ... available to End Users" | Only with approval - s6.3(c) "except as expressly approved by Groq"; s3.2 no reselling the account | "Groq authorized ... reseller" (s18); no public sign-up |
| Together AI | together.ai/terms-of-service (19 May 2026) | Not written either way | No - s4(3)(d) "resell ... or otherwise offer the Services on a standalone basis" | An order form; model licences (Llama etc.) also bind her |
| Fireworks AI | fireworks.ai/terms-of-service PDF (10 Jul 2026) | Unclear - s2.1 "personal use or internal business purposes" | No - s2.2(d) API keys "without our prior written consent"; s2.2(e) "resell, distribute" | Prior written consent / enterprise agreement |
| DeepInfra | deepinfra.com/terms (15 Oct 2026) | Implied yes - s10(iii) her "own products, services, and end-user relationships" | No - s11(a)(viii) "resell, sublicense ... make the Services available to any third party" unless a Service Order says so | A signed Service Order |

## What it means for Hoola

- **Hoola as it is today is allowed everywhere it matters.** Chat, Web Studio, Hoola Code, AI employees,
  Hoola Credits for Hoola's work, and the Hoola API that sells Hoola's tools (v0.877) are "own product for
  own users" on OpenAI, Anthropic, Google, xAI, Mistral, AWS, Azure, OpenRouter and Groq. Hoola must pass
  the model makers' usage rules on to its users (OpenRouter s5.1 / s5.8; Mistral "substantially
  equivalent" restrictions).
- **An OpenRouter-style gateway selling raw model access is forbidden on every standard term read.**
  Each needs its own written deal: OpenAI (direct / reseller), Anthropic (express approval), Google (Cloud
  reseller + Partner Advantage), AWS (Solution Provider + Anthropic's approval for Claude), Azure (CSP),
  Groq (authorised reseller), Mistral / xAI / Together / Fireworks / DeepInfra (written consent / order
  form). OpenRouter itself publishes no exception.
- **Open models on Hoola's own servers** (Qwen, DeepSeek, GLM, Mistral open weights) need no company's
  permission - only each model's own licence. Renting them from Together / Fireworks / DeepInfra / Groq
  does NOT give resale rights: their terms forbid it.

Not read: OpenAI Usage Policies, Anthropic AUP, Microsoft Generative AI Services terms, xAI's separate API
terms, Mistral's partner terms, OpenRouter's Enterprise Access Agreement.
