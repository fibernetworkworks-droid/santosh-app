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
