"""v0.113 Services and bookings on the deal engine: slots as quotes, job card, proof photos, bill by code, warranty.

Meghana ("default") books; Kunal ("kunal") is the plumber (and later a clinic)."""
import asyncio
import io
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.agent.tools import Ctx, ToolError, dispatch
from tests.test_net import _connect, ev


def _last(tenant, kind="hoola_deal"):
    return ev(tenant, kind)[-1]


def _plumber(**kw):
    net = _connect()
    from app.net import booking as bk, deal as dl
    bk.set_rules("kunal", days="daily", open_at="00:00", close_at="23:59", slot_minutes=60, lead_minutes=30, horizon_days=3,
                 visit_fee=200, visit_adjust=True, warranty_days=30, **kw)
    dl.set_stock("kunal", [{"name": "Tap repair", "price": 400, "gst_pct": 18, "kind": "service", "warranty_days": 30,
                            "aliases": ["tap leaking", "nal"]}])
    return net, dl, bk


def _photo_bytes():
    from PIL import Image
    img = Image.new("RGB", (64, 48), (200, 30, 30))
    out = io.BytesIO()
    exif = img.getexif()
    exif[0x010F] = "SecretCam"                      # Make
    img.save(out, "JPEG", exif=exif)
    return out.getvalue()


def _book(dl, what="Tap leaking at base", items=None):
    out = dl.ask("default", "@kunal.raj", items or [{"item": "tap leaking", "qty": 1}], note="", area="Kothrud",
                 service={"what": what, "when": "kal subah", "area": "Kothrud"})
    return out["deal"]["id"], _last("kunal")["id"]


def test_booking_slots_address_job_card_bill_and_receipt(env):
    net, dl, bk = _plumber()
    from app.net import dealpay as dp, job as jb
    bid, sid = _book(dl)
    c = _last("kunal")
    assert c["card"] == "quote" and "Khaali samay" in c["say"] and c["draft"]["slots"]
    assert c["draft"]["lines"][0]["item"] == "Visit charge" and c["draft"]["lines"][1]["item"] == "Tap repair"
    assert "address" not in dl._get("kunal", sid).ask                    # only the work, area and time went
    dl.send_quote("kunal", sid, estimate={"min": 400, "max": 900})
    q = dl.show("default", bid)["quote"]
    assert q["service"]["at"] == "their_place" and len(q["slots"]) >= 2 and q["estimate"] == {"min": 400, "max": 900}
    slot = q["slots"][1]
    with pytest.raises(dl.DealError, match="samay chuniye"):
        dl.confirm("default", bid, by_tap=True, slot="2020-01-01T10:00:00+00:00")
    with pytest.raises(dl.DealError, match="pata"):
        dl.confirm("default", bid, by_tap=True, slot=slot)
    from app import main
    with TestClient(main.app) as cl:
        r = cl.post(f"/api/net/deals/{bid}/confirm", json={"v": q["v"], "slot": slot, "address": "Flat 4, Shanti Apts, Kothrud"})
        assert r.status_code == 200, r.text
    s = dl._get("kunal", sid)
    assert s.ask["slot"] == slot and s.ask["address"].startswith("Flat 4")
    a = dl.accept("kunal", sid)
    assert a["number"] == "J-1001" and a["pick_list"] == []
    assert _last("default")["card"] == "booked" and "J-1001" in _last("default")["say"]
    assert slot not in bk.free_slots("kunal")                           # the slot is held now
    # on the way -> arrived -> extra work found -> HER yes / no per line (the model can't)
    jb.on_the_way("kunal", sid, 30)
    assert dl.show("default", bid)["state"] == "on_way" and "raste" in _last("default")["say"]
    jb.arrived("kunal", sid)
    assert dl.show("default", bid)["state"] == "working"
    jb.estimate("kunal", sid, [{"item": "Cartridge", "price": 350, "gst_pct": 18, "note": "andar ka purana kharab"},
                               {"item": "Naya nal", "price": 1200, "gst_pct": 18}])
    e = _last("default")
    assert e["card"] == "estimate" and "Haan / Na" in e["say"]
    with pytest.raises(dl.DealError, match="baaki"):
        jb.done("kunal", sid, "Ho gaya")
    r = asyncio.run(dispatch("hoola_booking", {"action": "approve", "deal_id": bid}, Ctx("default", net.home_conv("default"))))
    assert r["status"] == "needs_tap"
    with pytest.raises(dl.DealError, match="tap"):
        jb.approve("default", bid, ["x1"], ["x2"])
    with TestClient(main.app) as cl:
        r = cl.post(f"/api/net/deals/{bid}/approve", json={"ids_yes": ["x1"], "ids_no": ["x2"]})
        assert r.status_code == 200, r.text
    assert [x["status"] for x in dl.show("kunal", sid)["job"]["extras"]] == ["yes", "no"]
    # proof photo: kept on both sides, a real picture, no EXIF
    jb.add_photo("kunal", sid, _photo_bytes(), "after.jpg", "after")
    with pytest.raises(dl.DealError, match="photo nahi"):
        jb.add_photo("kunal", sid, b"%PDF-1.4 not a photo", "x.jpg", "after")
    ph = dl.show("default", bid)["job"]["photos"]
    assert len(ph) == 1 and ph[0]["stage"] == "after"
    from PIL import Image
    img = Image.open(jb.photo_file("default", bid, ph[0]["pid"]))
    assert not img.getexif()                                            # camera / location data dropped
    with TestClient(main.app) as cl:
        assert cl.get(ph[0]["url"]).status_code == 200
    # a bill with work she said NO to is refused by her Hoola
    s = dl._get("kunal", sid)
    forged = jb.build_bill(s, [dict(x, status="yes") for x in s.job["extras"]], True)
    r = net._post("kunal", s.peer, "job_done", {"summary": "x", "bill": forged, "warranty": {"days": 30},
                                                "step": s.step + 1, "prev": s.last_hash}, s.dkey, s.thread_id)
    assert r["ok"] is False and "haan nahi" in r["reason"]
    # the real bill: quote + approved line, visit charge adjusted (work was done)
    out = jb.done("kunal", sid, "Cartridge badla, leak band", 30, "nal ki fitting")
    b = out["bill"]
    assert b["adjusted"] and b["total"] == round(400 * 1.18 + 350 * 1.18, 2)
    v = dl.show("default", bid)
    assert v["state"] == "handed_over" and v["job"]["bill"]["total"] == b["total"] and v["job"]["warranty"]["days"] == 30
    assert _last("default")["card"] == "check" and "warranty 30 din" in _last("default")["say"]
    assert v["pay"]["due_left"] == b["total"]
    dp.received("kunal", sid, mode="cash")
    dp.all_ok("default", bid)
    assert dl.show("default", bid)["state"] == "closed" and dl._get("default", bid).last_hash == dl._get("kunal", sid).last_hash


