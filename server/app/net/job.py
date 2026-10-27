"""v0.113 The job card of a service deal: on the way, arrived, extra work approved line by line, proof photos, the bill,
the warranty, reschedule and warranty revisits - all signed steps of the same deal (research Diagrams 4.1 / 4.5 / 6.9).

States (deal.TRANSITIONS): accepted (booked) -> deal_status on_the_way -> on_way -> deal_status arrived -> working ->
job_done -> handed_over -> (dealpay: ok / dispute) -> closed. Kinds handled here:
  job_estimate   seller -> buyer  {v, lines [{id, item, price, gst_pct, amount, gst, note}]}   extra work found on site
  job_approve    buyer  -> seller {v, yes [ids], no [ids]}     ONLY from her tap (API); each line is its own yes / no
  job_photo      seller -> buyer  {photos [{pid, stage before|after|intake|proof, share_id, sha256, name, mime, size}]}
  job_done       seller -> buyer  {summary, bill {lines, subtotal, gst, total, adjusted}, warranty {days, until, covers}}
  job_slots      seller -> buyer  {purpose resched|warranty, slots}        new times to choose from
  job_slot_pick  buyer  -> seller {purpose, slot}                         her tap
  job_resched    buyer  -> seller {note}                                  "can we move it?"
  job_warranty   buyer  -> seller {note}                                  a claim inside the warranty
  job_warranty_done seller -> buyer {summary}                             the free revisit was done
The BILL is made by code from the quote lines + the extra lines she said yes to; the buyer's Hoola recomputes it and
refuses any bill with work she did not approve (the classic "work done without asking"). The visit charge is waived in
the bill when real work was done and the seller's rule says it is adjusted. Money then goes the deal's normal way
(dealpay: payment card locked to the bill, receipt, khata, dispute). Photos are fetched by the buyer's Hoola from the
seller's one-time share, checked to really be pictures, re-encoded (no EXIF / location kept) and kept for this job only.
"""
from __future__ import annotations

import hashlib
import io
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ..db import new_id, now, session
from . import identity as idn
from . import policy

STEP_KINDS = {"job_estimate", "job_approve", "job_photo", "job_done", "job_slots", "job_slot_pick", "job_resched",
              "job_warranty", "job_warranty_done"}
SELLER_KINDS = {"job_estimate", "job_photo", "job_done", "job_slots", "job_warranty_done"}
BUYER_KINDS = {"job_approve", "job_slot_pick", "job_resched", "job_warranty"}
STAGES = ("intake", "before", "after", "proof")
MAX_PHOTOS, MAX_PHOTO_MB = 30, 12
STATS = {"estimates": 0, "approved": 0, "refused_bills": 0, "photos": 0, "done": 0, "claims": 0}


def _dl():
    from . import deal as dl
    return dl


def _job(d) -> dict[str, Any]:
    return dict(d.job or {})


def _dir(tenant: str, deal_id: str) -> Path:
    import re
    p = Path("data") / "hoola_jobs" / re.sub(r"[^A-Za-z0-9_-]", "_", tenant)[:64] / deal_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def _clean_image(data: bytes) -> bytes:
    """A real picture, re-saved as JPEG (max 1600 px): EXIF / GPS / anything hidden is dropped."""
    from PIL import Image
    if not data or len(data) > MAX_PHOTO_MB * 1024 * 1024:
        raise _dl().DealError(f"Photo khaali hai ya {MAX_PHOTO_MB} MB se badi.")
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:
        raise _dl().DealError("Yeh photo nahi lagti.")
    img = img.convert("RGB")
    img.thumbnail((1600, 1600))
    out = io.BytesIO()
    img.save(out, "JPEG", quality=84)
    return out.getvalue()


# ---------------------------------------------------------------- seller
def _need_seller(d, states: tuple[str, ...]) -> None:
    dl = _dl()
    from . import booking
    if d.role != "seller" or not booking.is_service(d):
        raise dl.DealError("Yeh service ka kaam aapki taraf se nahi.")
    if d.state not in states:
        raise dl.DealError(f"Abhi '{dl.STATE_WORDS.get(d.state, d.state)}' hai; yeh nahi ho sakta.")


def on_the_way(tenant: str, deal_id: str, eta_minutes: Any = None, note: str = "") -> dict[str, Any]:
    dl = _dl()
    d = dl._get(tenant, deal_id)
    _need_seller(d, ("accepted",))
    m = dl._num(eta_minutes, 1, 600) if eta_minutes not in (None, "") else None
    eta = (now() + timedelta(minutes=m)).replace(microsecond=0).isoformat() if m else ""
    j = _job(d)
    j["eta"] = eta
    d.job = j
    dl._send(tenant, d, "deal_status", {"status": "on_the_way", "eta": eta, "note": policy.quote(note, 200)},
             "Raste mein" + (f", {int(m)} min" if m else ""))
    return {"status": "on_way", "deal": dl.view(dl._get(tenant, deal_id))}


