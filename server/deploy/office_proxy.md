# Hoola browser through your own internet line (for sites that refuse servers)

Some sites (UIDAI myAadhaar, IRCTC, some bank / tax portals) refuse connections from data-centre addresses
(DigitalOcean, AWS ...). From the VPS, Hoola then sees "Access Denied" or the site never answers. The fix is to let
the browser's traffic leave through **your own office / home broadband**, which those sites accept.

1. On an always-on office machine (Linux box, Raspberry Pi, or the FNW office server) install a forward proxy:
   `sudo apt install squid apache2-utils`
   `sudo htpasswd -c /etc/squid/passwd hoola` (choose a long password)
   In `/etc/squid/squid.conf` add (before other http_access lines):
   ```
   auth_param basic program /usr/lib/squid/basic_ncsa_auth /etc/squid/passwd
   acl hoola_users proxy_auth REQUIRED
   acl vps src <YOUR_VPS_IP>/32
   http_access allow vps hoola_users
   http_access deny all
   http_port 3128
   ```
   `sudo systemctl restart squid`. Forward TCP 3128 on the office router to that machine (only from the VPS IP).
2. On the VPS put the same line in BOTH `~/apps/santosh-core/.env` and `~/apps/santosh-browser/.env`:
   `BROWSER_UPSTREAM_PROXY=http://hoola:<password>@<office-public-ip>:3128`
   Optional, only some sites: `BROWSER_UPSTREAM_HOSTS=uidai.gov.in,irctc.co.in,incometax.gov.in`
3. `pm2 restart santosh santosh-browser --update-env`, then check:
   `cd ~/apps/santosh-core && .venv/bin/python -m app.operator.check https://myaadhaar.uidai.gov.in/`
   It prints "Upstream (her own network): ..." and the page title.

Hoola's safety filter still runs first on the VPS (never a local / private address). If the office line is down,
Hoola falls back to the direct route by itself.
