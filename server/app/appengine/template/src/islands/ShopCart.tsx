"use client"; // v0.999.77 D8: the shop's cart and checkout on a React website - an island on every page when her shop is on
// Hoola App Engine - Hoola's own kit file. It talks only to HER website's shop on Hoola (the same shop, stock, prices,
// orders and payments as her HTML website): GET /products (live prices + stock), POST /order (the server prices it -
// never this page), GET /order/<number>?t=<token> (the order's status), POST /order/<number>/paid (her customer's UPI
// reference; she still checks her own account and confirms).
// Under Hoola's address a website page runs sealed (no browser storage), so the cart lives while the page is open; on
// her own address (v0.999.82) the visitor's browser keeps it. The order link (?order=...&t=...) is what the customer
// keeps to see the order again.
import * as React from "react";
import { ShoppingBag, X } from "lucide-react";
import { keepGet, keepSet } from "@/lib/keep";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

export interface ShopCartProps {
  /** her website's shop address on Hoola, e.g. /api/site-shop/<site> */
  api: string;
  cod?: boolean;
  upi?: boolean;
  pickup?: boolean;
  shopName?: string;
}

type Line = { slug: string; name: string; qty: number };
type Prod = { slug: string; title: string; price_text?: string; in_stock?: boolean };
type Order = {
  number: string; token: string; status: string; status_text?: string; total?: string; delivery?: string;
  method?: string; items?: { title: string; qty: number; amount: string }[];
  pay?: { amount?: string; vpa?: string; qr?: string; link?: string }; online?: { url?: string };
  paid_online?: boolean; discount?: string; coupon?: string; error?: string;
};