def arrived(tenant: str, deal_id: str, note: str = "") -> dict[str, Any]:
    dl = _dl()
    d = dl._get(tenant, deal_id)
    _need_seller(d, ("accepted", "on_way"))
    dl._send(tenant, d, "deal_status", {"status": "arrived", "note": policy.quote(note, 200)}, "Pahunch gaye, kaam shuru")
    return {"status": "working", "deal": dl.view(dl._get(tenant, deal_id))}


def estimate(tenant: str, deal_id: str, lines: Any) -> dict[str, Any]:
    """Extra work found on site: each line goes to the customer for its own yes / no (nothing is billed without it)."""
    dl = _dl()
    d = dl._get(tenant, deal_id)
    _need_seller(d, ("accepted", "on_way", "working"))
    if not isinstance(lines, list) or not lines or len(lines) > 20:
        raise dl.DealError("lines: [{item, price, gst_pct, note}] (1-20)")
    j = _job(d)
    extras = list(j.get("extras") or [])
    v = int(j.get("est_v") or 0) + 1
    new = []
    for x in lines:
        if not isinstance(x, dict):
            raise dl.DealError("line galat")
        item = policy.clean_name(x.get("item"), 120)
        price = dl._num(x.get("price"), 0, dl.MAX_TOTAL)
        qty = dl._num(x.get("qty", 1), 0.001, 1e4)
        g = dl._num(x.get("gst_pct", 0), 0, 40)
        if not item or price is None or qty is None or g is None or g not in dl.GST_RATES:
            raise dl.DealError(f"'{x.get('item')}': kaam, daam aur sahi GST % chahiye")
        ln = dl._line(item, qty, qty, policy.clean_name(x.get("unit"), 20), price, g, "ok")
        ln |= {"id": f"x{len(extras) + len(new) + 1}", "note": policy.quote(x.get("note"), 200), "v": v, "status": "pending"}
        new.append(ln)
    if policy.secret_found(policy.all_text({"l": new})):
        raise dl.DealError("Isme mana ki gayi jaankari hai.")
    j["extras"], j["est_v"] = extras + new, v
    d.job = j
    body = {"v": v, "lines": [{k: l[k] for k in ("id", "item", "qty", "unit", "price", "gst_pct", "amount", "gst", "note")}
                              for l in new]}
    dl._send(tenant, d, "job_estimate", body, f"Extra kaam ka estimate: {dl.inr(sum(l['amount'] + l['gst'] for l in new))}")
    STATS["estimates"] += 1
    return {"status": "estimate_sent", "deal": dl.view(dl._get(tenant, deal_id))}


def add_photo(tenant: str, deal_id: str, data: bytes, name: str = "photo.jpg", stage: str = "after") -> dict[str, Any]:
    """Proof photos: kept for this job and sent to the customer's Hoola (a one-time share; it fetches and checks it)."""
    dl = _dl()
    d = dl._get(tenant, deal_id)
    _need_seller(d, ("accepted", "on_way", "working", "handed_over", "closed", "disputed"))
    stage = stage if stage in STAGES else "after"
    j = _job(d)
    photos = list(j.get("photos") or [])
    if len(photos) >= MAX_PHOTOS:
        raise dl.DealError(f"Ek kaam mein {MAX_PHOTOS} photo tak.")
    img = _clean_image(data)
    pid = new_id("jp")[:16]
    path = _dir(tenant, d.id) / f"{pid}.jpg"
    path.write_bytes(img)
    from .share import _share
    sh = _share(tenant, d.peer, f"{d.number or 'job'}_{stage}_{len(photos) + 1}.jpg", img, "image/jpeg")
    rec = {"pid": pid, "stage": stage, "path": str(path), "sha256": hashlib.sha256(img).hexdigest(), "at": now().isoformat()}
    j["photos"] = photos + [rec]
    d.job = j
    dl._send(tenant, d, "job_photo", {"photos": [{"pid": pid, "stage": stage, "share_id": sh["share_id"], "sha256": sh["sha256"],
                                                  "name": sh["name"], "mime": "image/jpeg", "size": sh["size"]}]},
             f"Photo ({stage})")
    STATS["photos"] += 1
    return {"status": "photo_sent", "pid": pid, "deal": dl.view(dl._get(tenant, deal_id))}


