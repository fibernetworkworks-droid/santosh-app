"""A small fictional shop (Demo Bazaar) for the Order karo tests: search, product, cart, checkout by URL, payment."""
from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

STATE = {"cart": {}, "orders": [], "paid": False}
ITEMS = {"p1": ("Airdopes 141 Black", 1299, 4.2), "p2": ("Airdopes 141 Black (Sponsored)", 1899, 3.1)}


def page(title, body):
    return f"<!doctype html><html><head><title>{title}</title></head><body><h1>{title}</h1>{body}</body></html>"


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, html, code=200, loc=None):
        self.send_response(code)
        if loc:
            self.send_header("Location", loc)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def do_GET(self):
        u = urlsplit(self.path)
        q = parse_qs(u.query)
        if u.path == "/s":
            rows = "".join(f'<li><a href="/p/{k}">{n}</a> ₹{p} · rating {r}</li>' for k, (n, p, r) in ITEMS.items())
            return self._send(page("Results for " + q.get("k", [""])[0], f"<ul>{rows}</ul>"))
        if u.path.startswith("/p/"):
            k = u.path.split("/")[-1]
            n, p, r = ITEMS[k]
            return self._send(page(n, f"<p>Price ₹{p}</p><form method=post action=/add><input type=hidden name=id value={k}>"
                                      "<label>Qty <input name=qty value=1></label><button>Add to Cart</button></form>"
                                      "<form method=post action=/buynow><button>Buy Now</button></form>"))
        if u.path == "/cart":
            rows = "".join(f"<li>{ITEMS[k][0]} x {n}</li>" for k, n in STATE["cart"].items())
            total = sum(ITEMS[k][1] * n for k, n in STATE["cart"].items())
            return self._send(page("Your cart", f"<ul>{rows}</ul><p>Total ₹{total}</p>"))
        if u.path == "/checkout":
            total = sum(ITEMS[k][1] * n for k, n in STATE["cart"].items())
            return self._send(page("Checkout", "<form method=post action=/place><fieldset><legend>Delivery address</legend>"
                                   "<label><input type=radio name=addr value=home> Ghar - Akot</label>"
                                   "<label><input type=radio name=addr value=office> Office - Akola</label></fieldset>"
                                   f"<p>Order total ₹{total}</p><button>Place your order</button></form>"))
        if u.path == "/done":
            o = STATE["orders"][-1]
            return self._send(page("Order placed", f"<p>Thank you! Order ID {o['id']} arriving Friday to {o['addr']}.</p>"))
        return self._send(page("Demo Bazaar", '<a href="/s?k=">Shop</a>'))

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        f = {k: v[0] for k, v in parse_qs(self.rfile.read(n).decode()).items()}
        if self.path == "/add":
            STATE["cart"][f["id"]] = STATE["cart"].get(f["id"], 0) + int(f.get("qty") or 1)
            return self._send("", 303, "/cart")
        if self.path == "/buynow":
            return self._send("", 303, "/checkout")
        if self.path == "/place":
            oid = f"DB-{4021 + len(STATE['orders'])}-778899"
            STATE["orders"].append({"id": oid, "addr": f.get("addr", ""), "cart": dict(STATE["cart"])})
            STATE["cart"].clear()
            return self._send("", 303, "/done")
        return self._send("", 404)


def serve(port: int = 0):
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
