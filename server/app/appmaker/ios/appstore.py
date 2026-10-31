"""v0.338 APP STORE LAUNCH (App Sahayak Phase 7, owner: "START PHASE 7"): her iPhone app on the App Store from HER OWN
Apple account, the iPhone twin of v0.331 PLAY STORE LAUNCH.

  1. Listing: name / subtitle / keywords / description / promotional text by Opus within Apple's limits (30 / 30 / 100 /
     4000 / 170) and Apple's metadata rules (no prices, no other brands, no "best"), or a template; her edits checked.
  2. Pages Apple asks for: privacy policy (/api/app-api/<key>/privacy) and a SUPPORT page (/api/app-api/<key>/support).
  3. App Privacy answers (Apple's "nutrition label" has no API) from what this app's lists really hold + the age rating
     answer + the one-time steps in App Store Connect.
  4. Push (kind store, her builds repo on a Mac): the TestFlight build + the listing + 6.9" screenshots from an iPhone Pro
     Max simulator go onto the editable App Store version (`asc.py push`).
  5. Submit for Review (kind review): ONLY from her tap after a confirm, never from chat; Apple's review + release stay hers.

Her App Store Connect key never reaches this server: every Apple API call runs in her builds repo with its secrets."""
from __future__ import annotations

import html
import json
import logging
import re
from typing import Any

from ...db import now, session
from .. import service as AS
from ..models import AppProject
from ..android import service as AN
from ..android import store as ST
from . import service as IO

log = logging.getLogger("santosh.appmaker.ios")
LIMITS = {"name": 30, "subtitle": 30, "keywords": 100, "description": 4000, "promotionalText": 170, "whatsNew": 4000}
STORE_SHOTS = 6                    # App Store takes up to 10 per size; the first 3 are what people see

LISTING_SYSTEM = """You write an Apple App Store listing for a small Indian business's iPhone app. Return JSON
{name, subtitle, keywords, description, promotionalText}.
name <= 30 characters (the business name, maybe + 1-2 words). subtitle <= 30 characters: what the app lets a customer do.
keywords <= 100 characters: comma-separated words people search for (no spaces after commas, no repeats of the name or of
words already in name / subtitle, no other brands or competitors, no "app", no plurals of the same word).
description <= 3000 characters: 3-6 short paragraphs or simple lines starting with "• " - what you can do in the app, how
ordering / booking works, contact, area served. promotionalText <= 170 characters: one friendly line.
Only the facts given (no invented prices, offers, awards, ratings, "best", "No. 1", emoji, other brands, ALL CAPS, mentions
of Android or other platforms) - Apple's App Review Guideline 2.3. Plain English an Indian customer reads easily."""


class AppStoreError(AS.AppError):
    pass


def _load(tenant: str, ref: str) -> AppProject:
    with session() as s:
        r = AS._find(s, tenant, ref)
        s.expunge(r)
    return r


def state(r: AppProject) -> dict[str, Any]:
    return IO.state(r).get("appstore") or {}


def _put(r: AppProject, **kw) -> dict[str, Any]:
    st = dict(state(AS._load(r.id)))
    st.update(kw)
    IO._put(r.id, appstore=st)
    return st


def _facts(r: AppProject) -> dict[str, Any]:
    return {**AS._j(r.facts, {}), **{k: v for k, v in AS.gather_facts(r.tenant_id, "").items() if v}}


def _keywords(s: Any) -> str:
    words, seen = [], set()
    for w in re.split(r"[,\n]+", str(s or "")):
        w = re.sub(r"\s+", " ", w).strip().lower()
        if w and w not in seen and w not in ("app", "iphone", "android"):
            seen.add(w)
            words.append(w)
    out = ""
    for w in words:
        if len(out) + len(w) + (1 if out else 0) > LIMITS["keywords"]:
            break
        out += ("," if out else "") + w
    return out