def add_photo_file(tenant: str, deal_id: str, file_id: str, stage: str = "after") -> dict[str, Any]:
    from ..mailbox import service as ms
    try:
        name, _mime, data = ms.load_files(tenant, [{"type": "file", "file_id": file_id}])[0]
    except Exception as e:
        raise _dl().DealError(f"Photo {file_id} nahi mili: {e}")
    return add_photo(tenant, deal_id, data, name, stage)


def build_bill(d, extras: list[dict[str, Any]], adjust: bool) -> dict[str, Any]:
    """Quote lines + the extra lines she said YES to. Visit charge waived when real work was done and the rule says so."""
    dl = _dl()
    q = d.quote or {}
    base = [dict(l) for l in q.get("lines") or [] if float(l.get("qty") or 0) > 0]
    yes = [dict(l) for l in extras if l.get("status") == "yes"]
    work = [l for l in base if "visit" not in dl.norm(l["item"])] + yes
    adjusted = False
    lines = []
    for l in base:
        is_visit = "visit" in dl.norm(l["item"])
        if is_visit and adjust and any(float(w.get("amount") or 0) > 0 for w in work):
            lines.append(dl._line(l["item"], float(l["qty"]), float(l["qty"]), l.get("unit", ""), 0.0, l["gst_pct"], "ok") |
                         {"from": "quote", "waived": True})
            adjusted = True
        else:
            lines.append({k: l[k] for k in ("item", "qty", "unit", "price", "gst_pct", "amount", "gst")} | {"from": "quote"})
    for l in yes:
        lines.append({k: l[k] for k in ("item", "qty", "unit", "price", "gst_pct", "amount", "gst")} | {"from": "extra",
                                                                                                     "id": l["id"]})
    sub = dl._r2(sum(float(l["amount"]) for l in lines))
    gst = dl._r2(sum(float(l["gst"]) for l in lines))
    return {"lines": lines, "subtotal": sub, "gst": gst, "total": dl._r2(sub + gst), "adjusted": adjusted}


def done(tenant: str, deal_id: str, summary: str = "", warranty_days: Any = None, covers: str = "") -> dict[str, Any]:
    """Work finished: the bill (by code), the warranty, then the deal's normal money + 'sab sahi?' steps."""
    dl = _dl()
    from . import booking
    d = dl._get(tenant, deal_id)
    _need_seller(d, ("accepted", "on_way", "working"))
    j = _job(d)
    pending = [l["item"] for l in j.get("extras") or [] if l.get("status") == "pending"]
    if pending:
        raise dl.DealError("Graahak ki haan / na baaki hai: " + ", ".join(pending) + ". Pehle unka jawab aane dijiye.")
    r = booking.rules(tenant)
    bill = build_bill(d, list(j.get("extras") or []), r.visit_adjust)
    wd = dl._num(warranty_days, 0, 3650) if warranty_days not in (None, "") else ((d.quote or {}).get("service") or {}).get(
        "warranty_days", r.warranty_days)
    wd = int(wd or 0)
    until = (now() + timedelta(days=wd)).date().isoformat() if wd else ""
    warranty = {"days": wd, "until": until, "covers": policy.quote(covers, 200) or ((d.quote or {}).get("service") or {}).get("what", "")}
    body = {"summary": policy.quote(summary, 600), "bill": bill, "warranty": warranty}
    j |= {"bill": bill, "warranty": warranty, "summary": body["summary"]}
    d.job = j
    p = dict(d.pay or {})
    if p:
        p["due"] = bill["total"]
        d.pay = p
    d.handed_at = now()
    dl._send(tenant, d, "job_done", body, f"Kaam poora, bill {dl.inr(bill['total'])}")
    STATS["done"] += 1
    _after_done(tenant, d.id, "seller")
    d = dl._get(tenant, deal_id)
    dl._publish(tenant, d, "info", f"Kaam {d.number} poora: bill {dl.inr(bill['total'])}" +
                (" (visit charge adjust)" if bill["adjusted"] else "") + (f", warranty {wd} din." if wd else "."))
    return {"status": d.state, "bill": bill, "deal": dl.view(d)}


def _after_done(tenant: str, deal_id: str, side: str) -> None:
    """Khata: the bill goes in now (not at booking). UPI: the payment card for the bill goes by itself (seller)."""
    dl = _dl()
    d = dl._get(tenant, deal_id)
    p = d.pay or {}
    total = float(((d.job or {}).get("bill") or {}).get("total") or 0)
    if p.get("choice") == "khata" and total > 0 and not p.get("khata_booked"):
        from . import khata
        khata.add(tenant, d.peer, "debit", total, d.number, p.get("due_on", ""), side=side)
        p = dict(p, khata_booked=True)
        d.pay = p
        dl._save(d)
    elif side == "seller" and p.get("choice") == "upi" and total > 0 and (p.get("payee") or {}).get("upi_id"):
        from . import dealpay
        try:
            dealpay.request_payment(tenant, deal_id, by="rules")
        except Exception:
            pass