const safeHttp = (u?: string) => (u && /^https:\/\//.test(u) ? u : "");

async function call<T>(api: string, method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(api + path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  const out = await res.json().catch(() => ({}));
  if (!res.ok || out.ok === false) throw new Error(out.detail || out.error || "The shop did not answer. Please try again.");
  return out as T;
}

export default function ShopCart({ api, cod = false, upi = false, pickup = false, shopName = "" }: ShopCartProps) {
  const idBase = React.useId();
  const [lines, setLines] = React.useState<Line[]>([]);
  // v0.999.82 D8: on her own address the browser keeps the cart (a sealed page keeps nothing: memory only)
  const store = "cart:" + api;
  React.useEffect(() => {
    const v = keepGet<unknown>(store, []);
    if (Array.isArray(v))
      setLines((now) => (now.length ? now : v.filter((x) => x && typeof x.slug === "string" && Number.isFinite(x.qty) && x.qty > 0)
        .slice(0, 50).map((x) => ({ slug: String(x.slug), name: String(x.name || x.slug), qty: Math.min(Math.round(x.qty), 99) }))));
  }, [store]);
  React.useEffect(() => keepSet(store, lines), [store, lines]);
  const [open, setOpen] = React.useState(false);
  const [prods, setProds] = React.useState<Record<string, Prod>>({});
  const [online, setOnline] = React.useState(false);
  const [step, setStep] = React.useState<"cart" | "details" | "done">("cart");
  const [busy, setBusy] = React.useState(false);
  const [said, setSaid] = React.useState("");
  const [order, setOrder] = React.useState<Order | null>(null);
  const [utr, setUtr] = React.useState("");
  const [f, setF] = React.useState({ name: "", phone: "", address: "", pincode: "", note: "", method: "", pickup: false, coupon: "" });
  const [couponSay, setCouponSay] = React.useState("");
  const [track, setTrack] = React.useState("");
  const [stars, setStars] = React.useState("5");
  const [review, setReview] = React.useState("");
  const cid = React.useRef("");
  const trap = React.useRef<HTMLInputElement>(null);

  const refresh = React.useCallback(() => {
    call<{ products: Prod[]; online?: boolean }>(api, "GET", "/products")
      .then((j) => {
        const m: Record<string, Prod> = {};
        for (const p of j.products || []) m[p.slug] = p;
        setProds(m);
        setOnline(!!j.online);
      })
      .catch(() => undefined);
  }, [api]);

  React.useEffect(() => {
    const add = (e: Event) => {
      const d = (e as CustomEvent).detail || {};
      if (!d.slug) return;
      setLines((ls) => {
        const at = ls.findIndex((l) => l.slug === d.slug);
        if (at >= 0) return ls.map((l, i) => (i === at ? { ...l, qty: Math.min(99, l.qty + 1) } : l));
        return [...ls, { slug: String(d.slug), name: String(d.name || d.slug), qty: 1 }];
      });
      setStep("cart");
      setOpen(true);
    };
    window.addEventListener("hoola-cart", add);
    const w = window as unknown as { __hoolaCartReady?: boolean; __hoolaCart?: unknown[] };
    for (const detail of w.__hoolaCart || []) add(new CustomEvent("hoola-cart", { detail }));   // asked before it woke
    w.__hoolaCart = [];
    w.__hoolaCartReady = true;
    const q = new URLSearchParams(location.search);                // the order link the customer kept
    const n = q.get("order"), t = q.get("t");
    if (n && t) {
      call<Order>(api, "GET", `/order/${encodeURIComponent(n)}?t=${encodeURIComponent(t)}`)
        .then((o) => { setOrder(o); setStep("done"); setOpen(true); })
        .catch(() => undefined);
    }
    return () => {
      window.removeEventListener("hoola-cart", add);
      w.__hoolaCartReady = false;
    };
  }, [api]);

  React.useEffect(() => {
    if (open) refresh();
  }, [open, refresh]);

  const ways = [
    ...(online ? [["online", "Online payment (UPI, card, netbanking - a secure page)"]] : []),
    ...(upi ? [["upi", "UPI (GPay, PhonePe, Paytm)"]] : []),
    ...(cod ? [["cod", "Cash on delivery"]] : []),
  ] as [string, string][];
  const count = lines.reduce((a, l) => a + l.qty, 0);
  const setQty = (slug: string, q: number) =>
    setLines((ls) => (q <= 0 ? ls.filter((l) => l.slug !== slug) : ls.map((l) => (l.slug === slug ? { ...l, qty: Math.min(99, q) } : l))));
  const set = (k: keyof typeof f) => (v: string | boolean) => setF((x) => ({ ...x, [k]: v }));

  const place = async (e: React.FormEvent) => {
    e.preventDefault();
    const phone = f.phone.replace(/\D/g, "");
    if (!f.name.trim() || phone.length < 10 || (!f.pickup && !f.address.trim()) || !(f.method || ways[0]?.[0])) {
      setSaid("Please add your name, a 10-digit mobile number" + (f.pickup ? "" : " and the delivery address") + ".");
      return;
    }
    if (!cid.current) cid.current = "c" + Date.now().toString(36) + Math.random().toString(36).slice(2, 10);   // a retry = the same order
    setBusy(true);
    setSaid("");
    try {
      const o = await call<Order>(api, "POST", "/order", {
        cid: cid.current, items: lines.map((l) => ({ slug: l.slug, qty: l.qty })), name: f.name.trim(), phone: phone.slice(-10),
        address: f.pickup ? "" : f.address.trim(), pincode: f.pincode.trim(), note: f.note.trim(),
        method: f.method || ways[0][0], pickup: f.pickup, website: trap.current?.value || "", coupon: f.coupon.trim(),
      });
      setLines([]);
      cid.current = "";
      const go = safeHttp(o.online?.url);
      if (go) {
        location.href = go;                                         // her payment gateway's own page
        return;
      }
      setOrder(o);
      setStep("done");
    } catch (er) {
      setSaid((er as Error).message);
      refresh();
    }
    setBusy(false);
  };

  const paid = async () => {
    if (!order || utr.replace(/\D/g, "").length < 6) {
      setSaid("Type the UPI reference (UTR) from your UPI app.");
      return;
    }
    setBusy(true);
    try {
      const o = await call<Order>(api, "POST", `/order/${encodeURIComponent(order.number)}/paid`, { token: order.token, utr });
      setOrder({ ...order, ...o });
      setSaid("Thank you. The shop checks its account and confirms your order.");
    } catch (er) {
      setSaid((er as Error).message);
    }
    setBusy(false);
  };

  const tryCoupon = async () => {                                   // the shop applies it - this page only asks
    if (!f.coupon.trim()) { setCouponSay(""); return; }
    try {
      const j = await call<{ ok?: boolean; code?: string; discount?: string; total?: string; why?: string }>(api, "POST", "/coupon",
        { code: f.coupon.trim(), items: lines.map((l) => ({ slug: l.slug, qty: l.qty })) });
      setCouponSay(j.ok ? `${j.code}: ${j.discount} off (items ${j.total})` : j.why || "That code does not apply.");
    } catch (er) {
      setCouponSay((er as Error).message);
    }
  };

  React.useEffect(() => {                                           // the courier's word, once it is on its way
    if (!order || !["shipped", "delivered"].includes(order.status)) return;
    call<{ awb?: string; status?: string }>(api, "GET", `/order/${encodeURIComponent(order.number)}/track?t=${encodeURIComponent(order.token)}`)
      .then((j) => j.awb && setTrack(`Courier AWB ${j.awb}${j.status ? `: ${j.status}` : ""}`))
      .catch(() => undefined);
  }, [api, order]);

  const sendReview = async () => {
    if (!order) return;
    const slug = (order.items as unknown as { slug?: string }[] | undefined)?.[0]?.slug || "";
    try {
      await call(api, "POST", `/order/${encodeURIComponent(order.number)}/review`, { token: order.token, slug, stars: Number(stars), text: review });
      setSaid("Thank you for the review.");
      setReview("");
    } catch (er) {
      setSaid((er as Error).message);
    }
  };

  const link = order && typeof location !== "undefined"
    ? `${location.origin}${location.pathname}?order=${encodeURIComponent(order.number)}&t=${encodeURIComponent(order.token)}` : "";

  if (!count && !open) return null;
  return (
    <>
      {!open ? (
        <Button
          type="button"
          size="lg"
          onClick={() => setOpen(true)}
          className="fixed bottom-5 right-5 z-40 shadow-card"
          aria-label={`Open the cart, ${count} item${count === 1 ? "" : "s"}`}
        >
          <ShoppingBag className="size-5" aria-hidden="true" />
          Cart · {count}
        </Button>
      ) : null}
      {open ? (
        <div role="dialog" aria-modal="true" aria-labelledby={`${idBase}-h`} className="fixed inset-0 z-50 flex justify-end bg-ink/40">
          <div className="flex h-full w-full max-w-md flex-col gap-5 overflow-y-auto bg-bg p-6 text-ink shadow-card">
            <div className="flex items-center justify-between gap-3">
              <h2 id={`${idBase}-h`} className="font-head text-2xl font-semibold tracking-tight">
                {step === "done" && order ? `Order ${order.number}` : step === "details" ? "Your details" : "Your cart"}
              </h2>
              <Button type="button" size="icon" variant="ghost" onClick={() => setOpen(false)} aria-label="Close">
                <X className="size-5" aria-hidden="true" />
              </Button>
            </div>

            {step === "cart" ? (
              lines.length ? (
                <>
                  <ul className="flex flex-col divide-y divide-line">
                    {lines.map((l) => {
                      const p = prods[l.slug];
                      return (
                        <li key={l.slug} className="flex items-center justify-between gap-3 py-3">
                          <span className="min-w-0">
                            <span className="block font-medium">{l.name}</span>
                            <span className={cn("text-sm", p && p.in_stock === false ? "text-bad" : "text-muted")}>
                              {p ? (p.in_stock === false ? "Sold out" : p.price_text || "") : ""}
                            </span>
                          </span>
                          <span className="flex shrink-0 items-center gap-2">
                            <Button type="button" size="icon" variant="outline" onClick={() => setQty(l.slug, l.qty - 1)} aria-label={`One fewer ${l.name}`}>−</Button>
                            <span className="w-6 text-center tabular-nums" aria-label="Quantity">{l.qty}</span>
                            <Button type="button" size="icon" variant="outline" onClick={() => setQty(l.slug, l.qty + 1)} aria-label={`One more ${l.name}`}>+</Button>
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                  <p className="text-sm text-muted">The shop works out the total, delivery and any offer when you send the order.</p>
                  <Button type="button" size="lg" onClick={() => setStep("details")} disabled={!ways.length}>
                    {ways.length ? "Continue" : "Ordering online is closed right now"}
                  </Button>
                  <p className="text-xs text-muted">Your cart stays while this page is open.</p>
                </>
              ) : (
                <p className="text-muted">Your cart is empty.</p>
              )
            ) : null}

            {step === "details" ? (
              <form onSubmit={place} noValidate className="flex flex-col gap-4">
                <div className="flex flex-col gap-2">
                  <Label htmlFor={`${idBase}-n`}>Your name</Label>
                  <Input id={`${idBase}-n`} autoComplete="name" value={f.name} onChange={(e) => set("name")(e.target.value)} />
                </div>
                <div className="flex flex-col gap-2">
                  <Label htmlFor={`${idBase}-p`}>Mobile number</Label>
                  <Input id={`${idBase}-p`} type="tel" inputMode="tel" autoComplete="tel" placeholder="10 digits" value={f.phone} onChange={(e) => set("phone")(e.target.value)} />
                </div>
                {pickup ? (
                  <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={f.pickup} onChange={(e) => set("pickup")(e.target.checked)} className="size-4 accent-primary" />
                    I will pick it up from the shop
                  </label>
                ) : null}
                {!f.pickup ? (
                  <>
                    <div className="flex flex-col gap-2">
                      <Label htmlFor={`${idBase}-a`}>Delivery address</Label>
                      <Textarea id={`${idBase}-a`} rows={3} autoComplete="street-address" value={f.address} onChange={(e) => set("address")(e.target.value)} />
                    </div>
                    <div className="flex flex-col gap-2">
                      <Label htmlFor={`${idBase}-z`}>PIN code</Label>
                      <Input id={`${idBase}-z`} inputMode="numeric" autoComplete="postal-code" value={f.pincode} onChange={(e) => set("pincode")(e.target.value)} />
                    </div>
                  </>
                ) : null}
                <fieldset className="flex flex-col gap-2">
                  <legend className="mb-1 text-sm font-medium">Payment</legend>
                  {ways.map(([k, t], i) => (
                    <label key={k} className="flex items-center gap-2 text-sm">
                      <input type="radio" name={`${idBase}-m`} value={k} checked={(f.method || ways[0][0]) === k} onChange={() => set("method")(k)} className="size-4 accent-primary" />
                      {t}
                    </label>
                  ))}
                </fieldset>
                <div className="flex flex-col gap-2">
                  <Label htmlFor={`${idBase}-o`}>Note for the shop <span className="font-normal text-muted">(optional)</span></Label>
                  <Input id={`${idBase}-o`} value={f.note} onChange={(e) => set("note")(e.target.value)} />
                </div>
                <div className="flex flex-col gap-2">
                  <Label htmlFor={`${idBase}-c`}>Coupon code <span className="font-normal text-muted">(optional)</span></Label>
                  <Input id={`${idBase}-c`} autoComplete="off" maxLength={16} value={f.coupon} onChange={(e) => set("coupon")(e.target.value)} onBlur={tryCoupon} />
                  {couponSay ? <p className="text-sm text-muted" role="status">{couponSay}</p> : null}
                </div>
                <input ref={trap} type="text" name="website" tabIndex={-1} autoComplete="off" aria-hidden="true" className="hidden" />
                <p className="text-sm text-bad" role="status">{said}</p>
                <div className="flex gap-3">
                  <Button type="button" variant="outline" onClick={() => setStep("cart")}>Back</Button>
                  <Button type="submit" size="lg" disabled={busy} className="flex-1">{busy ? "Sending…" : "Send order"}</Button>
                </div>
              </form>
            ) : null}

            {step === "done" && order ? (
              <div className="flex flex-col gap-4" aria-live="polite">
                {order.status_text ? <p className="text-lg">{order.status_text}</p> : null}
                <ul className="flex flex-col divide-y divide-line">
                  {(order.items || []).map((x) => (
                    <li key={x.title} className="flex justify-between gap-3 py-2">
                      <span>{x.title} × {x.qty}</span>
                      <span className="tabular-nums">{x.amount}</span>
                    </li>
                  ))}
                </ul>
                {order.total ? (
                  <p className="font-semibold">Total: {order.total}{order.delivery && order.delivery !== "₹0" ? ` (delivery ${order.delivery})` : ""}</p>
                ) : null}
                {order.pay && order.status === "new" ? (
                  <div className="flex flex-col gap-3 rounded-card border border-line p-4">
                    <p>{order.pay.amount} to pay to <span className="font-medium">{order.pay.vpa}</span></p>
                    {/^data:image\/svg\+xml;base64,/.test(order.pay.qr || "") ? (
                      <img src={order.pay.qr} alt="UPI QR code" width={180} height={180} className="self-start" />
                    ) : null}
                    {/^upi:\/\/pay\?/.test(order.pay.link || "") ? (
                      <Button asChild><a href={order.pay.link}>Pay in your UPI app</a></Button>
                    ) : null}
                    <div className="flex flex-col gap-2">
                      <Label htmlFor={`${idBase}-u`}>Paid? The UPI reference (UTR)</Label>
                      <Input id={`${idBase}-u`} inputMode="numeric" value={utr} onChange={(e) => setUtr(e.target.value)} />
                      <Button type="button" variant="outline" onClick={paid} disabled={busy}>I have paid</Button>
                    </div>
                  </div>
                ) : null}
                {order.paid_online ? <p>Online payment received (confirmed by the payment gateway).</p> : null}
                {track ? <p className="text-sm">{track}</p> : null}
                {["confirmed", "packed", "shipped", "delivered", "cancelled"].includes(order.status) ? (
                  <Button asChild variant="outline">
                    <a href={`${api}/order/${encodeURIComponent(order.number)}/invoice?t=${encodeURIComponent(order.token)}${order.status === "cancelled" ? "&doc=credit" : ""}`} target="_blank" rel="noopener">
                      {order.status === "cancelled" ? "Credit note (PDF)" : "GST bill (PDF)"}
                    </a>
                  </Button>
                ) : null}
                {order.status === "delivered" ? (
                  <div className="flex flex-col gap-2 rounded-card border border-line p-4">
                    <p className="text-sm font-medium">How was it?</p>
                    <div role="group" aria-label="Stars" className="flex gap-2">
                      {["1", "2", "3", "4", "5"].map((n) => (
                        <Button key={n} type="button" size="icon" variant={stars === n ? "default" : "outline"} aria-pressed={stars === n} onClick={() => setStars(n)} aria-label={`${n} star${n === "1" ? "" : "s"}`}>
                          {n}
                        </Button>
                      ))}
                    </div>
                    <Textarea rows={2} value={review} onChange={(e) => setReview(e.target.value)} aria-label="Your review" />
                    <Button type="button" variant="outline" onClick={sendReview}>Send review</Button>
                  </div>
                ) : null}
                <p className="text-sm text-muted" role="status">{said}</p>
                {link ? (
                  <p className="text-sm">
                    Keep this link to see your order again:{" "}
                    <a className="break-all text-primary underline" href={link}>{link}</a>
                  </p>
                ) : null}
                {shopName ? <p className="text-sm text-muted">{shopName} hears of your order at once.</p> : null}
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </>
  );
}