def _template(r: AppProject, facts: dict[str, Any], kinds: list[str]) -> dict[str, str]:
    play = ST._template_listing(r, facts, kinds)
    city = str(facts.get("city") or "")
    kw = [str(r.goal or "").replace("_", " "), "order", "delivery" if "orders" in kinds else "booking", city,
          str(facts.get("category") or ""), "local", "shop"]
    return {"name": ST._clip(play["title"], 30), "subtitle": ST._clip(play["short"].split(": ", 1)[-1], 30),
            "keywords": _keywords(",".join(kw)), "description": ST._clip(play["full"], 3000),
            "promotionalText": ST._clip(str(facts.get("tagline") or play["short"]), 170)}


def listing(tenant: str, ref: str, regen: bool = False, edit: dict[str, Any] | None = None) -> dict[str, Any]:
    """Make (or redo / take her edits to) the App Store listing; every field within Apple's limits."""
    from .. import backend as BE
    r = _load(tenant, ref)
    cur = dict(state(r).get("listing") or {})
    if edit:
        for k in ("name", "subtitle", "keywords", "description", "promotionalText", "whatsNew"):
            v = edit.get(k)
            if isinstance(v, str) and v.strip():
                v = _keywords(v) if k == "keywords" else v.strip()
                if len(v) > LIMITS[k]:
                    raise AppStoreError(f"{k}: App Store {LIMITS[k]} akshar tak leta hai ({len(v)} hain).")
                cur[k] = v
        cur["edited"] = True
    elif regen or not cur.get("name"):
        facts = _facts(r)
        kinds = [c["key"] for c in BE.schema(r)["collections"]]
        made = None
        try:
            from ...site import ai as SA
            got = SA.ask_json(LISTING_SYSTEM, "FACTS (data): " + json.dumps({k: facts.get(k) for k in ("name", "tagline", "about", "address",
                              "city", "hours", "phone", "upi_id") if facts.get(k)}, ensure_ascii=False)
                              + f"\nAPP LISTS: {', '.join(kinds)}\nAPP NAME: {r.name}", 2500, "app_edit")
            if isinstance(got, dict) and got.get("name") and got.get("description"):
                made = {"name": ST._clip(got["name"], 30), "subtitle": ST._clip(got.get("subtitle"), 30),
                        "keywords": _keywords(got.get("keywords")), "description": ST._clip(got.get("description"), 4000),
                        "promotionalText": ST._clip(got.get("promotionalText"), 170)}
        except Exception:                               # noqa: BLE001
            log.info("app store listing: template", exc_info=True)
        cur = made if made else _template(r, facts, kinds)
        cur["by"] = "opus" if made else "template"
    _put(r, listing=cur)
    return view(_load(tenant, ref))


# ---------------------------------------------------------------- pages + answers
def support_html(r: AppProject) -> str:
    """The Support URL Apple requires: who runs the app and how to reach them."""
    f = _facts(r)
    rows = [(lbl, f.get(k)) for lbl, k in (("Phone", "phone"), ("Email", "email"), ("Address", "address"), ("Hours", "hours")) if f.get(k)]
    body = (f"<p>{html.escape(str(f.get('about') or f.get('tagline') or ''))}</p>"
            + "".join(f"<p><b>{html.escape(a)}:</b> {html.escape(str(b))}</p>" for a, b in rows)
            + "<h2>Your account</h2><p>Sign in, your orders / bookings and <b>Delete my account</b> are under <b>My account</b> in the app.</p>")
    return ST._page(f"{r.name or 'App'} - Support", body)


