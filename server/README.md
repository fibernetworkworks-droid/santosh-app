# Santosh Core

The backend for **Santosh**, the AI coworker. Version 0.3 does three things:

- **Daily-life assistant:** reminders (one-time and repeating), phone alarms, timers and calendar entries (through the Santosh Android app), memory of facts you share, lists, weather, and a morning briefing.
- **Automatic jobs (new in 0.3):** Santosh gives himself scheduled work ("har subah 7 baje mausam aur reminders bata dena") and runs it on the server; the phone gets the result as a notification even when the app is closed. Voice-mode messages get short, speakable replies.
- **WhatsApp marketing campaigns** end to end (described below).

You talk to Santosh in Hindi, Hinglish, Marathi or English. Santosh then:

1. Reads your leads file (CSV or Excel) and cleans the numbers. It fixes Indian formats, removes duplicates and skips bad numbers.
2. Writes the WhatsApp template in your language, checks it against WhatsApp's rules, and submits it to Meta.
3. Checks consent. Only people who agreed to WhatsApp messages get the campaign.
4. Waits for Meta's approval in the background, then sends within your daily limit and rate.
5. Tracks sent, delivered, read and replied, and posts the report back into your chat.

It starts in **test mode**: Meta is simulated and nothing reaches real phones. Switch to live once your WhatsApp Business account is connected.

---

## Run it on your computer (10 minutes)

```bash
cd santosh-core
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then put your Claude key in ANTHROPIC_API_KEY
uvicorn app.main:app --port 8077
```

Open http://localhost:8077, tap the paperclip, and attach `samples/leads_sample_TEST_MODE_ONLY.csv`. Then say something like:

> Diwali offer ka campaign sab leads ko bhej do. 30% off, 2 November tak.

Santosh asks for consent, writes and submits the template, and about 20 seconds later the simulated approval arrives. The campaign card then fills up live.

If you set `API_KEY` in `.env`, open the page once as `http://localhost:8077/?key=YOUR_API_KEY`.

Run the tests: `pytest -q` (22 tests, including a full simulated campaign, reminders, phone actions and the morning briefing).

Weather uses the free Open-Meteo service (no key needed); the server needs internet access to reach it.

---

## Go live with real WhatsApp

You need a Meta Business account and a phone number that is **not** already used on the WhatsApp app.

1. **Create the app.** On developers.facebook.com, create an app of type *Business* and add the *WhatsApp* product.
2. **Copy the IDs.** In WhatsApp, then *API Setup*, copy the *Phone number ID* into `WA_PHONE_NUMBER_ID` and the *WhatsApp Business Account ID* into `WA_WABA_ID`.
3. **Get a permanent token.** Go to Business Settings, then *System users*. Add a system user, assign it the app and the WhatsApp account with full control, and generate a token with the `whatsapp_business_management` and `whatsapp_business_messaging` permissions. Put it in `WA_TOKEN`. The temporary token on the API Setup page expires in 24 hours, so don't use that one.
4. **Add the app secret.** Under App settings, then *Basic*, copy the *App secret* into `WA_APP_SECRET`. This lets Santosh reject fake webhook calls.
5. **Set up the webhook.** In WhatsApp, then *Configuration*:
   - Callback URL: `https://YOUR-DOMAIN/webhooks/whatsapp`
   - Verify token: the same word you put in `WA_VERIFY_TOKEN`
   - Subscribe to the **messages** and **message_template_status_update** fields.
6. **Set the daily limit.** Set `MAX_DAILY_SENDS` to your number's messaging limit, which WhatsApp Manager shows under your phone number. New numbers start low and Meta raises the limit as quality stays good.
7. **Switch to live.** Set `WA_DRY_RUN=false` and restart.

Meta charges for each marketing conversation. Check the current India rates in WhatsApp Manager under *Billing*.

### Safety rails built in
- **Consent.** If the file has an opt-in column (`opt_in`, `consent`, …), only "yes" rows are messaged. If it doesn't, Santosh must get your confirmation first.
- **Sending only when asked.** Santosh sends automatically only when you clearly asked him to send. Otherwise the campaign waits as *Taiyaar* until you tap *Haan, bhej do*.
- **Daily limit.** It is respected across all campaigns. Leftover messages wait and go out automatically after the limit resets.
- **Sample file.** Numbers from the sample file are refused in live mode.
- **Bad numbers and template problems.** Numbers that aren't on WhatsApp are marked failed and never retried. If Meta flags a problem with the template, Santosh pauses the campaign and tells you.

