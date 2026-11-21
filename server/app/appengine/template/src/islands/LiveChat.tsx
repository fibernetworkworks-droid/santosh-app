"use client"; // v0.999.82 D8 wave 8: live chat with her team on a React website - a page-wide island
// Hoola App Engine - Hoola's own kit file. The same chat as her HTML website (her website's member app on Hoola): a
// signed-in visitor writes to her team and sees the replies arrive live; her staff (signed in on the website) see every
// conversation and reply. Her own replies go from her Hoola console on her tap - nothing here answers by itself.
import * as React from "react";
import { MessageCircle, Send, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { liveStream, siteApp, useMember, type LiveEvent } from "@/lib/member";

export interface LiveChatProps {
  site: string;
  /** the sign-in page, e.g. ./sign-in */
  signin?: string;
  shopName?: string;
}

type Msg = { id: string; text: string; staff: boolean; name?: string; at?: string };
type Thread = { member: string; name?: string; last?: string; unread?: number };

function Bubbles({ msgs, mine }: { msgs: Msg[]; mine: (m: Msg) => boolean }) {
  const end = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {                          // a block body: scrollIntoView may return a Promise, never a cleanup
    end.current?.scrollIntoView({ block: "end" });
  }, [msgs.length]);
  return (
    <div className="flex max-h-80 min-h-40 flex-col gap-2 overflow-y-auto pr-1" role="log" aria-live="polite">
      {msgs.length === 0 ? <p className="text-sm text-muted">No messages yet.</p> : null}
      {msgs.map((m) => (
        <div key={m.id} className={cn("max-w-xs rounded-card px-3 py-2 text-sm", mine(m) ? "self-end bg-primary text-primary-ink" : "self-start bg-surface text-ink")}>
          {!mine(m) && m.name ? <p className="mb-0.5 text-xs opacity-75">{m.name}</p> : null}
          <p className="whitespace-pre-wrap">{m.text}</p>
        </div>
      ))}
      <div ref={end} />
    </div>
  );
}