def privacy_answers(r: AppProject) -> list[dict[str, Any]]:
    """App Store Connect > App Privacy (no API): each data type the app collects, why, linked to the user, no tracking."""
    from .. import backend as BE
    sc = BE.schema(r)
    fields = [f for c in sc["collections"] for f in c["fields"] if not f.get("hidden")]
    types = {f.get("type") for f in fields}
    keys = {f["key"] for f in fields}
    out = [{"type": "Contact Info > Email Address", "why": "App Functionality (sign-in)"},
           {"type": "Contact Info > Name", "why": "App Functionality (account, orders / bookings)"}]
    if "phone" in types:
        out.append({"type": "Contact Info > Phone Number", "why": "App Functionality (to reach you about your order / booking)"})
    if "address" in keys:
        out.append({"type": "Contact Info > Physical Address", "why": "App Functionality (delivery / visit)"})
    if "location" in types:
        out.append({"type": "Location > Precise Location", "why": "App Functionality (only when you tap Use my location)"})
    if "photo" in types:
        out.append({"type": "User Content > Photos or Videos", "why": "App Functionality (only photos you attach)"})
    if sc.get("order"):
        out.append({"type": "Purchases > Purchase History", "why": "App Functionality (your orders)"})
    out.append({"type": "Diagnostics > Crash Data", "why": "App Functionality (fixing crashes; no personal data)", "linked": False})
    for x in out:
        x.setdefault("linked", True)
        x["tracking"] = False
    return out


ONE_TIME = [
    "App Store Connect > My Apps > + > New App: platform iOS, the name, primary language English, the bundle ID on this card, SKU = the bundle ID.",
    "App Information: category (e.g. Shopping / Food & Drink / Lifestyle), content rights = does not use third-party content.",
    "Age Rating: answer None to every question (the app has no such content) -> 4+.",
    "App Privacy: Get Started -> add the data types listed here, each 'linked to the user', 'not used for tracking'; paste the privacy policy URL.",
    "Pricing and Availability: Free, India (or all countries).",
    "Agreements, Tax and Banking: the Free Apps agreement is active (accepted once for the Apple Developer account).",
]


# ---------------------------------------------------------------- push + submit (on her builds repo's Mac)
def _store_json(r: AppProject, ist: dict[str, Any], st: dict[str, Any]) -> dict[str, Any]:
    base = (AS._settings().public_base_url or "").rstrip("/")
    key = AN.state(r).get("app_key") or AN._app_key(r)
    tf = ist.get("testflight") or {}
    lst = dict(st.get("listing") or {})
    if (ist.get("history") or [])[:-1] and not lst.get("whatsNew"):
        last = (ist.get("history") or [{}])[-1]
        if last.get("written"):
            lst["whatsNew"] = "Improvements to " + ", ".join(str(x).replace("_", " ") for x in last["written"][:4]) + "."
    shots = [s for s in (ist.get("qa") or {}).get("shots") or [] if s not in ("hoola_login", "hoola_account", "privacy", "delete_account")]
    order = ["app_start"] + [s for s in shots if s != "app_start"]
    return {"version": str(tf.get("version") or ""), "build": str(tf.get("build") or ""), "locale": "en-US", "listing": lst,
            "privacyPolicyUrl": f"{base}/api/app-api/{key}/privacy", "supportUrl": f"{base}/api/app-api/{key}/support",
            "shots": order[:STORE_SHOTS], "not_first": bool(st.get("pushed"))}


def _ready_for_push(r: AppProject) -> tuple[dict[str, Any], dict[str, Any]]:
    ist, st = IO.state(r), state(r)
    if not (ist.get("testflight") or {}).get("build"):
        raise AppStoreError("Pehle iPhone app TestFlight par bhejiye: App Store usi build ko leta hai.")
    if not (st.get("listing") or {}).get("name"):
        raise AppStoreError("Pehle App Store listing banaiye.")
    if not IO.ready()["ready"]:
        raise AppStoreError(IO.ready()["why"])
    if not (AS._settings().public_base_url or "").startswith("https://"):
        raise AppStoreError("Server ka public https address (PUBLIC_BASE_URL) chahiye: privacy / support links usi par hain.")
    return ist, st


