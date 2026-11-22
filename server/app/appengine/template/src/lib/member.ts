// Hoola App Engine - locked by Hoola. v0.999.82 D8 wave 7: a visitor's sign-in on her website - the SAME members, lists,
// rules and sessions as her HTML website on Hoola (/api/site-app/<site>/...); the server checks every rule, never this
// file. The visitor's session token is kept in her browser only where the page is allowed one (a website on its own
// address), the way her HTML website keeps it; under Hoola's address a page runs sealed and the sign-in lasts while the
// page is open. In the Studio preview the calls go to the preview's own data (<site>~p), never her real members.
// Pages and blocks never touch the token: they call siteApp() and useMember().
import * as React from "react";

export type Member = { id: string; email?: string; name?: string; role?: string; phone?: string; two_fa?: boolean };
export type Field = { key: string; label?: string; type?: string; options?: string[]; required?: boolean; private?: boolean };
export type List = { key: string; label?: string; fields: Field[]; rules?: Record<string, string> };
export type Schema = {
  signup?: boolean;
  collections?: List[];
  security?: { otp?: boolean; consent?: boolean; email_code?: boolean };
  error?: string;
};

const KEY = "hoola:member:";
const EVENT = "hoola-member";
let memory: Record<string, string> = {};

/** the Studio preview (Hoola's preview address) works on the preview's own data, never her real members */
export function siteRef(site: string): string {
  const preview = typeof location !== "undefined" && location.pathname.startsWith("/api/app-preview/");
  return preview ? `${site}~p` : site;
}

function tokenOf(site: string): string {
  try {
    return window.localStorage.getItem(KEY + site) || memory[site] || "";
  } catch {
    return memory[site] || "";
  }
}

export function setToken(site: string, token: string): void {
  memory = { ...memory, [site]: token };
  try {
    if (token) window.localStorage.setItem(KEY + site, token);
    else window.localStorage.removeItem(KEY + site);
  } catch {
    /* a sealed page keeps nothing */
  }
  window.dispatchEvent(new CustomEvent(EVENT, { detail: { site } }));
}

export class AppError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

