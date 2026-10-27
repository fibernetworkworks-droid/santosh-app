"""Script / config templates the DevOps Sahayak writes as FILES she reviews. Hoola never runs any of them.
Every template is made safe by default (set -euo pipefail, guarded deletes, no inline secrets, pinned versions) and is still
passed through rules.check_script before she gets it."""
from __future__ import annotations

import re
from typing import Any

KINDS: dict[str, dict[str, Any]] = {
    "gha_ci": {"label": "GitHub Actions CI (build + test)", "lang": "yaml", "file": ".github/workflows/ci.yml",
               "params": {"stack": "node | python | flutter | android | go", "branch": "main"}},
    "gha_deploy": {"label": "GitHub Actions deploy (production, approval + rollback input)", "lang": "yaml", "file": ".github/workflows/deploy.yml",
                   "params": {"stack": "node | python | static", "host_secret": "DEPLOY_HOST", "app": "app naam", "path": "/srv/app"}},
    "dockerfile": {"label": "Dockerfile", "lang": "dockerfile", "file": "Dockerfile", "params": {"stack": "node | python", "port": "3000"}},
    "nginx": {"label": "nginx reverse proxy (HTTPS)", "lang": "nginx", "file": "site.conf", "params": {"domain": "example.com", "port": "3000"}},
    "backup": {"label": "Backup script (database / folder, retention)", "lang": "bash", "file": "backup.sh",
               "params": {"what": "postgres | mysql | sqlite | files", "name": "db / folder", "keep_days": "14", "dest": "/var/backups/app"}},
    "pm2": {"label": "pm2 ecosystem file", "lang": "js", "file": "ecosystem.config.js", "params": {"app": "app", "script": "server.js", "memory": "500M"}},
    "systemd": {"label": "systemd service", "lang": "ini", "file": "app.service", "params": {"app": "app", "cmd": "/usr/bin/node server.js", "user": "app", "dir": "/srv/app"}},
    "healthcheck": {"label": "Health check script (cron)", "lang": "bash", "file": "healthcheck.sh", "params": {"url": "https://example.com/health"}},
    "logrotate": {"label": "logrotate (180 din, CERT-In)", "lang": "ini", "file": "app.logrotate", "params": {"path": "/var/log/app/*.log"}},
    "ps_backup": {"label": "PowerShell backup (Windows folder / Tally data)", "lang": "powershell", "file": "backup.ps1",
                  "params": {"source": "C:\\TallyPrime\\Data", "dest": "D:\\Backup", "keep_days": "30"}},
}


def _p(params: dict[str, Any], k: str, default: str) -> str:
    v = str(params.get(k) or default).strip()
    return re.sub(r"[`$;|&<>\n\r]", "", v)[:200] or default


def _name(v: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "-", v)[:60] or "app"


def render(kind: str, params: dict[str, Any]) -> tuple[str, str, str]:
    """(file name, language, content)."""
    k = KINDS.get(kind)
    if not k:
        raise ValueError(f"Template '{kind}' nahi hai. Ye hain: {', '.join(KINDS)}")
    fn = globals()[f"_t_{kind}"]
    return k["file"], k["lang"], fn(params or {})


def _t_gha_ci(p: dict[str, Any]) -> str:
    stack, branch = _p(p, "stack", "node").lower(), _p(p, "branch", "main")
    head = f"""name: CI
on:
  push:
    branches: [{branch}]
  pull_request:
permissions:
  contents: read
concurrency:
  group: ci-${{{{ github.ref }}}}
  cancel-in-progress: true
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
"""
    body = {
        "node": """      - uses: actions/setup-node@v4
        with:
          node-version-file: .nvmrc
          cache: npm
      - run: npm ci --fetch-retries=3
      - run: npm run lint --if-present
      - run: npm test --if-present
      - run: npm run build --if-present
""",
        "python": """      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install --retries 3 -r requirements.txt
      - run: python -m pytest -q
""",
        "flutter": """      - uses: subosito/flutter-action@v2
        with:
          channel: stable
          cache: true
      - run: flutter pub get
      - run: flutter analyze
      - run: flutter test
""",
        "android": """      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: "17"
      - uses: gradle/actions/setup-gradle@v4
      - run: chmod +x gradlew
      - run: ./gradlew --no-daemon lint test assembleDebug
        env:
          GRADLE_OPTS: -Dorg.gradle.jvmargs=-Xmx3g
""",
        "go": """      - uses: actions/setup-go@v5
        with:
          go-version-file: go.mod
      - run: go vet ./...
      - run: go test ./...
""",
    }.get(stack)
    if body is None:
        raise ValueError("stack: node | python | flutter | android | go")
    return head + body