def _run(r: AppProject, kind: str) -> dict[str, Any]:
    """kind store | review on her builds repo; returns asc.py's result."""
    ist, st = IO.state(r), state(r)
    work = IO._dir(r)
    src = work / "project"
    if not (src / "project.yml").exists():
        raise AppStoreError("iPhone project nahi mila: 'iPhone app banao' dobara kahiye.")
    sj = _store_json(r, ist, st)
    (src / "hoola_qa" / "store.json").write_text(json.dumps({**sj, "bundle_id": ist.get("bundle_id") or IO.bundle_id(r)}, ensure_ascii=False, indent=1))
    key = r.id.replace("_", "-")[:60].lower()
    res = IO._mac(src, key, kind, lambda stage: _put(r, stage=stage))
    asc = res.get("asc") or {}
    if not asc:
        raise AppStoreError("Mac se App Store ka jawab nahi aaya (builds repo mein v0.338 wala hoola-ios.yml lagaiye).")
    return asc


def _bg(r: AppProject, fn) -> None:
    """A Mac run takes minutes: in the background (inline in tests), the card follows the status."""
    if AS._inline():
        fn()
        return
    import threading

    def go():
        try:
            fn()
        except Exception as e:                       # noqa: BLE001
            log.exception("app store %s", r.id)
            _put(r, status="failed", error=AS._tidy(str(e), 260), now="")
        finally:
            try:
                IO._emit(r.id, push=True)
            except Exception:                        # noqa: BLE001
                log.debug("emit", exc_info=True)
    threading.Thread(target=go, name=f"appstore-{r.id}", daemon=True).start()


def push(tenant: str, ref: str) -> dict[str, Any]:
    """Listing + 6.9" screenshots + the TestFlight build onto the App Store version (her tap or the tool)."""
    r = _load(tenant, ref)
    if state(r).get("status") in ("pushing", "submitting"):
        return view(r)
    _ready_for_push(r)
    _put(r, status="pushing", error="", now="App Store Connect par listing, screenshots aur build bhej raha hoon")
    _bg(r, lambda: _push_now(r))
    return view(_load(tenant, ref))


def _push_now(r: AppProject) -> None:
    try:
        asc = _run(r, "store")
    except AppStoreError as e:
        _put(r, status="failed", error=str(e), now="")
        return
    if not asc.get("ok"):
        _put(r, status="failed", error=why_line(asc.get("error") or ""), now="")
        return
    _put(r, status="ready", pushed=now().isoformat(), now="", error="", version=asc.get("version_string"),
         screenshots=asc.get("screenshots"), asc_state=asc.get("state"))
    AN._note(r, f"App Store par taiyaar: {r.name} v{asc.get('version_string')} - listing, {asc.get('screenshots')} screenshots aur build lag gaye. "
                "Review ke liye 'Review ke liye bhejo' aapka tap hai.")


def submit(tenant: str, ref: str, her_tap: bool = False) -> dict[str, Any]:
    """Submit for Review: ONLY her tap in the app (the tool never calls this)."""
    if not her_tap:
        raise AppStoreError("App Store review ke liye bhejna sirf aapke tap se hota hai (app ka button).")
    r = _load(tenant, ref)
    st = state(r)
    if not st.get("pushed"):
        raise AppStoreError("Pehle listing + screenshots App Store par bhejiye.")
    if st.get("status") in ("pushing", "submitting"):
        return view(r)
    _put(r, status="submitting", error="", now="Apple review ke liye bhej raha hoon")
    _bg(r, lambda: _submit_now(r))
    return view(_load(tenant, ref))


