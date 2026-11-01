"""v0.384 SOCIAL MEDIA MANAGER Phase 6 - WhatsApp Business on HER OWN number, by Meta's Embedded Signup.

Before this, a business typed its phone number id + a token from WhatsApp Manager into the Business inbox (v0.59). Now one
tap: Hoola's page opens Meta's own Embedded Signup popup (Facebook Login for Business with the WhatsApp configuration,
WA_ES_CONFIG_ID). She picks / creates her business, WhatsApp Business account and number on Meta's pages; Meta sends the page
the WhatsApp Business account id + phone number id and a one-time code. The server exchanges the code for her business token
(sealed), subscribes Hoola's app to her account's webhooks, registers the number for the Cloud API (a 6-digit PIN Hoola makes
and keeps sealed) and adds it as her Business inbox channel - so customers' messages reach her inbox and Hoola's
campaigns / replies go from her number.

Rules kept: official Cloud API only (never WhatsApp Web), her tap starts it, nothing is sent by connecting. Live use beyond
testers needs Newtika to be a Meta Tech Provider (Business Verification + app review)."""
from __future__ import annotations

import html
import json
import secrets
from typing import Any

from ..config import get_settings
from ..db import now, session
from . import meta as M
from .desk import SocialAccount, SocialError, _event, _hired, _take_state, _upsert_account, ensure_tables


def connect_url(tenant: str) -> str:
    """Hoola's own page that opens Meta's Embedded Signup (it needs Meta's JS SDK on a page of Hoola's domain)."""
    from ..db import MailLinkState
    _hired(tenant)
    if not M.configured("whatsapp"):
        raise SocialError("Server par WhatsApp Embedded Signup ki setting abhi nahi lagi (.env: WA_ES_CONFIG_ID + META_APP_ID / "
                          "META_APP_SECRET, PUBLIC_BASE_URL).")
    state = "soc_wh_" + secrets.token_urlsafe(24)
    with session() as s:
        s.add(MailLinkState(state=state, tenant_id=tenant, provider="social_wh"))
    return get_settings().public_base_url.rstrip("/") + "/api/social/whatsapp/start?s=" + state


