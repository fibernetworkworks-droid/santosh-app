"""v0.999.20 ONE SHOP step 2 (gap 9 of docs/research/lovable/03_backend_vs_hoola.md, owner: "GO STEP 2"): every website
order is a row of the app's Orders list.

Before: a website order lived only in `site_shop_orders`; the staff phone app, her app's Orders list, live updates,
logic / connectors on order status and the app dashboard never saw it. Now, for a site joined to its App Sahayak project
(step 1, `shopjoin`):
- the project gets an Orders list if it has none (staff-only rules: a website member can never write an order row - the
  website's checkout is the only way in, with the server's prices);
- every website order gets ONE row there, made when the order is saved (`mirror`), with its items, total, customer,
  address, payment way, paid state and status in the app's words; the row is a guest row (no app member owns it), so
  only her staff and she read it;
- the two stay in step BOTH ways, through one table of words (WEB_TO_APP / APP_TO_WEB):
  website -> app: every website move (her console, the gateway's verified payment, the customer's "I have paid", an
  unpaid online order released) rewrites the row's status / paid / UTR (`mirror`);
  app -> website: a staff move on the row (her app, staff phone app, Hoola, a workflow) moves the website order through
  its own rules (`from_app`): a cancel there is a website cancel, so stock / coupon / credit note come back ONCE, by the
  website's own code; a move the website cannot make is said and the row is put back to the website's state;
- the website keeps its own record of the order beside the row (the customer's private link, payment, invoice, courier):
  step 3 moves the old orders over.
A site with no project: nothing changes."""
from __future__ import annotations

import json
import logging
import threading
from typing import Any

from ..db import now, session

log = logging.getLogger("santosh.site")

WEB_TO_APP = {"new": "New", "payment_told": "New", "confirmed": "Accepted", "packed": "Packed", "shipped": "Out for delivery",
              "delivered": "Delivered", "cancelled": "Cancelled"}
APP_TO_WEB = {"Accepted": "confirmed", "Packed": "packed", "Out for delivery": "shipped", "Delivered": "delivered",
              "Cancelled": "cancelled"}
PATH = ["new", "confirmed", "packed", "shipped", "delivered"]          # the website's forward road (payment_told = new)
COLL = "orders"
_NOW = threading.local()                                               # a move that came from the other side


def _j(s: Any, d: Any) -> Any:
    try:
        return json.loads(s) if s else d
    except (TypeError, ValueError):
        return d


def _syncing() -> bool:
    return bool(getattr(_NOW, "on", False))


def ensure_list(p) -> None:
    """The project's Orders list (made once, staff-only) - the place website orders appear."""
    from ..appmaker import backend as BE
    if any(c.get("key") == COLL for c in BE.schema(p).get("collections") or []):
        return
    lst = BE._orders()
    lst["rules"] = dict(BE.STAFF_RULES)                 # only the website's checkout writes these rows
    lst["fields"] = [f for f in lst["fields"] if f.get("type") != "location"]
    BE.change_schema(p, {"add_list": [lst]}, "website shop: orders")


def _data(o) -> dict[str, Any]:
    from . import shop as SH
    items = _j(o.items, [])
    pay = {"cod": "Cash on delivery", "upi": "UPI", "online": "UPI"}.get(o.method, "UPI")
    paid = "Verified" if o.status in ("confirmed", "packed", "shipped", "delivered") and o.method != "cod" else \
        ("Customer says paid" if o.status == "payment_told" else "No")
    note = (o.note or "").strip()
    extra = [f"Website order {o.number}", "paid online" if o.method == "online" else ""]
    if o.discount:
        extra.append(f"coupon {o.coupon or ''} -{SH.rupees(o.discount)}".strip())
    if o.delivery:
        extra.append(f"delivery {SH.rupees(o.delivery)}")
    return {"items": "\n".join(f"{int(i['qty'])} x {i['title']}" + (f" ({i['unit']})" if i.get("unit") else "")
                               + f" @ Rs {i['price'] / 100:g}" for i in items),
            "total": round(o.total / 100, 2), "name": o.name, "phone": o.phone,
            "address": f"{o.address} {o.pincode}".strip(), "note": " · ".join(x for x in [note, *extra] if x)[:900],
            "pay": pay, "paid": paid, "utr": o.utr or "", "status": WEB_TO_APP.get(o.status, "New"),
            "_web_order": o.number, "_web_id": o.id, "_site": o.site_id, "_from": "website"}


