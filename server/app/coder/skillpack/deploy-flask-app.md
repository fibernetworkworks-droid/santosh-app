---
name: deploy-flask-app
description: Deploy a Flask or FastAPI app to the VPS with systemd
when_to_use: deploy, flask app, fastapi app, put my app on the server, vps deploy, host my python app, go live
---
GOAL: a new Flask/FastAPI service live on the VPS, restartable, logged.

1. Prereqs on the box: `python3 -m venv ~/apps/<name>/.venv`, then
   `~/apps/<name>/.venv/bin/pip install -r requirements.txt`.
2. One process, one unit: write `/etc/systemd/system/<name>.service`
   (User= a non-root user, ExecStart= the venv's uvicorn/gunicorn line,
   WorkingDirectory= the app dir, Restart=always). `systemctl enable --now <name>`.
3. Port law: the app listens on 127.0.0.1:<port>; nginx (or Caddy) fronts it
   with TLS. Never expose the raw port.
4. Secrets: only in the service's .env (chmod 600). Never in the repo, never in chat.
5. Health: a `/healthz` that answers {"ok": true} - the watchdog and you both read it.
6. Logs: `journalctl -u <name> -f` is the truth; the app must log WARN+ to it.
7. Updates: `git pull`, copy/checkout, `systemctl restart <name>`. DB migrations
   must be additive (nullable or defaulted columns) BEFORE the code that needs them.
VERIFY: curl the /healthz through the public https URL; restart once and curl again.