def offer_slots(tenant: str, deal_id: str, purpose: str = "resched", slots: Any = None) -> dict[str, Any]:
    dl = _dl()
    from . import booking
    d = dl._get(tenant, deal_id)
    if purpose == "warranty":
        _need_seller(d, ("handed_over", "closed", "disputed"))
        if not ((d.job or {}).get("claim") or {}).get("open"):
            raise dl.DealError("Koi warranty shikayat khuli nahi.")
    else:
        purpose = "resched"
        _need_seller(d, ("accepted", "on_way"))
    if slots:
        pick = [s for s in (slots if isinstance(slots, list) else [slots]) if booking.slot_free(tenant, str(s), d.id)]
        sl = [dl._when(s).astimezone(timezone.utc).replace(microsecond=0).isoformat() for s in pick][:6]
    else:
        sl = booking.free_slots(tenant, exclude=d.id)
    if not sl:
        raise dl.DealError("Koi khaali samay nahi mila.")
    j = _job(d)
    j["offer"] = {"purpose": purpose, "slots": sl, "at": now().isoformat()}
    d.job = j
    dl._send(tenant, d, "job_slots", {"purpose": purpose, "slots": sl}, f"Naye samay ({len(sl)})" +
             (" warranty ke liye" if purpose == "warranty" else ""))
    return {"status": "slots_sent", "slots": sl, "deal": dl.view(dl._get(tenant, deal_id))}


def warranty_done(tenant: str, deal_id: str, summary: str = "") -> dict[str, Any]:
    dl = _dl()
    d = dl._get(tenant, deal_id)
    _need_seller(d, ("handed_over", "closed", "disputed"))
    j = _job(d)
    c = dict(j.get("claim") or {})
    if not c.get("open"):
        raise dl.DealError("Koi warranty shikayat khuli nahi.")
    c |= {"open": False, "done_at": now().isoformat(), "summary": policy.quote(summary, 400)}
    j["claim"] = c
    j["revisit"] = dict(j.get("revisit") or {}, status="done")
    j["claims"] = list(j.get("claims") or []) + [c]
    d.job = j
    dl._send(tenant, d, "job_warranty_done", {"summary": c["summary"]}, "Warranty ka kaam ho gaya (muft)")
    return {"status": "warranty_done", "deal": dl.view(dl._get(tenant, deal_id))}


# ---------------------------------------------------------------- buyer
def _need_buyer(d, states: tuple[str, ...]) -> None:
    dl = _dl()
    from . import booking
    if d.role != "buyer" or not booking.is_service(d):
        raise dl.DealError("Yeh aapki booking nahi.")
    if d.state not in states:
        raise dl.DealError(f"Abhi '{dl.STATE_WORDS.get(d.state, d.state)}' hai; yeh nahi ho sakta.")


def approve(tenant: str, deal_id: str, yes: Any = None, no: Any = None, by_tap: bool = False) -> dict[str, Any]:
    """Her tap on the extra-work card: yes / no per line. Only from the app (the model can never approve work)."""
    dl = _dl()
    if not by_tap:
        raise dl.DealError("Extra kaam ki haan sirf aapke tap se: card par har line ke saamne Haan / Na.")
    d = dl._get(tenant, deal_id)
    _need_buyer(d, ("accepted", "on_way", "working"))
    j = _job(d)
    ids_y = {str(x) for x in (yes or [])}
    ids_n = {str(x) for x in (no or [])}
    pend = {l["id"] for l in j.get("extras") or [] if l.get("status") == "pending"}
    if not (ids_y | ids_n) or not (ids_y | ids_n) <= pend or ids_y & ids_n:
        raise dl.DealError("Har baaki line ke liye Haan ya Na chuniye.")
    for l in j["extras"]:
        if l["id"] in ids_y:
            l["status"] = "yes"
        elif l["id"] in ids_n:
            l["status"] = "no"
    d.job = j
    v = int(j.get("est_v") or 0)
    names = [l["item"] for l in j["extras"] if l["id"] in ids_y]
    dl._send(tenant, d, "job_approve", {"v": v, "yes": sorted(ids_y), "no": sorted(ids_n)},
             ("Haan: " + ", ".join(names) if names else "Extra kaam: na") + (f"; na: {len(ids_n)}" if ids_n and names else ""))
    STATS["approved"] += len(ids_y)
    return {"status": "answered", "deal": dl.view(dl._get(tenant, deal_id))}


