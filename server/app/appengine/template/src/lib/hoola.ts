// Hoola App Engine - locked by Hoola. The ONLY way this app reaches its data and sign-in: Hoola Cloud.
// The app runs in a sealed frame; this file asks the app's Hoola shell (the page around it), which keeps the sign-in
// and calls Hoola Cloud. Every rule (who may read, add, change) is checked on Hoola's server, never here.
// The same backend as Hoola websites and phone apps: every write journaled, daily backups, approvals, sessions.
// Not connected yet (later steps): files, live updates, payments, AI.
import type { Lists } from "./cloud.types";

export type ListName = keyof Lists;
export type Row<T> = T & { id: string; created: string; mine: boolean; sample?: boolean };
export type Member = { id: string; email: string; name: string; role: "member" | "staff" | "admin" };

let seq = 0;
const waiting = new Map<number, { resolve: (v: any) => void; reject: (e: Error) => void }>();
const inShell = window.parent !== window;

window.addEventListener("message", (e: MessageEvent) => {
  if (e.source !== window.parent) return;
  const d = e.data as { hoola?: string; id?: number; ok?: boolean; data?: unknown; error?: string };
  if (!d || d.hoola !== "cloud-r" || typeof d.id !== "number") return;
  const w = waiting.get(d.id);
  if (!w) return;
  waiting.delete(d.id);
  if (d.ok) w.resolve(d.data);
  else w.reject(new Error(d.error || "Hoola Cloud refused that."));
});

function call<T = any>(op: string, args: Record<string, unknown> = {}): Promise<T> {
  if (!inShell) return Promise.reject(new Error("Hoola Cloud is reached only inside the Hoola app page."));
  return new Promise<T>((resolve, reject) => {
    const id = ++seq;
    waiting.set(id, { resolve, reject });
    window.parent.postMessage({ hoola: "cloud", id, op, args }, "*");
    setTimeout(() => {
      if (waiting.delete(id)) reject(new Error("Hoola Cloud did not answer in time."));
    }, 20000);
  });
}

const listeners = new Set<(m: Member | null) => void>();
let current: Member | null = null;
function setMe(m: Member | null) {
  current = m;
  listeners.forEach((fn) => fn(m));
}

export const hoola = {
  connected: inShell,
  auth: {
    async signUp(p: { email: string; password: string; name?: string }): Promise<Member> {
      const r = await call<{ me: Member }>("signup", p);
      setMe(r.me);
      return r.me;
    },
    async signIn(p: { email: string; password: string }): Promise<Member> {
      const r = await call<{ me: Member; need_2fa?: boolean; ticket?: string }>("signin", p);
      if (r.need_2fa) {
        // the password was right; the member turned on an authenticator code: ask for it, then auth.verifyCode(ticket, code)
        throw Object.assign(new Error("Enter the code from your authenticator app."), { ticket: r.ticket || "" });
      }
      setMe(r.me);
      return r.me;
    },
    async signOut(): Promise<void> {
      await call("signout");
      setMe(null);
    },
    async me(): Promise<Member | null> {
      const r = await call<{ me: Member | null }>("me");
      setMe(r.me);
      return r.me;
    },
    // v0.999.7 B4 the one backend: phone OTP (when the SMS service is set up), authenticator 2FA, sign-in sessions
    async phoneStart(phone: string): Promise<{ sent: boolean }> {
      return call("otp_start", { phone });
    },
    async phoneVerify(p: { phone: string; code: string; name?: string; consent?: boolean }): Promise<Member> {
      const r = await call<{ me: Member }>("otp_verify", p);
      setMe(r.me);
      return r.me;
    },
    async verifyCode(ticket: string, code: string): Promise<Member> {
      const r = await call<{ me: Member }>("2fa_login", { ticket, code });
      setMe(r.me);
      return r.me;
    },
    sessions: () => call<{ sessions: { id: string; device: string; how: string; this: boolean; since: string }[] }>("sessions"),
    endSession: (id: string) => call("session_end", { id }),
    async signOutEverywhere(): Promise<void> {
      await call("signout_all");
      setMe(null);
    },
    current: (): Member | null => current,
    onChange(fn: (m: Member | null) => void): () => void {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
  },
  approvals: {
    list: () => call<{ approvals: unknown[] }>("approvals"),
    decide: (id: string, decision: "approve" | "reject", note = "") => call("decide", { id, decision, note }),
  },
  fn: (name: string, args: unknown[] = []) => call("fn", { name, args }),
  db: {
    collection<K extends ListName>(list: K) {
      return {
        async list(limit = 200): Promise<Row<Lists[K]>[]> {
          return (await call<{ rows: Row<Lists[K]>[] }>("list", { list, limit })).rows;
        },
        async create(data: Lists[K]): Promise<Row<Lists[K]>> {
          return (await call<{ row: Row<Lists[K]> }>("create", { list, data })).row;
        },
        async update(id: string, data: Partial<Lists[K]>): Promise<Row<Lists[K]>> {
          return (await call<{ row: Row<Lists[K]> }>("update", { list, id, data })).row;
        },
        async remove(id: string): Promise<void> {
          await call("remove", { list, id });
        },
      };
    },
  },
};