def test_warranty_claim_revisit_and_expiry(env):
    net, dl, bk = _plumber()
    from app.net import dealpay as dp, job as jb
    bid, sid = _book(dl)
    dl.send_quote("kunal", sid)
    q = dl.show("default", bid)["quote"]
    dl.confirm("default", bid, by_tap=True, slot=q["slots"][0], address="Ghar 12")
    dl.accept("kunal", sid)
    jb.arrived("kunal", sid)
    jb.done("kunal", sid, "Tap theek", 15)
    dp.received("kunal", sid, mode="upi")
    dp.all_ok("default", bid)
    # inside the warranty: claim -> free revisit slots -> her tap -> done
    jb.claim("default", bid, "Phir se tapak raha hai")
    assert _last("kunal")["card"] == "warranty" and "warranty_slots" in dl.show("kunal", sid)["actions"]
    with pytest.raises(dl.DealError, match="pehle se"):
        jb.claim("default", bid, "phir")
    jb.offer_slots("kunal", sid, "warranty")
    off = dl.show("default", bid)["job"]["offer"]
    assert off["purpose"] == "warranty" and "pick_slot" in dl.show("default", bid)["actions"]
    with pytest.raises(dl.DealError, match="tap"):
        jb.pick_slot("default", bid, off["slots"][0])
    jb.pick_slot("default", bid, off["slots"][0], by_tap=True)
    rv = dl.show("kunal", sid)["job"]["revisit"]
    assert rv["status"] == "booked" and off["slots"][0] not in bk.free_slots("kunal")
    jb.warranty_done("kunal", sid, "Washer badla")
    assert not dl.show("default", bid)["job"]["claim"]["open"] and "muft" in _last("default")["say"]
    # after the warranty ends: no claim
    d = dl._get("default", bid)
    d.job = dict(d.job, warranty=dict(d.job["warranty"], until=(dl.now() - timedelta(days=1)).date().isoformat()))
    dl._save(d)
    with pytest.raises(dl.DealError, match="khatam"):
        jb.claim("default", bid, "phir dikkat")