---

## Deploy on your VPS

**Quick way (recommended):** copy the zip to the server, then as your normal user:

```bash
unzip santosh-v0.2.zip && cd santosh-core && bash deploy/install.sh
```

It installs everything into `~/apps/santosh-core`, generates your API key, runs the tests, starts Santosh under PM2 on `127.0.0.1:8077`, and prints the Caddy block for an https address. It never touches your other apps or your Caddyfile.

**Manual way (systemd + nginx):**

```bash
sudo useradd -r -m -d /opt/santosh-core santosh
sudo cp -r santosh-core/* /opt/santosh-core/ && sudo chown -R santosh /opt/santosh-core
cd /opt/santosh-core && sudo -u santosh python3 -m venv .venv && sudo -u santosh .venv/bin/pip install -r requirements.txt
sudo -u santosh cp .env.example .env && sudo -u santosh nano .env
sudo cp deploy/santosh.service /etc/systemd/system/ && sudo systemctl enable --now santosh
sudo cp deploy/nginx-santosh.conf /etc/nginx/sites-available/santosh   # edit server_name
sudo ln -s /etc/nginx/sites-available/santosh /etc/nginx/sites-enabled/ && sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d santosh.example.com    # Meta requires https for the webhook
```

Run **one** app process. The campaign worker runs inside it. For Postgres, `pip install "psycopg[binary]"` and set `DATABASE_URL=postgresql+psycopg://…`.

---

## API (for the Flutter app)

All `/api` calls need `Authorization: Bearer <API_KEY>` when `API_KEY` is set.

| Method | Path | What it does |
|---|---|---|
| POST | `/api/conversations` | Start a chat → `{id}` |
| POST | `/api/conversations/{id}/messages` | `{"text": "..."}`. Santosh works in the background |
| GET | `/api/conversations/{id}/events?after=0` | Live stream (server-sent events) of messages, steps and campaign updates |
| GET | `/api/conversations/{id}/messages` | Chat history |
| POST | `/api/leads/upload` | Form fields `file` (CSV/XLSX) and optional `conversation_id` |
| GET | `/api/campaigns/{id}` | Campaign progress and counts |
| POST | `/api/campaigns/{id}/action` | `{"action": "send" \| "pause" \| "resume" \| "cancel"}` |
| GET/POST | `/webhooks/whatsapp` | Meta webhook |
| GET | `/api/reminders` · POST `/api/reminders/{id}/cancel` | Upcoming reminders |
| GET | `/api/lists` · POST `/api/lists/items/{id}/done` | Lists |
| GET/DELETE | `/api/memory`, `/api/memory/{id}` | What Santosh remembers |
| GET/PUT | `/api/profile` | Name, city, language, time zone, briefing time |
| GET | `/api/device-actions/pending` · POST `/api/device-actions/{id}/result` | Phone actions (alarm, timer, calendar) for the app |
| GET | `/api/routines` · POST `/api/routines/{id}/cancel` | Santosh's automatic jobs |
| GET | `/healthz` | Mode and whether the Claude key is set |

Event kinds on the stream: `message`, `typing`, `step` (one per tool Santosh uses: running/done/error), `campaign` (full campaign view), `upload`, `reminders` (updated list), `reminder` (one just fired), `lists`, `device_action` (the phone should run it), `device_action_result` and `briefing`.

## Update an existing server

```bash
cd ~/santosh_app && git pull
cp -r ~/santosh_app/server/app ~/apps/santosh-core/
pm2 restart santosh
```
The database gains its new table automatically on start; settings in `.env` are kept.

## Code map
```
app/main.py              API, webhook, live stream, demo page
app/agent/santosh.py     the agent loop (Claude decides, tools act)
app/agent/tools.py       Santosh's WhatsApp tools
app/agent/life_tools.py  Santosh's daily-life tools
app/life.py              reminders, time zones, weather, morning briefing
app/agent/prompts.py     Santosh's personality and rules
app/campaigns.py         campaign logic shared by tools, worker and webhook
app/worker.py            waits for approval, sends, enforces limits, posts reports
app/whatsapp/client.py   Meta Graph API client + test-mode simulator
app/whatsapp/templates.py  WhatsApp template rule checks
app/leads.py             CSV/Excel import, Indian phone clean-up
app/static/index.html    demo chat page
```