def _t_gha_deploy(p: dict[str, Any]) -> str:
    stack, app, path = _p(p, "stack", "node").lower(), _name(_p(p, "app", "app")), _p(p, "path", "/srv/app")
    host = re.sub(r"[^A-Z0-9_]", "", _p(p, "host_secret", "DEPLOY_HOST").upper()) or "DEPLOY_HOST"
    build = {"node": "      - run: npm ci && npm run build --if-present\n", "python": "", "static": ""}.get(stack, "")
    restart = {"node": f"pm2 reload {app} --update-env", "python": f"sudo systemctl restart {app}", "static": "true"}.get(stack, "true")
    return f"""name: Deploy production
# Hoola starts this ONLY after your tap on its Deploy card (workflow_dispatch). Add a required reviewer to the
# 'production' environment in GitHub > Settings > Environments for a second gate.
on:
  workflow_dispatch:
    inputs:
      sha:
        description: Commit to deploy (rollback = an older commit)
        required: true
permissions:
  contents: read
concurrency:
  group: deploy-production
  cancel-in-progress: false
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{{{ inputs.sha }}}}
{build}      - name: Upload and restart
        env:
          SSH_KEY: ${{{{ secrets.DEPLOY_SSH_KEY }}}}
          HOST: ${{{{ secrets.{host} }}}}
          SHA: ${{{{ inputs.sha }}}}
        run: |
          set -euo pipefail
          install -m 600 /dev/null ~/.ssh_key && printf '%s\\n' "$SSH_KEY" > ~/.ssh_key
          mkdir -p ~/.ssh && ssh-keyscan -H "$HOST" >> ~/.ssh/known_hosts
          rsync -az --delete --exclude .git -e "ssh -i ~/.ssh_key" ./ "deploy@$HOST:{path}/releases/$SHA/"
          ssh -i ~/.ssh_key "deploy@$HOST" "ln -sfn {path}/releases/$SHA {path}/current && cd {path}/current && {restart}"
      - name: Health check
        run: |
          set -euo pipefail
          for i in 1 2 3 4 5; do curl -fsS "${{{{ vars.HEALTH_URL }}}}" && exit 0; sleep 6; done; exit 1
"""


def _t_dockerfile(p: dict[str, Any]) -> str:
    stack, port = _p(p, "stack", "node").lower(), re.sub(r"\D", "", _p(p, "port", "3000")) or "3000"
    if stack == "python":
        return f"""FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home --uid 1000 app
USER app
EXPOSE {port}
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{port}"]
"""
    return f"""FROM node:20-slim AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build --if-present && npm prune --omit=dev

FROM node:20-slim
ENV NODE_ENV=production
WORKDIR /app
COPY --from=build /app /app
USER node
EXPOSE {port}
CMD ["node", "server.js"]
"""


def _t_nginx(p: dict[str, Any]) -> str:
    dom = re.sub(r"[^A-Za-z0-9.-]", "", _p(p, "domain", "example.com")) or "example.com"
    port = re.sub(r"\D", "", _p(p, "port", "3000")) or "3000"
    return f"""server {{
    listen 80;
    server_name {dom} www.{dom};
    return 301 https://$host$request_uri;
}}

server {{
    listen 443 ssl;
    http2 on;
    server_name {dom} www.{dom};
    ssl_certificate /etc/letsencrypt/live/{dom}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{dom}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    server_tokens off;
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Content-Type-Options nosniff always;
    client_max_body_size 20m;

    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }}
}}
"""