def test_slots_are_held_reschedule_and_reminders(env):
    net, dl, bk = _plumber()
    from app.net import job as jb
    b1, s1 = _book(dl)
    dl.send_quote("kunal", s1)
    b2, s2 = _book(dl, "Doosra nal")
    dl.send_quote("kunal", s2)
    q1, q2 = dl.show("default", b1)["quote"], dl.show("default", b2)["quote"]
    same = [x for x in q1["slots"] if x in q2["slots"]][0]
    dl.confirm("default", b1, by_tap=True, slot=same, address="A")
    with pytest.raises(dl.DealError, match="khaali nahi"):              # one job per slot (her capacity 1)
        dl.confirm("default", b2, by_tap=True, slot=same, address="A")
    dl.accept("kunal", s1)
    # reschedule: she asks, he offers new times, her tap moves it (both sides)
    jb.ask_resched("default", b1, "Shaam ko aa sakte ho?")
    assert _last("kunal")["card"] == "resched"
    jb.offer_slots("kunal", s1)
    new = dl.show("default", b1)["job"]["offer"]["slots"][-1]
    jb.pick_slot("default", b1, new, by_tap=True)
    assert dl._get("kunal", s1).ask["slot"] == new == dl._get("default", b1).ask["slot"]
    assert same in bk.free_slots("kunal", n=50)                         # the old one is free again
    # reminders: a day before (customer) and the morning of the job (worker), once each
    for t, i in (("default", b1), ("kunal", s1)):
        d = dl._get(t, i)
        d.ask = dict(d.ask, slot=(dl.now() + timedelta(hours=5)).replace(microsecond=0).isoformat())
        dl._save(d)
    bk.tick()
    assert "Kal / aaj" in _last("default")["say"] and "Aaj ka kaam J-" in _last("kunal")["say"]
    n = len(ev("default", "hoola_deal"))
    bk.tick()
    assert len(ev("default", "hoola_deal")) == n


def test_clinic_appointment_at_my_place_no_address(env):
    net, dl, bk = _plumber(at="my_place", prefix="T")
    bk.set_rules("kunal", visit_fee=400, visit_adjust=False)
    dl.set_rules("kunal", auto_quote="connected")
    bid = dl.ask("default", "@kunal.raj", [], area="", service={"what": "Dr Patil, bukhar 3 din", "when": "Saturday shaam"})["deal"]["id"]
    q = dl.show("default", bid)
    assert q["state"] == "quoted" and q["quote"]["service"]["at"] == "my_place"         # her rule: quote by itself
    assert q["quote"]["lines"][0]["item"] == "Visit charge" and q["quote"]["lines"][0]["price"] == 400
    assert len(q["quote"]["lines"]) == 1                                  # the fee is the quote; her words stay the 'what'
    sid = _last("kunal")["id"]
    dl.confirm("default", bid, by_tap=True, slot=q["quote"]["slots"][0])  # no address for 'at my place'
    a = dl.accept("kunal", sid)
    assert a["number"].startswith("T-") and "address" not in dl._get("kunal", sid).ask


def test_tools_rate_card_hours_and_limits(env):
    net, dl, bk = _plumber()
    ctx = Ctx("kunal", net.home_conv("kunal"))
    r = asyncio.run(dispatch("hoola_booking", {"action": "services", "op": "set",
                                               "items": [{"name": "AC service", "price": 600, "gst_pct": 18}]}, ctx))
    names = [x["name"] for x in asyncio.run(dispatch("hoola_booking", {"action": "services"}, ctx))["services"]]
    assert "AC service" in names and "Tap repair" in names
    asyncio.run(dispatch("hoola_booking", {"action": "hours", "op": "set", "settings": {"slot_minutes": 90, "capacity": 2}}, ctx))
    assert bk.rules_view("kunal")["slot_minutes"] == 90 and bk.rules_view("kunal")["capacity"] == 2
    assert asyncio.run(dispatch("hoola_booking", {"action": "free_slots"}, ctx))["slots"]
    with pytest.raises(ToolError, match="owner"):
        asyncio.run(dispatch("hoola_booking", {"action": "hours", "op": "set", "settings": {"capacity": 9}},
                             Ctx("kunal", net.home_conv("kunal"), actor="peer:x")))
    with pytest.raises(dl.DealError):
        bk.set_rules("kunal", open_at="20:00", close_at="09:00")
    out = asyncio.run(dispatch("hoola_booking", {"action": "book", "to": "@kunal.raj", "what": "AC service, thanda nahi",
                                                 "area": "Baner"}, Ctx("default", net.home_conv("default"))))
    assert out["deal"]["service"] and "pata bhi tabhi" in out["say"]
    from app import main
    with TestClient(main.app) as cl:
        assert cl.get("/api/net/bookings").json()["bookings"]
        assert cl.get("/api/net/service_rules").status_code == 200
    _ = r