def start_page(state: str) -> str:
    """The page with Meta's SDK. Meta posts {type: WA_EMBEDDED_SIGNUP, data: {waba_id, phone_number_id}} to this window
    and FB.login returns the code; both go to /api/social/whatsapp/finish with the one-time state."""
    st = get_settings()
    cfg = {"appId": st.meta_app_id, "version": st.meta_social_version, "configId": st.wa_es_config_id, "state": state}
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Connect WhatsApp Business - Hoola</title>
<style>body{{font-family:system-ui,sans-serif;max-width:520px;margin:40px auto;padding:0 16px;color:#1d1d1f;background:#fff}}
button{{font:inherit;font-size:16px;padding:12px 18px;border-radius:10px;border:0;background:#1877f2;color:#fff;cursor:pointer}}
#msg{{margin-top:18px;line-height:1.5}}.bad{{color:#b3261e}}.ok{{color:#1a7f37}}</style></head><body>
<h2>Connect your WhatsApp Business number</h2>
<p>Meta's own window opens. Choose your business, your WhatsApp Business account and the number customers will message.
Hoola never sees your Facebook password, and nothing is sent to anyone by connecting.</p>
<button id="go" type="button">Continue with Facebook</button><div id="msg" role="status"></div>
<script>window.HOOLA_ES = {html.escape(json.dumps(cfg), quote=False)};</script>
<script src="/api/social/whatsapp/es.js"></script>
<script async defer crossorigin="anonymous" src="https://connect.facebook.net/en_US/sdk.js"></script>
</body></html>"""


ES_JS = r"""(function () {
  var C = window.HOOLA_ES, info = {}, msg = document.getElementById('msg');
  function say(t, cls) { msg.className = cls || ''; msg.textContent = t; }
  window.addEventListener('message', function (ev) {
    if (!/(^|\.)facebook\.com$/.test(new URL(ev.origin).hostname)) return;
    try { var d = typeof ev.data === 'string' ? JSON.parse(ev.data) : ev.data; } catch (e) { return; }
    if (!d || d.type !== 'WA_EMBEDDED_SIGNUP') return;
    if (d.event === 'CANCEL') say('Stopped before the end' + (d.data && d.data.current_step ? ' (' + d.data.current_step + ')' : '') + '. Tap Continue to try again.', 'bad');
    if (d.event === 'ERROR') say('Meta said: ' + ((d.data && d.data.error_message) || 'error'), 'bad');
    if (d.data && d.data.waba_id) info = d.data;
  });
  window.fbAsyncInit = function () { FB.init({appId: C.appId, autoLogAppEvents: true, xfbml: false, version: C.version}); };
  document.getElementById('go').addEventListener('click', function () {
    if (!window.FB) { say('Meta is still loading - try again in a moment.'); return; }
    FB.login(function (r) {
      if (!r.authResponse || !r.authResponse.code) { say('Not connected.', 'bad'); return; }
      say('Connecting your number…');
      var tries = 0;
      (function send() {
        if (!info.waba_id && tries++ < 20) { setTimeout(send, 250); return; }
        fetch('/api/social/whatsapp/finish', {method: 'POST', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({state: C.state, code: r.authResponse.code, waba_id: info.waba_id || '', phone_number_id: info.phone_number_id || ''})})
          .then(function (x) { return x.json().then(function (j) { return [x.ok, j]; }); })
          .then(function (a) { a[0] ? say('Connected: ' + a[1].number + '. You can close this page and go back to Hoola.', 'ok') : say(a[1].detail || 'Not connected.', 'bad'); })
          .catch(function () { say('Network problem - try again.', 'bad'); });
      })();
    }, {config_id: C.configId, response_type: 'code', override_default_response_type: true,
        extras: {setup: {}, sessionInfoVersion: '3'}});
  });
})();"""


def _pin() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(6))


def finish(state: str, code: str, waba_id: str, phone_number_id: str) -> dict[str, Any]:
    from .. import accounts as acc
    from ..employee import inbox as biz
    tenant = _take_state(state, "whatsapp")
    ensure_tables()
    waba, pnid = "".join(ch for ch in str(waba_id) if ch.isdigit()), "".join(ch for ch in str(phone_number_id) if ch.isdigit())
    if not waba or not pnid:
        raise SocialError("Meta ne WhatsApp account / number nahi bheja (signup poora nahi hua). Dobara Connect kijiye.")
    st = get_settings()
    v = st.meta_social_version
    tok = M._req("GET", f"{M.FB_GRAPH}/{v}/oauth/access_token", params={"client_id": st.meta_app_id, "client_secret": st.meta_app_secret,
                                                                       "code": code})
    token = str(tok.get("access_token") or "")
    if not token:
        raise SocialError("Meta ne token nahi diya; dobara Connect kijiye.")
    info = M._req("GET", f"{M.FB_GRAPH}/{v}/{pnid}", params={"fields": "display_phone_number,verified_name,quality_rating",
                                                              "access_token": token})
    M._req("POST", f"{M.FB_GRAPH}/{v}/{waba}/subscribed_apps", data={"access_token": token})
    pin, note = _pin(), ""
    try:
        M._req("POST", f"{M.FB_GRAPH}/{v}/{pnid}/register", json={"messaging_product": "whatsapp", "pin": pin},
               params={"access_token": token})
    except M.MetaError as e:                        # e.g. a two-step PIN she set earlier: she can register it in WhatsApp Manager
        note, pin = str(e)[:200], ""
    number = str(info.get("display_phone_number") or "")
    try:
        biz.set_channel(tenant, pnid, number, token)    # her Business inbox now answers on this number
    except Exception as e:       # noqa: BLE001 - e.g. the number is joined to another Hoola business
        raise SocialError(str(e))
    with session() as s:
        row = _upsert_account(s, tenant, "whatsapp", pnid)
        row.meta_user_id = waba
        row.handle = number[:120]
        row.name = str(info.get("verified_name") or number)[:200]
        row.kind = str(info.get("quality_rating") or "")[:30]
        row.token_enc = acc.encrypt(token)
        row.user_token_enc = acc.encrypt(pin) if pin else None       # the Cloud API registration PIN, sealed
        row.scopes = "whatsapp_business_messaging,whatsapp_business_management"
        row.status = "ok"
        row.last_error = note
        row.expires_at = None
        row.connected_at = row.connected_at or now()
    _event(tenant, "connect", "ok" if not note else "warn",
           f"Connected WhatsApp Business {number}: customers' messages now reach your Business inbox."
           + (f" The number could not be registered for the Cloud API yet ({note}) - if you set a two-step PIN earlier, "
              "turn it off in WhatsApp Manager and tap Connect again." if note else ""))
    return {"platform": "whatsapp", "number": number, "accounts": [number], "registered": not note}


def disconnect(tenant: str, aid: str) -> None:
    """Called by desk.disconnect for a WhatsApp row: the Business inbox channel goes too (Meta keeps her number)."""
    from ..employee import inbox as biz
    with session() as s:
        a = s.get(SocialAccount, aid)
        pnid = a.account_id if a is not None and a.tenant_id == tenant and a.platform == "whatsapp" else ""
    if pnid:
        try:
            biz.remove_channel(tenant, pnid)
        except Exception:        # noqa: BLE001 - already removed in the inbox
            pass
