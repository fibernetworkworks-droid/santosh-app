"""v0.80 Order karo: shopping / grocery / food / travel orders end to end up to the payment, which she makes herself."""
import asyncio
import json

import pytest
from fastapi.testclient import TestClient

T = "default"


@pytest.fixture
def shop(env):
    from app.shop import service
    yield service


def test_plan_routes(shop, monkeypatch):
    p = shop.plan(T, "Blinkit se 2 litre doodh aur bread")
    assert p["site"] == "blinkit" and p["route"] == "operator" and p["named"]
    assert shop.plan(T, "chicken biryani mangwa do")["kind"] == "food"
    assert shop.plan(T, "ek achha mixer grinder 3000 tak")["site"] == "amazon"
    p = shop.plan(T, "redmi charger", "flipkart", compare=["amazon", "nope"])
    assert p["site"] == "flipkart" and p["compare"] == ["amazon"]
    # her linked official Swiggy MCP wins over the browser
    from app.agent import mcp_live
    monkeypatch.setattr(mcp_live, "snapshot", lambda t: [{"pack_id": "swiggy-food", "status": "ready", "tools": [{"name": "x"}]}])
    p = shop.plan(T, "Swiggy se paneer tikka")
    assert p["route"] == "mcp" and p["mcp_pack"] == "swiggy-food"
    v = shop.order(T, "Swiggy se paneer tikka 2 plate")
    assert v["route"] == "mcp" and "place-order tool" in v["next"] and "Never pick a payment method" in v["next"]


def test_operator_job_and_order_tracking(shop):
    from app.db import session
    from app.operator.models import OperatorTask
    from app.operator import service as ops
    v = shop.order(T, "Amazon se boAt Airdopes 141 black, 1 piece", budget="1500", address="ghar", compare=["flipkart"])
    assert v["route"] == "operator" and v["status"] == "working" and "pay aap khud" in v["say"]
    with session() as s:
        row = s.get(OperatorTask, v["task_id"])
        assert row.task.startswith("Order on Amazon:") and "Budget: 1500" in row.task and "ghar" in row.task
        assert "Flipkart" in row.task                                   # compare first
        assert row.start_url == "https://www.amazon.in/s?k=boat+airdopes+141+black"
        assert "ask_owner(kind='payment'" in row.guide and "Add to Cart' (not 'Buy Now')" in row.guide
        assert "insurance" in row.guide and "Never type card numbers" in row.guide
        assert "ORDER RULES" not in row.task                            # her card shows her words, not the rulebook
    # only one browser job at a time: a second order is refused plainly
    with pytest.raises(shop.ShopError):
        shop.order(T, "Blinkit se doodh")
    # the job reaches the payment page: waiting for her
    with session() as s:
        row = s.get(OperatorTask, v["task_id"])
        row.status = "waiting"
        row.pending = json.dumps({"kind": "payment", "reason": "Amazon: boAt Airdopes 141 x1 = Rs 1,299, delivery Fri, ghar"})
    o = shop.orders(T)[0]
    assert o["status"] == "waiting_payment" and o["total"] == "₹1,299" and "Airdopes" in o["summary"]
    # she paid; the job read the confirmation
    with session() as s:
        row = s.get(OperatorTask, v["task_id"])
        row.status, row.pending = "done", ""
        row.summary = "Order placed. Order ID 403-1234567-7654321, arriving Friday."
        row.proof = json.dumps(["Order # 403-1234567-7654321"])
    o = shop.orders(T)[0]
    assert o["status"] == "placed" and o["order_ref"] == "403-1234567-7654321"
    assert ops.active(T) is None


def test_payment_buttons_stay_hers_cart_buttons_dont():
    from app.operator import guard
    def node(text, tag="button"):
        return {"tag": tag, "text": text, "attributes": {}}
    for pay in ("Place your order", "Proceed to Pay", "Pay Now", "Buy Now", "Place Order", "Pay ₹1,299"):
        assert guard.classify_click(node(pay)) == "payment", pay
    for ok in ("Add to Cart", "ADD", "Add to bag", "Continue", "Deliver to this address"):
        assert guard.classify_click(node(ok)) == "ok", ok


