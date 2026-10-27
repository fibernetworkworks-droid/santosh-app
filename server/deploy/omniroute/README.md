# OmniRoute for Santosh

OmniRoute is an open-source (MIT) LLM gateway. It runs on the Santosh VPS, holds your provider API keys, and
switches between providers by itself (priority / cost / fallback combos). Santosh sends every chat turn to it at
`http://127.0.0.1:20128/v1`; if OmniRoute or all its providers fail, Santosh answers with Claude instead.

Tested with OmniRoute 3.8.51: Santosh's full tool-calling loop (56 tools, tool call -> tool result -> answer)
passes through unchanged. Santosh sends `x-omniroute-compression: off` so prompts and tool results are never rewritten.

## 1. Start it (Docker, loopback only)
    bash ~/santosh_app/server/deploy/omniroute/run.sh

## 2. Open the dashboard from your PC (SSH tunnel, nothing exposed publicly)
    ssh -L 20128:127.0.0.1:20128 root@YOUR_VPS
then open http://localhost:20128 in your PC browser and set the admin password.

## 3. In the dashboard
1. Providers -> add **API-key** providers you pay for (e.g. Z.ai GLM, DeepSeek, OpenRouter, Anthropic API).
2. Combos -> create a combo named **santosh**: cheapest good tool-calling model first, then fallbacks.
3. Endpoints -> create an API key for Santosh and copy it.

## 4. Point Santosh at it (~/apps/santosh-core/.env)
    CHAT_LLM=auto
    OMNIROUTE_URL=http://127.0.0.1:20128/v1
    OMNIROUTE_KEY=the-key-from-step-3
    OMNIROUTE_MODEL=santosh
then `pm2 restart santosh`. `/healthz` shows `"chat_brain": "omniroute:santosh"`.

## Rules for a product with real customers
- Use **API keys** only. Do not connect personal ChatGPT/Claude/Gemini subscriptions (OAuth) or the keyless
  "free" providers for customer traffic: their terms forbid it and customer data would pass through unknown relays.
- Keep the `santosh` combo on providers you have a contract with; don't route Santosh to `auto` (it may include free relays).
- Keep it on 127.0.0.1. Never publish port 20128.
- OmniRoute can log full request bodies: keep body logging off or short-lived (bills, contacts and emails pass through it).