def pick_slot(tenant: str, deal_id: str, slot: str, by_tap: bool = False) -> dict[str, Any]:
    dl = _dl()
    if not by_tap:
        raise dl.DealError("Naya samay aapke tap se chuna jaata hai.")
    d = dl._get(tenant, deal_id)
    _need_buyer(d, ("accepted", "on_way", "handed_over", "closed", "disputed"))
    off = (d.job or {}).get("offer") or {}
    t = dl._when(slot)
    iso = t.astimezone(timezone.utc).replace(microsecond=0).isoformat() if t else ""
    if iso not in (off.get("slots") or []):
        raise dl.DealError("Inme se ek samay chuniye.")
    dl._send(tenant, d, "job_slot_pick", {"purpose": off.get("purpose", "resched"), "slot": iso}, "Naya samay chuna")
    d = dl._get(tenant, deal_id)
    _apply_pick(d, off.get("purpose", "resched"), iso)
    return {"status": "picked", "deal": dl.view(dl._get(tenant, deal_id))}


def _apply_pick(d, purpose: str, iso: str) -> None:
    dl = _dl()
    j = _job(d)
    j.pop("offer", None)
    if purpose == "warranty":
        j["revisit"] = {"slot": iso, "status": "booked"}
    else:
        d.ask = dict(d.ask or {}, slot=iso)
        tm = dict(d.timers or {})
        for k in ("rem_2h", "rem_1d", "rem_job"):
            tm.pop(k, None)
        d.timers = tm
    d.job = j
    dl._save(d)


def ask_resched(tenant: str, deal_id: str, note: str = "") -> dict[str, Any]:
    dl = _dl()
    d = dl._get(tenant, deal_id)
    _need_buyer(d, ("accepted", "on_way"))
    dl._send(tenant, d, "job_resched", {"note": policy.quote(note, 300) or "Samay badal sakte hain?"}, "Samay badalne ko kaha")
    return {"status": "asked", "say": "Dukaan / technician se naya samay maanga.", "deal": dl.view(dl._get(tenant, deal_id))}


def claim(tenant: str, deal_id: str, note: str) -> dict[str, Any]:
    dl = _dl()
    d = dl._get(tenant, deal_id)
    _need_buyer(d, ("handed_over", "closed", "disputed"))
    w = (d.job or {}).get("warranty") or {}
    if not w.get("until") or now().date().isoformat() > w["until"]:
        raise dl.DealError("Warranty nahi hai ya khatam ho chuki" + (f" ({w['until']})" if w.get("until") else "") + ".")
    if ((d.job or {}).get("claim") or {}).get("open"):
        raise dl.DealError("Warranty shikayat pehle se khuli hai.")
    note = policy.quote(note, 400)
    if not note:
        raise dl.DealError("Kya dikkat aayi? Do line mein likhiye.")
    j = _job(d)
    j["claim"] = {"open": True, "note": note, "at": now().isoformat()}
    d.job = j
    dl._send(tenant, d, "job_warranty", {"note": note}, "Warranty: " + note[:80])
    STATS["claims"] += 1
    return {"status": "claimed", "say": "Warranty ki shikayat bheji; unke naye samay aate hi bataunga.",
            "deal": dl.view(dl._get(tenant, deal_id))}