def mirror(site_id: str, order_id: str) -> str:
    """The order's row in the app's Orders list, made once and then kept equal to the website order. Returns the row id
    ('' = the site has no project / the row could not be written - the website order itself is never affected)."""
    from ..appmaker import backend as BE
    from . import shop as SH
    from . import shopjoin as SJ
    from . import webapp as W
    p = SJ.project_of(site_id)
    if p is None:
        return ""
    try:
        SH.ensure_tables()
        ensure_list(p)
        with session() as s:
            o = s.get(SH.SiteShopOrder, order_id)
            if o is None:
                return ""
            d = _data(o)
            row = s.get(W.SiteAppRow, o.app_row) if getattr(o, "app_row", None) else None
            if row is None:
                row = W.SiteAppRow(site_id=BE.bid(p), coll=COLL, owner="", data=json.dumps(d, ensure_ascii=False))
                s.add(row)
                s.flush()
                o.app_row = row.id
            else:
                old = _j(row.data, {})
                if all(old.get(k) == v for k, v in d.items()):
                    return row.id
                row.data = json.dumps({**old, **d, "_ev": now().isoformat()}, ensure_ascii=False)
            return row.id
    except Exception:                                   # noqa: BLE001 - the app's copy never breaks a website order
        log.exception("website order row site=%s order=%s", site_id, order_id)
        return ""


def from_app(p, row_id: str, out: dict[str, Any]) -> None:
    """A staff / owner move of a website order's row in the app -> the same move on the website order, by the website's
    own rules (a cancel returns stock, coupon and the credit note there, once)."""
    if _syncing():
        return
    from . import shop as SH
    from . import webapp as W
    with session() as s:
        row = s.get(W.SiteAppRow, row_id)
        d = _j(row.data if row is not None else "", {})
    if d.get("_from") != "website" or not d.get("_web_order"):
        return
    site_id, number = str(d.get("_site") or ""), str(d["_web_order"])
    want = APP_TO_WEB.get(str(out.get("status") or d.get("status") or ""))
    paid = str(out.get("paid") or d.get("paid") or "")
    with session() as s:
        o = s.query(SH.SiteShopOrder).filter_by(site_id=site_id, number=number).first()
        cur, oid = (o.status, o.id) if o is not None else ("", "")
    if not oid:
        return
    if want is None and paid == "Verified" and cur in ("new", "payment_told"):
        want = "confirmed"                              # she / her staff saw the money in the app
    _NOW.on = True
    try:
        steps = _road(cur, want) if want else []
        for to in steps:
            SH.set_status(site_id, number, to, by="app")
    except SH.ShopError as e:
        log.info("website order %s: app move to %s refused: %s", number, want, e)
    finally:
        _NOW.on = False
    mirror(site_id, oid)                                 # the row shows what the website order really is now


def _road(cur: str, want: str) -> list[str]:
    """The website moves from `cur` to `want`: one step, or the forward road through its states."""
    from . import shop as SH
    if not want or want == cur:
        return []
    if want in SH.NEXT.get(cur, ()):
        return [want]
    start = "new" if cur == "payment_told" else cur
    if start in PATH and want in PATH and PATH.index(want) > PATH.index(start):
        return PATH[PATH.index(start) + 1:PATH.index(want) + 1]     # payment_told -> confirmed like new -> confirmed
    raise SH.ShopError(f"Website order cannot go from '{SH.WORDS.get(cur, cur)}' to '{SH.WORDS.get(want, want)}'.", 409)
