# Hoola Website hosting (v0.122) — one-time server setup

Websites Hoola launches are served by the Hoola server itself (`app/site/hosting.py`, HTTP middleware by Host name).
Nothing goes live until the owner taps "Haan, live karo".

## 1. Free Hoola addresses (`<name>.<SITES_BASE_DOMAIN>`)
1. Pick a domain Newtika owns only for customer sites (NOT the API domain), e.g. `hoolasites.in`.
2. Put it on Cloudflare. DNS: `*` and `@` → A record → the VPS IP, **proxied (orange cloud)**. SSL mode: Full.
3. nginx: a server block that accepts any host and proxies to the app (keep the API block as it is):
   ```
   server {
       listen 80 default_server;
       listen 443 ssl default_server;            # Cloudflare origin certificate for *.hoolasites.in
       server_name _;
       ssl_certificate     /etc/ssl/hoolasites-origin.pem;
       ssl_certificate_key /etc/ssl/hoolasites-origin.key;
       client_max_body_size 1m;
       location / {
           proxy_pass http://172.18.0.1:8077;
           proxy_set_header Host $host;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto https;
       }
   }
   ```
4. `.env`: `SITES_BASE_DOMAIN=hoolasites.in` and `PUBLIC_BASE_URL=https://<api host>` (site forms post there).

## 2. Her own domain through Cloudflare for SaaS (recommended)
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