# ---------------------------------------------------------------- receiving
def receive_step(tenant: str, d, kind: str, raw: dict[str, Any], who: str, key) -> dict[str, Any]:
    dl = _dl()
    E = dl.DealError
    j = _job(d)
    if kind == "job_estimate":                            # buyer: extra work to approve, line by line
        v = dl._num(raw.get("v"), 1, 999)
        lines = raw.get("lines")
        if v is None or int(v) <= int(j.get("est_v") or 0) or not isinstance(lines, list) or not lines or len(lines) > 20:
            raise E("estimate galat")
        new = []
        have = {l["id"] for l in j.get("extras") or []}
        for x in lines:
            qty = dl._num(x.get("qty", 1), 0.001, 1e4)
            price = dl._num(x.get("price"), 0, dl.MAX_TOTAL)
            g = dl._num(x.get("gst_pct", 0), 0, 40)
            lid = policy.clean_name(x.get("id"), 12)
            if qty is None or price is None or g is None or g not in dl.GST_RATES or not lid or lid in have:
                raise E("estimate line galat")
            ln = dl._line(policy.clean_name(x.get("item"), 120) or "?", qty, qty, policy.clean_name(x.get("unit"), 20), price, g, "ok")
            for k in ("amount", "gst"):
                if abs(float(x.get(k) or 0) - ln[k]) > 0.011:
                    raise E("estimate ka hisaab galat")
            new.append(ln | {"id": lid, "note": policy.quote(x.get("note"), 200), "v": int(v), "status": "pending"})
            have.add(lid)
        dl._record(d, kind, raw, "seller", f"Extra kaam ka estimate ({len(new)})")
        j["extras"], j["est_v"] = list(j.get("extras") or []) + new, int(v)
        d.job, d.waiting = j, "approve"
        dl._save(d)
        tot = sum(l["amount"] + l["gst"] for l in new)
        dl._publish(tenant, d, "estimate", f"{who}: extra kaam mila - " + "; ".join(f"{l['item']} {dl.inr(l['amount'] + l['gst'])}"
                    for l in new) + f" (kul {dl.inr(tot)}). Har line ke liye Haan / Na; bina haan ke bill mein nahi judega.",
                    f"{who} ne on-site extra kaam ka estimate bheja ({dl.inr(tot)}). Haan / Na sirf owner ke tap se; tum approve "
                    f"nahi kar sakte. deal_id={d.id}.")
        return {"ok": True, "status": "estimate"}
    if kind == "job_approve":                             # seller: her answers
        ids_y, ids_n = {str(x) for x in raw.get("yes") or []}, {str(x) for x in raw.get("no") or []}
        pend = {l["id"] for l in j.get("extras") or [] if l.get("status") == "pending"}
        if not (ids_y | ids_n) <= pend or ids_y & ids_n:
            raise E("jawab galat")
        for l in j.get("extras") or []:
            if l["id"] in ids_y:
                l["status"] = "yes"
            elif l["id"] in ids_n:
                l["status"] = "no"
        names_y = [l["item"] for l in j["extras"] if l["id"] in ids_y]
        names_n = [l["item"] for l in j["extras"] if l["id"] in ids_n]
        dl._record(d, kind, raw, "buyer", "Graahak: haan " + (", ".join(names_y) or "-") + "; na " + (", ".join(names_n) or "-"))
        d.job = j
        dl._save(d)
        dl._publish(tenant, d, "info", f"{who}: " + (f"haan - {', '.join(names_y)}" if names_y else "") +
                    (("; " if names_y else "") + f"na - {', '.join(names_n)}" if names_n else "") + ". Sirf haan wala kaam kijiye.")
        return {"ok": True, "status": "answered"}
    if kind == "job_photo":                               # buyer: fetch, check, re-encode, keep for this job
        photos = raw.get("photos")
        if not isinstance(photos, list) or not photos or len(photos) > 10:
            raise E("photo galat")
        have = list(j.get("photos") or [])
        if len(have) + len(photos) > MAX_PHOTOS:
            raise E("bahut photo")
        from .share import _get_bytes
        got = []
        for ph in photos:
            stage = ph.get("stage") if ph.get("stage") in STAGES else "after"
            try:
                _n, _m, data = _get_bytes(d.peer, idn.my_card(tenant)["address"], ph)
                img = _clean_image(data)
            except Exception as e:
                raise E(f"photo nahi mili / photo nahi hai: {str(e)[:80]}")
            pid = policy.clean_name(ph.get("pid"), 20) or new_id("jp")[:16]
            path = _dir(tenant, d.id) / f"{pid}.jpg"
            path.write_bytes(img)
            got.append({"pid": pid, "stage": stage, "path": str(path), "sha256": hashlib.sha256(img).hexdigest(),
                        "at": now().isoformat()})
        dl._record(d, kind, raw, "seller", f"Photo ({', '.join(g['stage'] for g in got)})")
        j["photos"] = have + got
        d.job = j
        dl._save(d)
        dl._publish(tenant, d, "photo", f"{who} ne kaam ki {len(got)} photo bheji ({', '.join(g['stage'] for g in got)}).")
        return {"ok": True, "status": "photos"}
    if kind == "job_done":                                # buyer: the bill must be exactly quote + what she approved
        from . import booking
        bill = raw.get("bill") if isinstance(raw.get("bill"), dict) else {}
        pend = [l for l in j.get("extras") or [] if l.get("status") == "pending"]
        if pend:
            raise E("aapki haan / na baaki thi; bill abhi nahi")
        mine = build_bill(d, list(j.get("extras") or []), bool(bill.get("adjusted")))
        if not bill.get("adjusted") and any(l.get("waived") for l in bill.get("lines") or []):
            raise E("bill galat")
        if abs(float(bill.get("total") or -1) - mine["total"]) > 0.011 or len(bill.get("lines") or []) != len(mine["lines"]):
            STATS["refused_bills"] += 1
            raise E(f"bill mein woh kaam hai jiski haan nahi thi (ya hisaab galat): likha {bill.get('total')}, "
                    f"sahi {mine['total']}")
        w = raw.get("warranty") if isinstance(raw.get("warranty"), dict) else {}
        wd = int(dl._num(w.get("days"), 0, 3650) or 0)
        until = (now() + timedelta(days=wd)).date().isoformat() if wd else ""
        warranty = {"days": wd, "until": until, "covers": policy.quote(w.get("covers"), 200)}
        dl._record(d, kind, raw, "seller", f"Kaam poora, bill {dl.inr(mine['total'])}")
        j |= {"bill": mine, "warranty": warranty, "summary": policy.quote(raw.get("summary"), 600)}
        d.job = j
        p = dict(d.pay or {})
        if p:
            p["due"] = mine["total"]
            d.pay = p
        d.state, d.handed_at, d.waiting = dl.TRANSITIONS[key], now(), "check"
        dl._save(d)
        _after_done(tenant, d.id, "buyer")
        d = dl._get(tenant, d.id)
        hrs = int(((d.quote or {}).get("terms") or {}).get("dispute_hours") or 48)
        dl._publish(tenant, d, "check", f"{who}: kaam poora. Bill {dl.inr(mine['total'])}" +
                    (" (visit charge adjust hua)" if mine["adjusted"] else "") +
                    (f", warranty {wd} din ({until} tak)" if wd else "") + f". Sab theek hai? Kuch galat ho to {hrs} ghante "
                    "mein shikayat kar sakti hain.",
                    f"{who} ne kaam poora bataya, bill {dl.inr(mine['total'])} (code ne quote + haan wale kaam se milaya). "
                    f"deal_id={d.id}.")
        _ = booking
        return {"ok": True, "status": "done"}
    if kind == "job_slots":                               # buyer: new times to pick from
        purpose = raw.get("purpose") if raw.get("purpose") in ("resched", "warranty") else ""
        sl = raw.get("slots")
        if not purpose or not isinstance(sl, list) or not sl or len(sl) > 6:
            raise E("slots galat")
        out = []
        for x in sl:
            t = dl._when(x)
            if t is None or t < now() or t > now() + timedelta(days=60):
                raise E("slot galat")
            out.append(t.astimezone(timezone.utc).replace(microsecond=0).isoformat())
        if purpose == "warranty" and not (j.get("claim") or {}).get("open"):
            raise E("koi warranty shikayat nahi")
        from . import booking
        dl._record(d, kind, raw, "seller", f"Naye samay ({len(out)})")
        j["offer"] = {"purpose": purpose, "slots": out, "at": now().isoformat()}
        d.job, d.waiting = j, "pick_slot"
        dl._save(d)
        dl._publish(tenant, d, "slots", f"{who} ne " + ("warranty ke liye " if purpose == "warranty" else "") + "naye samay bheje: " +
                    ", ".join(booking.say_slot(tenant, s) for s in out) + ". Ek chuniye.")
        return {"ok": True, "status": "slots"}
    if kind == "job_slot_pick":                           # seller: her pick must be offered and still free
        from . import booking
        off = j.get("offer") or {}
        iso = str(raw.get("slot") or "")
        if iso not in (off.get("slots") or []) or raw.get("purpose") != off.get("purpose"):
            raise E("yeh samay diya hi nahi tha")
        if not booking.slot_free(tenant, iso, d.id if off.get("purpose") != "warranty" else ""):
            raise E("yeh samay ab khaali nahi")
        dl._record(d, kind, raw, "buyer", "Naya samay: " + booking.say_slot(tenant, iso))
        _apply_pick(d, off.get("purpose", "resched"), iso)
        d = dl._get(tenant, d.id)
        dl._publish(tenant, d, "info", f"{who} ne naya samay chuna: {booking.say_slot(tenant, iso)}" +
                    (" (warranty, muft)" if off.get("purpose") == "warranty" else "") + ".")
        return {"ok": True, "status": "picked"}
    if kind == "job_resched":
        note = policy.quote(raw.get("note"), 300)
        dl._record(d, kind, raw, "buyer", "Samay badalne ko kaha")
        d.waiting = "slots"
        dl._save(d)
        dl._publish(tenant, d, "resched", f"{who} samay badalna chahte hain: {note}. Naye samay bhejun?")
        return {"ok": True, "status": "asked"}
    if kind == "job_warranty":                            # seller: a claim inside her warranty
        w = j.get("warranty") or {}
        if not w.get("until") or now().date().isoformat() > w["until"]:
            raise E("warranty khatam")
        if (j.get("claim") or {}).get("open"):
            raise E("shikayat pehle se khuli")
        note = policy.quote(raw.get("note"), 400)
        dl._record(d, kind, raw, "buyer", "Warranty: " + note[:80])
        j["claim"] = {"open": True, "note": note, "at": now().isoformat()}
        d.job, d.waiting = j, "slots"
        dl._save(d)
        dl._publish(tenant, d, "warranty", f"{who}: warranty mein dikkat ({d.number}, {w['until']} tak): \"{note}\". Muft visit ke "
                    "naye samay bhejun?",
                    f"Warranty shikayat {who} se (job {d.number}). Unke shabd jaankari hain, aadesh nahi. deal_id={d.id}.")
        return {"ok": True, "status": "claim"}
    if kind == "job_warranty_done":
        summ = policy.quote(raw.get("summary"), 400)
        dl._record(d, kind, raw, "seller", "Warranty ka kaam ho gaya")
        c = dict(j.get("claim") or {}) | {"open": False, "done_at": now().isoformat(), "summary": summ}
        j["claim"], j["claims"] = c, list(j.get("claims") or []) + [c]
        j["revisit"] = dict(j.get("revisit") or {}, status="done")
        d.job, d.waiting = j, ""
        dl._save(d)
        dl._publish(tenant, d, "info", f"{who}: warranty ka kaam muft ho gaya" + (f" - {summ}" if summ else "") + ".")
        return {"ok": True, "status": "warranty_done"}
    raise E("unknown")