def test_swiggy_tool_tiers_and_wiring(shop):
    from app.bazar.packs.registry import load_manifests
    packs = {p.id: p for p in load_manifests()}
    food = packs["swiggy-food"]
    assert food.tier_of("update_food_cart") == 0 and food.tier_of("search_restaurants") == 0
    assert food.tier_of("check_payment_status") == 0 and food.tier_of("get_payment_options") == 0
    assert food.tier_of("place_food_order") == 2 and food.tier_of("confirm_order") == 2
    from app.bazar.config import get_settings as bazar_settings
    assert bazar_settings().mcp_swiggy_instamart_url.endswith("/im")
    from app.agent.tools import HANDLERS, TOOLS, Ctx
    from app.voice import VOICE_TOOL_NAMES
    assert any(t["name"] == "order_karo" for t in TOOLS) and "order_karo" in VOICE_TOOL_NAMES
    r = asyncio.run(HANDLERS["order_karo"](Ctx(tenant_id=T, conversation_id="c"), action="sites"))
    assert {"amazon", "flipkart", "blinkit", "zepto", "swiggy", "zomato", "irctc"} <= {x["id"] for x in r["sites"]}
    from app.main import app
    c = TestClient(app)
    assert c.post("/api/shop/orders", json={"what": "x"}).status_code == 400
    v = c.post("/api/shop/orders", json={"what": "Zepto se 6 ande", "site": "zepto"}).json()
    assert v["site"] == "zepto" and c.get("/api/shop/orders").json()["orders"][0]["id"] == v["id"]


# ---------------------------------------------------------------- real browser, fictional shop
try:
    import playwright  # noqa: F401
    HAVE_PW = True
except ImportError:
    HAVE_PW = False


@pytest.mark.skipif(not HAVE_PW, reason="needs playwright")
def test_end_to_end_order_she_only_pays(env, monkeypatch):
    import re
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    import shop_site
    from test_v067_operator import call, ref
    monkeypatch.setenv("OPERATOR_ALLOW_PRIVATE", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.operator import service as ops
    from app.shop import service as shop, sites
    srv = shop_site.serve(0)
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    monkeypatch.setitem(sites.SITES, "demobazaar", {"name": "Demo Bazaar", "kind": "shopping", "web": base,
                                                    "search": base + "/s?k={q}", "words": ["demo bazaar"],
                                                    "play": "Add to Cart, then open /cart and /checkout by URL."})
    shop_site.STATE.update(cart={}, orders=[])
    v = shop.order(T, "Demo Bazaar se Airdopes 141 black, 1", address="ghar")
    assert v["route"] == "operator"

    async def go():
        op = await ops.operator(T)
        job = ops.Job(ops._row(v["task_id"]), op, ops.memory(T))
        ops._set(v["task_id"], status="running")
        try:
            p = (await call(job, "open", url=ops._row(v["task_id"]).start_url))["page"]
            assert "Sponsored" in p                                # it can see the sponsored result and skip it
            p = (await call(job, "click", ref=ref(p, "Airdopes 141 Black", "link")))
            p = p.get("page") or await call(job, "page")
            buy = await call(job, "click", ref=ref(p, "Buy Now", "button"))
            assert buy.get("blocked") == "payment"                 # "Buy now" looks like paying: never pressed
            r = await call(job, "click", ref=ref(p, "Add to Cart", "button"))
            assert shop_site.STATE["cart"] == {"p1": 1}
            p = (await call(job, "open", url=base + "/cart"))["page"]
            assert "Total ₹1299" in p
            p = (await call(job, "open", url=base + "/checkout"))["page"]   # checkout page by URL: nothing is paid
            await call(job, "check", ref=ref(p, "Ghar", "radio"))
            place = ref(p, "Place your order", "button")
            assert (await call(job, "click", ref=place)).get("blocked") == "payment"
            assert not shop_site.STATE["orders"]                   # nothing ordered without her
            asked = asyncio.create_task(call(job, "ask_owner", kind="payment", ref=place,
                                             reason="Demo Bazaar: Airdopes 141 Black x1 = Rs 1,299, delivery Friday, ghar"))
            for _ in range(80):
                await asyncio.sleep(0.1)
                if shop.orders(T)[0]["status"] == "waiting_payment":
                    break
            mine = shop.orders(T)[0]
            assert mine["status"] == "waiting_payment" and mine["total"] == "₹1,299"
            s = op.sessions["main"]
            pend = next(a for a in op.approvals.values() if a.status == "pending")
            box = await s.page.locator(f'[data-hoola-ref="{pend.ref}"]').bounding_box()
            await ops.owner_input(T, "click", box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)   # SHE presses
            await asyncio.sleep(0.8)
            await ops.resolve(T, pend.id, "approved", "")
            await asked
            p = await call(job, "page")
            m = re.search(r"DB-\d+-\d+", p)
            assert m and shop_site.STATE["orders"][0]["addr"] == "home"
            await call(job, "finish", summary=f"Order placed. Order ID {m.group(0)}, arriving Friday.", proof=[m.group(0)])
            await ops._wrap(job, "done", job.finished["summary"], job.finished)
        finally:
            await op.close("main")
        return m.group(0)
    oid = asyncio.run(go())
    o = shop.orders(T)[0]
    assert o["status"] == "placed" and o["order_ref"] == oid
    srv.shutdown()
    ops._ops.clear()
