"""v0.774 CONNECTORS PAGE: the page a sign-in lands on (MCP OAuth /bazar/link/callback and Composio
/bazar/composio/callback) - one page for the phone AND the web console.

Before v0.774 both pages always jumped to `santosh://bazar?linked=1`, the phone app's own deep link. A sign-in
started from the web console therefore ended on a computer that has no handler for that address: a dead page.

How it decides, with no change to the sign-in URLs (the MCP redirect_uri is registered with each server and cannot
carry a flag):
- the console writes `hoola.connect.pending` (a timestamp) into localStorage right before it opens the sign-in tab;
- this page is served from the SAME origin, so it can read that key. Fresh (under 20 minutes) = a console sign-in:
  it tells the console tab through BroadcastChannel('hoola-connect') AND a localStorage `hoola.connect.done` write
  (the `storage` event reaches older browsers), then closes itself, or says it can be closed;
- no key (the phone's browser has its own storage) = the phone: the old deep link back into the app, unchanged.

Nothing secret is on the page: the app name and ok / not-ok only. Every value is HTML-escaped and the JSON for the
script is escaped for a <script> block.
"""
from __future__ import annotations

import json
from html import escape

WEB_WINDOW_MS = 20 * 60 * 1000


def render(ok: bool, title: str, detail: str, app_link: str, name: str = "") -> str:
    t, d = escape(title), escape(detail)
    data = json.dumps({"ok": bool(ok), "name": name, "link": app_link}).replace("<", "\\u003c")
    mark = ("<path d='M5 12.5l4.2 4.2L19 7'/>" if ok else "<path d='M12 7v6M12 17h.01'/>")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{'Connected' if ok else 'Not connected'} · Hoola</title>
<style>
:root{{--bg:#fff;--ink:#1A1A1F;--mut:#5C5C63;--line:#ECECEA;--pri:#5B45E0;--ok:#13875F;--bad:#C94343}}
@media (prefers-color-scheme:dark){{:root{{--bg:#110F20;--ink:#ECEAF8;--mut:#ABA6C8;--line:#2A2644;--pri:#9C88FF;--ok:#3FCB98;--bad:#F27D7D}}}}
*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;display:grid;place-items:center;background:var(--bg);color:var(--ink);
font:15px/1.5 'Schibsted Grotesk',system-ui,-apple-system,'Segoe UI',sans-serif;padding:24px}}
.c{{max-width:420px;width:100%;text-align:center;border:1px solid var(--line);border-radius:20px;padding:36px 28px}}
.i{{width:56px;height:56px;border-radius:50%;display:grid;place-items:center;margin:0 auto 18px;
background:color-mix(in srgb,var({'--ok' if ok else '--bad'}) 12%,transparent);color:var({'--ok' if ok else '--bad'})}}
h1{{font-size:20px;font-weight:600;margin:0 0 8px}}p{{color:var(--mut);margin:0 0 22px}}
a{{display:inline-block;background:var(--pri);color:#fff;text-decoration:none;border-radius:10px;padding:10px 18px;font-weight:500}}
.s{{font-size:13px;color:var(--mut);margin-top:14px}}
</style></head><body><main class="c" role="status">
<div class="i"><svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"
stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{mark}</svg></div>
<h1>{t}</h1><p>{d}</p><a id="go" href="{escape(app_link)}">Back to Hoola</a><div class="s" id="s"></div></main>
<script>(function(){{var D={data},web=false;
try{{var p=+localStorage.getItem('hoola.connect.pending')||0;web=p&&Date.now()-p<{WEB_WINDOW_MS};}}catch(e){{}}
if(web){{var msg={{type:'connector-done',ok:D.ok,name:D.name,at:Date.now()}};
try{{new BroadcastChannel('hoola-connect').postMessage(msg);}}catch(e){{}}
try{{localStorage.setItem('hoola.connect.done',JSON.stringify(msg));localStorage.removeItem('hoola.connect.pending');}}catch(e){{}}
var a=document.getElementById('go');a.href='/console/';a.textContent='Back to the console';
document.getElementById('s').textContent='You can close this tab - the console has been updated.';
setTimeout(function(){{try{{window.close();}}catch(e){{}}}},1400);}}
else{{setTimeout(function(){{location.href=D.link;}},800);}}}})();</script></body></html>"""