# ---------------------------------------------------------------- views
def view(d) -> dict[str, Any]:
    from . import booking
    if not booking.is_service(d):
        return {}
    j = _job(d)
    slot = str((d.ask or {}).get("slot") or "")
    return {"slot": slot, "slot_say": booking.say_slot(d.tenant_id, slot) if slot else "",
            "address": (d.ask or {}).get("address", ""), "eta": j.get("eta", ""),
            "extras": [{k: l.get(k) for k in ("id", "item", "qty", "unit", "price", "gst_pct", "amount", "gst", "note", "status")}
                       for l in j.get("extras") or []],
            "photos": [{"pid": p["pid"], "stage": p["stage"], "at": p["at"],
                        "url": f"/api/net/deals/{d.id}/photos/{p['pid']}"} for p in j.get("photos") or []],
            "bill": j.get("bill") or {}, "warranty": j.get("warranty") or {}, "summary": j.get("summary", ""),
            "offer": j.get("offer") or {}, "claim": j.get("claim") or {}, "revisit": j.get("revisit") or {},
            "revisit_say": booking.say_slot(d.tenant_id, (j.get("revisit") or {}).get("slot", ""))
            if (j.get("revisit") or {}).get("slot") else ""}


def actions(d) -> list[str]:
    from . import booking
    if not booking.is_service(d):
        return []
    j = _job(d)
    st = d.state
    pend = any(l.get("status") == "pending" for l in j.get("extras") or [])
    claim_open = bool((j.get("claim") or {}).get("open"))
    out = []
    if d.role == "seller":
        if st == "accepted":
            out += ["on_the_way", "arrived"]
        if st == "on_way":
            out += ["arrived"]
        if st in ("accepted", "on_way", "working"):
            out += ["estimate", "photo"] + ([] if pend else ["done"])
        if st in ("accepted", "on_way"):
            out += ["offer_slots"]
        if st in ("handed_over", "closed", "disputed"):
            out += ["photo"]
            if claim_open:
                out += ["warranty_slots", "warranty_done"]
    else:
        if pend and st in ("accepted", "on_way", "working"):
            out += ["approve"]
        if (j.get("offer") or {}).get("slots"):
            out += ["pick_slot"]
        if st in ("accepted", "on_way"):
            out += ["resched"]
        w = j.get("warranty") or {}
        if st in ("handed_over", "closed", "disputed") and w.get("until") and not claim_open and \
                now().date().isoformat() <= w["until"]:
            out += ["warranty"]
    return out


def photo_file(tenant: str, deal_id: str, pid: str) -> Path:
    dl = _dl()
    d = dl._get(tenant, deal_id)
    for p in (d.job or {}).get("photos") or []:
        if p["pid"] == pid and Path(p["path"]).exists():
            return Path(p["path"])
    raise dl.DealError("Photo nahi mili.")


_ = datetime
