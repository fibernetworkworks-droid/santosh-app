# Hoola Website hosting (v0.122) — one-time server setup

Websites Hoola launches are served by the Hoola server itself (`app/site/hosting.py`, HTTP middleware by Host name).
Nothing goes live until the owner taps "Haan, live karo".

## 1. Free Hoola addresses (`<name>.<SITES_BASE_DOMAIN>`)
1. Pick a domain Newtika owns only for customer sites (NOT the API domain), e.g. `hoolasites.in`.
2. Put it on Cloudflare. DNS: `*` and `@` → A record → the VPS IP, **proxied (orange cloud)**. SSL mode: Full.
3. nginx (v0.224): nginx itself serves the live sites, so a Hoola restart / deploy / crash no longer takes them down.
   Generate the server block on the VPS and include it inside `http { }` (keep the API block as it is):
   ```
   cd ~/apps/santosh-core && .venv/bin/python -m app.site.edge conf \
       --cert /etc/ssl/hoolasites-origin.pem --key /etc/ssl/hoolasites-origin.key > /tmp/hoola-sites.conf
   sudo cp /tmp/hoola-sites.conf /etc/nginx/conf.d/hoola-sites.conf && sudo nginx -t && sudo systemctl reload nginx
   ```
   It serves `data/hosted_enabled/$host` (Hoola keeps that folder in step with every launch / rollback / take-down: no
   nginx reload ever needed), sends her bare domain to www, lets only `/api/site-forms/` reach Hoola (every other
   `/api/` is 404) and hands any host it doesn't know to Hoola (the old Python serving stays as the fallback).
   **nginx's user (`www-data`) must be able to read the files**: `sudo setfacl -R -m u:www-data:rX ~/apps/santosh-core/data/hosted
   ~/apps/santosh-core/data/hosted_enabled && sudo setfacl -m u:www-data:x ~ ~/apps ~/apps/santosh-core ~/apps/santosh-core/data`
   and `sudo setfacl -R -d -m u:www-data:rX ~/apps/santosh-core/data/hosted` (new sites inherit it). nginx also writes
   `data/hosted_access.log` (visits): `sudo setfacl -m u:www-data:rwx ~/apps/santosh-core/data`. Check from the VPS:
   `curl -H 'Host: <slug>.hoolasites.in' http://127.0.0.1/` returns the site with `pm2 stop santosh` too.
4. `.env`: `SITES_BASE_DOMAIN=hoolasites.in` and `PUBLIC_BASE_URL=https://<api host>` (site forms post there).

## 1b. Caddy instead of nginx (the Hoola VPS: the 443 edge is the `fnwconnect_caddy` container) (v0.277)
Caddy asks Hoola before making any certificate (`/api/hosting/ask`: 200 only for addresses of launched sites, and for a
direct-mode domain only once its records point here). Caddy allows ONE global `{ }` block, at the top of the file: put
`on_demand_tls` inside the existing one. Edit the bind-mounted Caddyfile IN PLACE (a replaced file is not seen by the
container), then `docker exec <caddy> caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile` and
`caddy reload` (no downtime; a failed reload keeps the old config).
```
{
	on_demand_tls {
		ask http://172.18.0.1:8077/api/hosting/ask
	}
}

# Hoola websites: free addresses AND her own domains (direct mode); a certificate only when Hoola says yes
https:// {
	tls {
		on_demand
	}
	encode gzip
	reverse_proxy 172.18.0.1:8077
}
```
The catch-all `https://` only takes names no other site block of the file names. Free addresses need the DNS wildcard
`*.sites` A -> the VPS IP (GoDaddy) and `SITES_BASE_DOMAIN=sites.ainewtika.com`.

## 2a. Her own domain, DIRECT MODE (v0.277, like Lovable; no Cloudflare needed)
`.env`: `SITES_DIRECT_IP=<the VPS public IP>`. Joining her domain gives her three records for ANY registrar (GoDaddy,
Hostinger, BigRock, Cloudflare with the orange cloud OFF, Porkbun): `A @ -> IP`, `A www -> IP`, `TXT _hoola -> hoola_verify=...`
(applied by Hoola on her tap when her DNS is on her Cloudflare / Porkbun, or on Newtika's Cloudflare for a domain bought
through Hoola). The worker shows Verifying -> Setting up -> Live; the certificate is made by the edge above on the first
visit. Bare domain is main by default, www 301s to it ("Main banao" switches). If Cloudflare for SaaS (section 2) is
configured too, SaaS is used instead.

## 2. Her own domain through Cloudflare for SaaS
1. In the `hoolasites.in` zone: SSL/TLS → Custom Hostnames → enable; fallback origin = `origin.hoolasites.in`
   (an A record → VPS IP, proxied).
2. Make an API token with `Zone: SSL and Certificates: Edit` + `Zone: Read` on that zone only.
3. `.env`: `SITES_ORIGIN=origin.hoolasites.in`, `SITES_CF_TOKEN=<token>`, `SITES_CF_ZONE_ID=<zone id>`.
   Then her `www` (and apex when her DNS is on Cloudflare) gets a custom hostname; Hoola shows the exact DNS records and,
   if her own Cloudflare token is saved in the app, applies them only on her tap (snapshot + undo for 7 days).

Without SaaS: if her domain is in HER Cloudflare account, Hoola proxies it to `SITES_ORIGIN_IP` (set it to the VPS IP).

## 3. Restart
`cd ~/santosh_app && git pull && cp -r server/app ~/apps/santosh-core/ && pm2 restart santosh --update-env`

Check: `curl -H 'Host: <slug>.hoolasites.in' http://172.18.0.1:8077/` after a launch returns the site.

## 4. Outside uptime check (v0.224)
`.github/workflows/site-uptime.yml` opens every live site every 15 minutes from GitHub's machines (it also sees the times
the whole server is down) and reports back; a failed run = GitHub emails the repo owner. Set the same long random value
as `SITES_UPTIME_KEY` in the VPS `.env` and as a repo secret, plus the repo secret `HOOLA_URL=https://<api host>`.

## 5. Daily backup of the website files (v0.224)
Litestream backs up only the database. Set `SITES_BACKUP_BUCKET`, `SITES_BACKUP_ENDPOINT` (R2 / B2 / Spaces; empty = AWS),
`SITES_BACKUP_KEY_ID`, `SITES_BACKUP_SECRET` (a key limited to that bucket) in `.env`: every day after 03:00 IST one
tar.gz of `data/hosted` + every site's `src` goes to `hoola/sites/<date>.tar.gz`; older than `SITES_BACKUP_KEEP_DAYS`
(14) is deleted. Restore into a folder first: `.venv/bin/python -m app.site.backup restore 2026-10-29 /tmp/sites-restore`.