/** one call to her website's app on Hoola; a 401 forgets the visitor's sign-in */
export async function siteApp<T>(site: string, path: string, method = "GET", body?: unknown): Promise<T> {
  const ref = siteRef(site);
  const tok = tokenOf(ref);
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (tok) headers.Authorization = `Bearer ${tok}`;
  const res = await fetch(`/api/site-app/${encodeURIComponent(ref)}/${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  let data: unknown = {};
  try {
    data = await res.json();
  } catch {
    data = {};
  }
  if (!res.ok) {
    if (res.status === 401 && tok) setToken(ref, "");
    const d = data as { detail?: unknown; error?: unknown };
    const msg = typeof d.detail === "string" ? d.detail : typeof d.error === "string" ? d.error : "That did not work. Please try again.";
    throw new AppError(msg, res.status);
  }
  return data as T;
}

/** after a sign-in answer: keep the visitor's token (the answer itself is never kept) */
export function signedIn(site: string, answer: { token?: string }): boolean {
  if (!answer || typeof answer.token !== "string" || !answer.token) return false;
  setToken(siteRef(site), answer.token);
  return true;
}

export async function signOut(site: string): Promise<void> {
  if (pushReady()) await pushOff(site).catch(() => undefined);   // wave 9: a shared computer stops getting her news
  try {
    await siteApp(site, "logout", "POST", {});
  } catch {
    /* the server forgets it anyway when it expires */
  }
  setToken(siteRef(site), "");
}

/** who is signed in on this website (null = a visitor), kept in step across the page's islands */
export function useMember(site: string): { me: Member | null; ready: boolean; refresh: () => void } {
  const [me, setMe] = React.useState<Member | null>(null);
  const [ready, setReady] = React.useState(false);
  const refresh = React.useCallback(() => {
    if (!site || !tokenOf(siteRef(site))) {
      setMe(null);
      setReady(true);
      return;
    }
    siteApp<{ me: Member | null }>(site, "me")
      .then((d) => setMe(d.me || null))
      .catch(() => setMe(null))
      .finally(() => setReady(true));
  }, [site]);
  React.useEffect(() => {
    refresh();
    const on = () => refresh();
    window.addEventListener(EVENT, on);
    return () => window.removeEventListener(EVENT, on);
  }, [refresh]);
  return { me, ready, refresh };
}

const schemas: Record<string, Promise<Schema>> = {};

/** her website's lists, fields and sign-in ways (no data) - read once a page */
export function useSchema(site: string): Schema | null {
  const [s, setS] = React.useState<Schema | null>(null);
  React.useEffect(() => {
    if (!site) return;
    const ref = siteRef(site);
    schemas[ref] = schemas[ref] || siteApp<Schema>(site, "schema").catch((e: Error) => ({ error: e.message }));
    let live = true;
    schemas[ref].then((d) => live && setS(d));
    return () => {
      live = false;
    };
  }, [site]);
  return s;
}

export type LiveEvent = { type: string; [k: string]: unknown };

/** v0.999.82 D8 wave 8: the website's live channel for a signed-in member (chat, typing, presence, row changes) - the
 *  same stream her HTML website reads. The token goes in the header (an EventSource cannot send one), so the stream is
 *  read with fetch; it reconnects by itself (with the last event's id) until the page stops it. */
export function liveStream(site: string, onEvent: (e: LiveEvent) => void): () => void {
  const ref = siteRef(site);
  let stopped = false;
  let last = "";
  let ctl: AbortController | null = null;
  let wait = 3000;
  const run = async () => {
    while (!stopped) {
      const tok = tokenOf(ref);
      if (!tok) return;
      ctl = new AbortController();
      try {
        const res = await fetch(`/api/site-app/${encodeURIComponent(ref)}/live${last ? `?last=${encodeURIComponent(last)}` : ""}`, {
          headers: { Authorization: `Bearer ${tok}` },
          signal: ctl.signal,
        });
        if (res.status === 401) {
          setToken(ref, "");
          return;
        }
        if (!res.ok || !res.body) throw new Error("no stream");
        const reader = res.body.getReader();
        const dec = new TextDecoder();
        let buf = "";
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          buf += dec.decode(value, { stream: true });
          let cut: number;
          while ((cut = buf.indexOf("\n\n")) >= 0) {
            const block = buf.slice(0, cut);
            buf = buf.slice(cut + 2);
            let data = "";
            for (const line of block.split("\n")) {
              if (line.startsWith("id:")) last = line.slice(3).trim();
              else if (line.startsWith("data:")) data += line.slice(5).trim();
              else if (line.startsWith("retry:")) wait = Math.max(1000, Number(line.slice(6)) || 3000);
            }
            if (!data) continue;
            try {
              const ev = JSON.parse(data) as LiveEvent;
              if (ev.type === "bye" && ev.why === "login") {
                setToken(ref, "");
                return;
              }
              onEvent(ev);
            } catch {
              /* a line that is not an event */
            }
          }
        }
      } catch {
        if (stopped) return;
      }
      await new Promise((r) => setTimeout(r, wait));
    }
  };
  void run();
  return () => {
    stopped = true;
    ctl?.abort();
  };
}

/** v0.999.91 D8 wave 9: notifications on this browser for a signed-in member - the same as her HTML website. Asked ONLY
 *  on the visitor's own tap, then the browser asks its own question; no yes = nothing stored, nothing sent. Works on
 *  her website's own address (a sealed page under Hoola's address cannot run the worker that shows them). */
export type PushState = "sealed" | "unsupported" | "blocked" | "off" | "on";
const SW = "/hoola-push-sw.js";

function pushReady(): boolean {
  return typeof window !== "undefined" && "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
}

function keyBytes(s: string): ArrayBuffer {
  const raw = atob((s + "=".repeat((4 - (s.length % 4)) % 4)).replace(/-/g, "+").replace(/_/g, "/"));
  const buf = new ArrayBuffer(raw.length);   // a plain ArrayBuffer: the newer DOM types refuse Uint8Array<ArrayBufferLike>
  const out = new Uint8Array(buf);
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return buf;
}

async function current(): Promise<PushSubscription | null> {
  const reg = await navigator.serviceWorker.getRegistration("/");
  return reg ? reg.pushManager.getSubscription() : null;
}

export async function pushState(): Promise<PushState> {
  if (typeof window === "undefined") return "unsupported";
  if (window.origin === "null" || location.pathname.startsWith("/api/") || location.pathname.startsWith("/apps/")) return "sealed";
  if (!pushReady() || !window.isSecureContext) return "unsupported";
  if (Notification.permission === "denied") return "blocked";
  try {
    return (await current()) ? "on" : "off";
  } catch {
    return "off";
  }
}

/** her tap: the browser's own question, then the subscription goes to her website's app on Hoola */
export async function pushOn(site: string): Promise<PushState> {
  const st = await pushState();
  if (st !== "off" && st !== "on") return st;
  const perm = await Notification.requestPermission();
  if (perm !== "granted") return perm === "denied" ? "blocked" : "off";
  const [reg, key] = await Promise.all([navigator.serviceWorker.register(SW, { scope: "/" }),
    siteApp<{ key: string }>(site, "push/key")]);
  await navigator.serviceWorker.ready;
  const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(key.key) });
  const j = sub.toJSON();
  await siteApp(site, "push/subscribe", "POST", { endpoint: j.endpoint, keys: j.keys, consent: true });
  return "on";
}

export async function pushOff(site: string): Promise<PushState> {
  const sub = await current().catch(() => null);
  if (sub) {
    await siteApp(site, "push/unsubscribe", "POST", { endpoint: sub.endpoint }).catch(() => undefined);
    await sub.unsubscribe().catch(() => false);
  }
  return pushState();
}

// ---------------------------------------------------------------- v0.999.103 D8 wave 10: her AI assistant
// Her own Hoola AI App (the one that answers her customers, built in AI Apps) answers on her website's own address:
// /api/aiapp-pub/<code>/... with its own notice, limits and monthly cost ceiling, checked on Hoola's server. The visitor
// agrees to the notice first; the chat's visitor token is kept here like the sign-in token (never by a page). Under
// Hoola's address (the sealed Studio preview) the assistant is not called: no visitor's words spend her credits there.
const AI_KEY = "hoola:ai:";
let aiMemory: Record<string, string> = {};

function aiTokenOf(code: string): string {
  try {
    return window.localStorage.getItem(AI_KEY + code) || aiMemory[code] || "";
  } catch {
    return aiMemory[code] || "";
  }
}

function setAiToken(code: string, token: string): void {
  aiMemory = { ...aiMemory, [code]: token };
  try {
    if (token) window.localStorage.setItem(AI_KEY + code, token);
    else window.localStorage.removeItem(AI_KEY + code);
  } catch {
    /* a sealed page keeps nothing */
  }
}

/** true under Hoola's address (the sealed Studio preview): the assistant answers only on her website's own address */
export function aiSealed(): boolean {
  if (typeof window === "undefined") return true;
  return window.origin === "null" || location.pathname.startsWith("/api/") || location.pathname.startsWith("/apps/");
}

/** has this visitor agreed to the assistant's notice on this browser? */
export function aiAgreed(code: string): boolean {
  return !!aiTokenOf(code);
}

/** one call to her AI assistant on Hoola (the embed channel: her app's embed switch decides); a 401 forgets the agreement */
export async function aiApp<T>(code: string, path = "", method = "GET", body?: unknown): Promise<T> {
  const tok = aiTokenOf(code);
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (tok) headers["X-Visitor-Token"] = tok;
  const res = await fetch(`/api/aiapp-pub/${encodeURIComponent(code)}${path ? "/" + path : ""}?embed=1`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  let data: unknown = {};
  try {
    data = await res.json();
  } catch {
    data = {};
  }
  if (!res.ok) {
    if (res.status === 401 && tok) setAiToken(code, "");
    const d = data as { detail?: unknown };
    throw new AppError(typeof d.detail === "string" ? d.detail : "That did not work. Please try again.", res.status);
  }
  return data as T;
}

/** the visitor's own tap on I agree: the notice is agreed on Hoola's server and the chat's token kept here */
export async function aiAgree(code: string): Promise<void> {
  const a = await aiApp<{ token?: string }>(code, "session", "POST", { consent: true });
  if (typeof a.token === "string" && a.token) setAiToken(code, a.token);
}