def _submit_now(r: AppProject) -> None:
    st = state(AS._load(r.id))
    try:
        asc = _run(r, "review")
    except AppStoreError as e:
        _put(r, status="failed", error=str(e), now="")
        return
    if not asc.get("ok"):
        _put(r, status="failed", error=why_line(asc.get("error") or ""), now="")
        return
    subs = list(st.get("submissions") or []) + [{"version": asc.get("version_string"), "at": now().isoformat(), "id": asc.get("submission")}]
    _put(r, status="in_review", submitted=now().isoformat(), now="", error="", submissions=subs[-10:])
    AN._note(r, f"{r.name} v{asc.get('version_string')} Apple review mein bhej di. Apple aam taur par 1-2 din leta hai; jawab App Store "
                "Connect aur aapke email par aayega. Approve hone ke baad release ka button bhi aapka hai.")


def why_line(err: str) -> str:
    """Apple's refusal -> the step SHE takes (never a raw log)."""
    e = err or ""
    if "MISSING_SECRET" in e:
        return "Builds repo ke Secrets mein App Store Connect key nahi mili: " + e.split("MISSING_SECRET", 1)[1].strip() + "."
    if "NO_APP_RECORD" in e:
        return "App Store Connect mein yeh app abhi bani nahi: My Apps > + > New App, bundle ID wahi jo card par hai."
    if "NO_BUILD" in e:
        return "Yeh build App Store Connect mein nahi mila: pehle 'TestFlight par bhejo' kijiye."
    if "BUILD_PROCESSING" in e:
        return "Apple abhi build process kar raha hai (10-30 minute). Thodi der baad dobara bhejiye."
    if "1320x2868" in e:
        return "Screenshot ka size App Store ke 6.9-inch slot se match nahi hua; builds repo ka naya hoola-ios.yml lagaiye."
    if re.search(r"401|NOT_AUTHORIZED|authentication", e, re.I):
        return "App Store Connect key kaam nahi kar rahi (Key ID / Issuer ID / .p8 check kijiye; Admin ya App Manager access chahiye)."
    if re.search(r"STATE_ERROR|ENTITY_ERROR|missing|required", e, re.I):
        return "App Store Connect ne kuch adhoora bataya: " + AS._tidy(e, 220) + " (App Information / Age Rating / App Privacy bhara hai?)"
    return "App Store Connect: " + AS._tidy(e, 260)


def view(r: AppProject) -> dict[str, Any]:
    st, ist = state(r), IO.state(r)
    base = (AS._settings().public_base_url or "").rstrip("/")
    key = AN.state(r).get("app_key") or AN._app_key(r)      # the app's stable public key (made once)
    tf = ist.get("testflight") or {}
    lst = st.get("listing") or {}
    steps = [{"id": "testflight", "label": "TestFlight build", "done": bool(tf.get("build")),
              "value": f"v{tf.get('version')} ({tf.get('build')})" if tf.get("build") else ""},
             {"id": "listing", "label": "App Store listing", "done": bool(lst.get("name")), "value": lst.get("name") or ""},
             {"id": "pushed", "label": "Listing + screenshots + build on App Store Connect", "done": bool(st.get("pushed")),
              "value": f"v{st.get('version')} · {st.get('screenshots') or 0} screenshots" if st.get("pushed") else ""},
             {"id": "review", "label": "Submitted for review (your tap)", "done": bool(st.get("submitted")), "value": (st.get("submitted") or "")[:10]}]
    return {"id": r.id, "name": r.name, "bundle_id": ist.get("bundle_id") or IO.bundle_id(r), "status": st.get("status") or "",
            "now": st.get("now") or "", "error": st.get("error") or "", "steps": steps, "listing": lst, "limits": LIMITS,
            "privacy_url": f"{base}/api/app-api/{key}/privacy" if key else "", "support_url": f"{base}/api/app-api/{key}/support" if key else "",
            "privacy_answers": privacy_answers(r) if key else [], "age_rating": "4+ (answer None to every question)",
            "one_time": ONE_TIME, "submissions": list(reversed(st.get("submissions") or [])), "runner": IO.ready()}


def get(tenant: str, ref: str) -> dict[str, Any]:
    return view(_load(tenant, ref))