function Composer({ onSend, onTyping }: { onSend: (t: string) => Promise<void>; onTyping?: () => void }) {
  const [text, setText] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [err, setErr] = React.useState("");
  const send = async (e: React.FormEvent) => {
    e.preventDefault();
    const t = text.trim();
    if (!t) return;
    setBusy(true);
    setErr("");
    try {
      await onSend(t);
      setText("");
    } catch (x) {
      setErr((x as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <form onSubmit={send} className="flex flex-col gap-2">
      <Textarea value={text} maxLength={1000} rows={2} aria-label="Write a message" placeholder="Write a message"
        onChange={(e) => { setText(e.target.value); onTyping?.(); }} />
      {err ? <p role="alert" className="text-sm text-bad">{err}</p> : null}
      <Button type="submit" disabled={busy || !text.trim()} className="w-fit">
        <Send className="size-4" aria-hidden="true" />Send
      </Button>
    </form>
  );
}

export default function LiveChat({ site, signin, shopName }: LiveChatProps) {
  const { me, ready } = useMember(site);
  const [open, setOpen] = React.useState(false);
  const [msgs, setMsgs] = React.useState<Msg[]>([]);
  const [threads, setThreads] = React.useState<Thread[]>([]);
  const [thread, setThread] = React.useState("");
  const [typing, setTyping] = React.useState("");
  const [unread, setUnread] = React.useState(0);
  const staff = !!me && (me.role === "staff" || me.role === "admin");
  const typedAt = React.useRef(0);

  const loadMine = React.useCallback(() => {
    siteApp<{ messages: Msg[] }>(site, "chat").then((d) => setMsgs(d.messages || [])).catch(() => undefined);
  }, [site]);
  const loadThreads = React.useCallback(() => {
    siteApp<{ threads: Thread[] }>(site, "chat?all=1").then((d) => setThreads(d.threads || [])).catch(() => undefined);
  }, [site]);
  const loadThread = React.useCallback((m: string) => {
    siteApp<{ messages: Msg[] }>(site, `chat?member=${encodeURIComponent(m)}`).then((d) => setMsgs(d.messages || [])).catch(() => undefined);
  }, [site]);

  React.useEffect(() => {
    if (!open || !me) return;
    if (staff) {
      if (thread) loadThread(thread);
      else loadThreads();
    } else loadMine();
  }, [open, me, staff, thread, loadMine, loadThreads, loadThread]);

  React.useEffect(() => {
    if (!me) return;
    return liveStream(site, (ev: LiveEvent) => {
      if (ev.type === "chat") {
        const t = String(ev.thread || "");
        const mineThread = staff ? t === thread : t === me.id;
        if (mineThread) {
          const m: Msg = { id: String(ev.id || ""), text: String(ev.text || ""), staff: !!ev.staff, name: String(ev.name || "") };
          setMsgs((xs) => (xs.some((x) => x.id === m.id) ? xs : [...xs, m]));
        }
        if (staff && !thread) loadThreads();
        if (!open && !(ev.staff === staff)) setUnread((n) => n + 1);
      } else if (ev.type === "typing") {
        const t = String(ev.thread || "");
        if ((staff && t === thread) || (!staff && t === me.id && ev.staff)) {
          setTyping(String(ev.name || "Someone"));
          window.setTimeout(() => setTyping(""), 4000);
        }
      }
    });
  }, [site, me, staff, thread, open, loadThreads]);

  const typed = () => {
    if (!me || Date.now() - typedAt.current < 3000) return;
    typedAt.current = Date.now();
    siteApp(site, "live/typing", "POST", { thread: staff ? thread : me.id }).catch(() => undefined);
  };
  const write = async (t: string) => {
    const m = staff
      ? await siteApp<Msg>(site, `chat/${encodeURIComponent(thread)}`, "POST", { text: t })
      : await siteApp<Msg>(site, "chat", "POST", { text: t });
    setMsgs((xs) => (m && m.id && !xs.some((x) => x.id === m.id) ? [...xs, m] : xs));
  };

  if (!site || !ready) return null;
  const title = staff ? "Messages" : `Message ${shopName || "us"}`;
  return (
    <div className="fixed bottom-5 left-5 z-40 flex flex-col items-start gap-3">
      {open ? (
        <div role="dialog" aria-label={title} className="w-80 max-w-full rounded-card border border-line bg-bg p-4 shadow-card">
          <div className="mb-3 flex items-center justify-between gap-2">
            <p className="font-semibold">{staff && thread ? threads.find((x) => x.member === thread)?.name || "Conversation" : title}</p>
            <Button variant="ghost" size="sm" aria-label="Close" onClick={() => setOpen(false)}><X className="size-4" aria-hidden="true" /></Button>
          </div>
          {!me ? (
            <div className="flex flex-col gap-3">
              <p className="text-sm text-muted">Sign in to write to us. We reply here.</p>
              {signin ? <Button asChild className="w-fit"><a href={signin}>Sign in</a></Button> : null}
            </div>
          ) : staff && !thread ? (
            <ul className="flex max-h-80 flex-col gap-1 overflow-y-auto">
              {threads.length === 0 ? <li className="text-sm text-muted">No conversations yet.</li> : null}
              {threads.map((t) => (
                <li key={t.member}>
                  <button type="button" onClick={() => setThread(t.member)}
                    className="flex w-full items-center justify-between gap-2 rounded-control px-2 py-2 text-left text-sm hover:bg-ink/5">
                    <span className="truncate">{t.name || "Visitor"}{t.last ? <span className="block truncate text-muted">{t.last}</span> : null}</span>
                    {t.unread ? <span className="rounded-full bg-primary px-2 text-xs text-primary-ink">{t.unread}</span> : null}
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <div className="flex flex-col gap-3">
              {staff ? <button type="button" className="w-fit text-sm underline" onClick={() => { setThread(""); setMsgs([]); }}>All conversations</button> : null}
              <Bubbles msgs={msgs} mine={(m) => m.staff === staff} />
              {typing ? <p className="text-xs text-muted">{typing} is typing…</p> : null}
              <Composer onSend={write} onTyping={typed} />
            </div>
          )}
        </div>
      ) : null}
      <Button size="lg" onClick={() => { setOpen((o) => !o); setUnread(0); }} aria-expanded={open}>
        <MessageCircle className="size-4" aria-hidden="true" />
        {title}
        {unread ? <span className="ml-1 rounded-full bg-bg px-2 text-xs text-ink">{unread}</span> : null}
      </Button>
    </div>
  );
}
