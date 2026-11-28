# OpenClaw inside Hoola - the concept (28 Nov 2026)

Owner: "AS WE HAVE READY MADE PRODUCTION GRADE PRODUCT OPENCLAW --- WE WILL 100 % USE ENTIERLY AS IT IS. JUST PLUGING IT TO
HOOLA PROPERLY ... WE JUST MAKE IT PERFECTLY MUTITENT FUCTIONAL. FIRST UNDERSTAND THE CONCEPT."

Read from OpenClaw's own docs (commit fe1e82080, release 2026.11.10, MIT): gateway/security/trust-model, concepts/multi-user,
gateway/operator-scopes, gateway/embedding, gateway/external-apps, gateway/protocol, gateway/trusted-proxy-auth,
gateway/openai-http-api, gateway/tools-invoke-http-api, install/docker, install/fly, channels/whatsapp.

## The concept

- **OpenClaw is not changed.** We run its official release (pinned version, its own Docker image / npm package) and only
  write its configuration. Its own updates are switched off; we move every user to a new release after we test it.
- **Hoola is the control plane** - sign-in, accounts, credits, the console and phone screens, Hoola's own tools and desks.
  **OpenClaw is the runtime** - the agent, its channels, its tools, its memory, per user.
- **Multi-tenant = one OpenClaw Gateway per Hoola user.** OpenClaw's trust model says one Gateway is one trust boundary
  ("Not supported: one shared gateway/agent used by mutually untrusted or adversarial users. Adversarial-user isolation
  needs separate gateways"); its multi-user mode and operator scopes are "collaboration guardrails, not tenant isolation";
  session tools read across the whole Gateway by default. So two Hoola users never share a Gateway. Each gets:
  its own container from the pinned image, its own state volume (memory, sessions, credentials), its own config and
  Gateway token (sealed in Hoola), RAM / CPU / disk caps, no network path to other users' containers.
- **How she reaches it:** through Hoola only. Hoola signs her in and forwards to her Gateway (OpenClaw's trusted-proxy auth),
  so its Control UI opens inside the Hoola console; the phone and Hoola's own chat talk to it over its documented Gateway
  WebSocket protocol (`gateway/external-apps`) or its OpenAI-compatible endpoint. Her chat apps (Telegram, Discord, Slack ...)
  connect to her own Gateway as OpenClaw does.
- **Hoola's powers inside OpenClaw:** Hoola is added to her Gateway as an MCP server with a token bound to her account, so
  her OpenClaw agent can use Hoola's desks, Route, studios, Hoola PC, memory - with Hoola's own approval cards.
- **Models and money:** her Gateway's model provider is OpenRouter with a key made for her alone (OpenRouter key per
  tenant with a spending limit), so every model call is metered into Hoola Credits and one user cannot spend another's.
- **Sleep and wake:** OpenClaw recommends about 2 GB RAM per Gateway (Fly: shared-cpu-2x, 2 GB). A quiet user's container
  is stopped and its state kept; a message or a Hoola tap wakes it. Channels that need a live connection keep it awake.

## Conflicts with Hoola's own rules - the owner decides

1. **WhatsApp in OpenClaw is WhatsApp Web (Baileys), the unofficial linked-device route** (also Zalo personal via
   zca-js). Hoola's non-negotiable rule forbids personal WhatsApp automation. Either those plugins stay off and Hoola's
   official WhatsApp (bahar.py) is used, or the owner changes the rule.
2. **Sending, paying, deleting need her tap in Hoola.** OpenClaw has its own approvals and permission modes; they are set
   in config to ask for those actions, and Hoola's MCP tools keep Hoola's cards.
3. **iMessage needs a signed-in Mac** per user - not possible on our server.
4. **Hoola brain or OpenClaw brain:** does OpenClaw become the coworker that answers her Hoola chat, or a section beside
   it (her own claw with its channels)?
5. **Capacity:** about 1-2 GB RAM per awake user; the VPS size limits how many are awake at once.
6. **The name:** OpenClaw is MIT (keep the notice); the product shown to users is Hoola.
