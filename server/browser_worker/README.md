# Santosh Browser

Santosh's own web browser: the open-source **browser-use** agent (MIT) driving a headless Chromium on the VPS.
Santosh calls it through the `browse_web` tool when Google search or reading a page isn't enough: sites built
with JavaScript, clicking through menus, checking a status, comparing on a site, filling an online form.

```
Santosh core (browse_web) --HTTP 127.0.0.1 + key--> worker.py (browser-use) --> Chromium --> netguard proxy --> internet
```

It runs as its own pm2 process with its own Python environment, because browser-use pins package versions
(mcp, google-genai) that differ from Santosh core.

## Safety (enforced by the worker, not by the model)

| Step on a website | What happens |
|---|---|
| Read, search, scroll, open links, fill ordinary fields, choose options | Santosh does it |
| Submit / send / book / apply / register / delete / confirm, or Enter in a form | Santosh pauses; the user gets a confirm card; only after **Approve** does it do that one click |
| Pay / checkout / place order / UPI / card | Never. The user gets an Open button and pays on the phone |
| Password, OTP, PIN, CVV, card number, Aadhaar | Never typed. The user does that step on the phone |
| WhatsApp Web, localhost, private/cloud-metadata IPs, file:// | Blocked (the netguard proxy checks every request, including redirects) |
| Run JavaScript, upload files | Actions removed |

Page text is treated as untrusted. Even if a page tells the model to do something else, the rules above still hold.

## Setup on the VPS

```bash
bash ~/santosh_app/server/browser_worker/setup.sh          # venv + browser-use + Chromium, prints WORKER_KEY
sudo ~/apps/santosh-browser/.venv/bin/python -m playwright install-deps chromium   # system libraries (once)
pm2 start ~/apps/santosh-browser/run.sh --name santosh-browser
```

Then in `~/apps/santosh-core/.env`:

```
BROWSER_WORKER_URL=http://127.0.0.1:8079
BROWSER_WORKER_KEY=<the key setup.sh printed>
BROWSER_LLM=auto        # Claude (sees the page) when ANTHROPIC_API_KEY is set; else OmniRoute / GLM
```

and `pm2 restart santosh --update-env`. `/healthz` then lists `browser` in features.

Each browser uses about 250–400 MB of RAM. `MAX_SESSIONS` in the worker's `.env` caps how many run at once
(default 2). Each person has one browser; a new task replaces their old one. Idle browsers close after 10 minutes.

## Tests

```bash
cd server/browser_worker
~/apps/santosh-browser/.venv/bin/python -m pip install pytest httpx
~/apps/santosh-browser/.venv/bin/python -m pytest -q
```

These tests run a real Chromium against local test pages with a scripted model. They cover reading a page, a
submit that waits for approval and then completes, password and payment steps that are never done, blocked
sites, and the proxy refusing local addresses.