def _t_backup(p: dict[str, Any]) -> str:
    what = _p(p, "what", "postgres").lower()
    name = _name(_p(p, "name", "appdb"))
    keep = re.sub(r"\D", "", _p(p, "keep_days", "14")) or "14"
    dest = _p(p, "dest", "/var/backups/app")
    dump = {
        "postgres": f'pg_dump --format=custom "{name}" > "$OUT.dump"',
        "mysql": f'mysqldump --single-transaction --defaults-extra-file="$HOME/.my.cnf" "{name}" | gzip > "$OUT.sql.gz"',
        "sqlite": f'sqlite3 "{name}" ".backup \'$OUT.sqlite\'"',
        "files": f'tar -czf "$OUT.tar.gz" -C "$(dirname "{name}")" "$(basename "{name}")"',
    }.get(what)
    if dump is None:
        raise ValueError("what: postgres | mysql | sqlite | files")
    return f"""#!/usr/bin/env bash
# Hoola backup script ({what}). Review it, then run it yourself / from cron:
#   15 2 * * * /usr/local/bin/backup.sh >> /var/log/backup.log 2>&1
# Passwords: postgres -> ~/.pgpass, mysql -> ~/.my.cnf (chmod 600). Never write them here.
set -euo pipefail
DEST="{dest}"
KEEP_DAYS="{keep}"
: "${{DEST:?DEST khaali hai}}"
mkdir -p "$DEST"
STAMP="$(date +%F_%H%M)"
OUT="$DEST/{name}_$STAMP"
{dump}
# keep only the last $KEEP_DAYS days (only our own files, only inside $DEST)
find "${{DEST:?}}" -maxdepth 1 -type f -name '{name}_*' -mtime +"$KEEP_DAYS" -print -delete
echo "backup ok: $OUT"
# Copy it off this server too (rclone / another machine): a backup on the same disk is not a backup.
"""


def _t_pm2(p: dict[str, Any]) -> str:
    app, script = _name(_p(p, "app", "app")), _p(p, "script", "server.js")
    mem = re.sub(r"[^0-9MG]", "", _p(p, "memory", "500M")) or "500M"
    return f"""module.exports = {{
  apps: [
    {{
      name: "{app}",
      script: "{script}",
      instances: 1,
      exec_mode: "fork",
      max_memory_restart: "{mem}",
      max_restarts: 10,
      min_uptime: "30s",
      restart_delay: 3000,
      time: true,
      env: {{ NODE_ENV: "production" }},
    }},
  ],
}};
// Secrets go in a .env file on the server (chmod 600), never in this file.
// pm2 start ecosystem.config.js && pm2 save && pm2 startup
"""


def _t_systemd(p: dict[str, Any]) -> str:
    app, cmd, user, d = _name(_p(p, "app", "app")), _p(p, "cmd", "/usr/bin/node server.js"), _name(_p(p, "user", "app")), _p(p, "dir", "/srv/app")
    return f"""[Unit]
Description={app}
After=network-online.target
Wants=network-online.target

[Service]
User={user}
WorkingDirectory={d}
EnvironmentFile=-{d}/.env
ExecStart={cmd}
Restart=on-failure
RestartSec=5
LimitNOFILE=65535
NoNewPrivileges=true
ProtectSystem=full
PrivateTmp=true

[Install]
WantedBy=multi-user.target
"""


def _t_healthcheck(p: dict[str, Any]) -> str:
    url = _p(p, "url", "https://example.com/health")
    return f"""#!/usr/bin/env bash
# Run from cron every 5 min; exits non-zero when the site is down (your monitoring / mail picks that up).
set -euo pipefail
URL="{url}"
if ! curl -fsS --max-time 10 -o /dev/null "$URL"; then
  echo "$(date -Is) DOWN $URL" >&2
  exit 1
fi
"""


def _t_logrotate(p: dict[str, Any]) -> str:
    path = _p(p, "path", "/var/log/app/*.log")
    return f"""{path} {{
    daily
    rotate 180
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}}
# 180 days kept: CERT-In Directions (28 Apr 2022) ask ICT logs to be kept 180 days within India.
"""


def _t_ps_backup(p: dict[str, Any]) -> str:
    src, dest = _p(p, "source", "C:\\TallyPrime\\Data"), _p(p, "dest", "D:\\Backup")
    keep = re.sub(r"\D", "", _p(p, "keep_days", "30")) or "30"
    return f"""# Hoola backup (Windows). Review, then run it yourself or from Task Scheduler. Close Tally before backup.
$ErrorActionPreference = 'Stop'
$Source = '{src}'
$Dest = '{dest}'
$KeepDays = {keep}
if (-not $Source -or -not (Test-Path $Source)) {{ throw "Source folder nahi mila: $Source" }}
if (-not $Dest) {{ throw 'Dest khaali hai' }}
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
$Stamp = Get-Date -Format 'yyyy-MM-dd_HHmm'
$Zip = Join-Path $Dest "backup_$Stamp.zip"
Compress-Archive -Path (Join-Path $Source '*') -DestinationPath $Zip
Get-ChildItem -Path $Dest -Filter 'backup_*.zip' | Where-Object {{ $_.LastWriteTime -lt (Get-Date).AddDays(-$KeepDays) }} | Remove-Item
Write-Host "backup ok: $Zip"
"""
