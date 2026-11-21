"use client"; // v0.999.82 D8 wave 8: her clinic's live queue on a React website - an island
// Hoola App Engine - Hoola's own kit file. The same queue as her HTML website (her website's member app on Hoola): the
// public board shows ONLY numbers (now serving, next, how many wait, minutes each) and updates live; a signed-in
// patient takes today's token (when she allows it) and sees how many are ahead; her staff add walk-ins, call the next
// token and mark who came. Tokens are given on Hoola's server under its lock - never by this page.
import * as React from "react";
import { BellRing, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { siteApp, siteRef, useMember } from "@/lib/member";

export interface QueueBoardProps {
  site: string;
  label?: string;
  signin?: string;
}

type Board = { on?: boolean; open?: boolean; label?: string; now?: number | null; next?: number[]; waiting?: number;
  min_each?: number; self_take?: boolean; done?: number };
type Mine = { token?: number | null; status?: string; ahead?: number; est_min?: number; now?: number | null };
type Tok = { token: number; name: string; phone?: string; status: string; by?: string };

export default function QueueBoard({ site, label, signin }: QueueBoardProps) {
  const { me, ready } = useMember(site);
  const [b, setB] = React.useState<Board | null>(null);
  const [mine, setMine] = React.useState<Mine | null>(null);
  const [toks, setToks] = React.useState<Tok[]>([]);
  const [walkIn, setWalkIn] = React.useState({ name: "", phone: "" });
  const [err, setErr] = React.useState("");
  const staff = !!me && (me.role === "staff" || me.role === "admin");

  React.useEffect(() => {                            // the public board, live (numbers only, no sign-in)
    if (!site) return;
    siteApp<Board>(site, "queue").then(setB).catch(() => undefined);
    let es: EventSource | null = null;
    try {
      es = new EventSource(`/api/site-app/${encodeURIComponent(siteRef(site))}/queue/live`);
      es.addEventListener("board", (e) => {
        try {
          setB(JSON.parse((e as MessageEvent).data) as Board);
        } catch {
          /* not a board */
        }
      });
    } catch {
      es = null;
    }
    return () => es?.close();
  }, [site]);

  const refresh = React.useCallback(() => {
    if (!me) return;
    if (staff) siteApp<{ tokens: Tok[] }>(site, "queue?staff=1").then((d) => setToks(d.tokens || [])).catch(() => undefined);
    else siteApp<Mine>(site, "queue?mine=1").then(setMine).catch(() => undefined);
  }, [me, staff, site]);
  React.useEffect(() => { refresh(); }, [refresh, b?.now, b?.waiting]);

  const act = async (path: string, body: Record<string, unknown>) => {
    setErr("");
    try {
      const d = await siteApp<Mine & { tokens?: Tok[] }>(site, path, "POST", body);
      if (d.tokens) setToks(d.tokens);
      else setMine(d);
      return true;
    } catch (x) {
      setErr((x as Error).message);
      return false;
    }
  };

  if (!site || !b || b.on === false) return null;
  const name = label || b.label || "Queue";
  return (
    <section className="mx-auto my-8 w-full max-w-6xl px-4 sm:px-6" data-block="queue_board">
      <Card>
        <CardHeader>
          <CardTitle>{name}</CardTitle>
          <CardDescription>{b.open === false ? "Today's queue has closed." : "Live - this updates by itself."}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <dl className="grid grid-cols-2 gap-4 md:grid-cols-4" aria-live="polite">
            <div className="rounded-card border border-line p-4">
              <dt className="text-sm text-muted">Now serving</dt>
              <dd className="text-4xl font-semibold tabular-nums">{b.now ?? "—"}</dd>
            </div>
            <div className="rounded-card border border-line p-4">
              <dt className="text-sm text-muted">Next</dt>
              <dd className="text-xl font-semibold tabular-nums">{(b.next || []).slice(0, 4).join(", ") || "—"}</dd>
            </div>
            <div className="rounded-card border border-line p-4">
              <dt className="text-sm text-muted">Waiting</dt>
              <dd className="text-4xl font-semibold tabular-nums">{b.waiting ?? 0}</dd>
            </div>
            <div className="rounded-card border border-line p-4">
              <dt className="text-sm text-muted">Minutes each</dt>
              <dd className="text-4xl font-semibold tabular-nums">{b.min_each ?? "—"}</dd>
            </div>
          </dl>
          {err ? <p role="alert" className="text-sm text-bad">{err}</p> : null}
          {ready && !me && b.self_take && b.open !== false ? (
            <div className="flex flex-wrap items-center gap-3">
              <p className="text-muted">Sign in to take your token.</p>
              {signin ? <Button asChild><a href={signin}>Sign in</a></Button> : null}
            </div>
          ) : null}
          {me && !staff ? (
            mine?.token ? (
              <div className="flex flex-wrap items-center gap-4 rounded-card border border-primary p-4">
                <BellRing className="size-6 text-primary" aria-hidden="true" />
                <p>
                  Your token <strong className="text-2xl tabular-nums">{mine.token}</strong>
                  {mine.status === "called" ? " - it is your turn now." : mine.status === "waiting"
                    ? ` - ${mine.ahead ?? 0} ahead of you, about ${mine.est_min ?? 0} minutes.` : ` - ${mine.status}.`}
                </p>
              </div>
            ) : b.self_take && b.open !== false ? (
              <Button className="w-fit" onClick={() => act("queue/take", {})}>Take a token</Button>
            ) : (
              <p className="text-muted">Tokens are given at the reception.</p>
            )
          ) : null}
          {staff ? (
            <div className="flex flex-col gap-4">
              <div className="flex flex-wrap gap-3">
                <Button onClick={() => act("queue/call", {})}>Call next</Button>
              </div>
              <form className="flex flex-wrap items-end gap-3" onSubmit={async (e) => {
                e.preventDefault();
                if (await act("queue/add", walkIn)) setWalkIn({ name: "", phone: "" });
              }}>
                <div className="flex flex-col gap-1">
                  <Label htmlFor="qb-name">Walk-in name</Label>
                  <Input id="qb-name" value={walkIn.name} onChange={(e) => setWalkIn({ ...walkIn, name: e.target.value })} />
                </div>
                <div className="flex flex-col gap-1">
                  <Label htmlFor="qb-phone">Mobile (for the "turn near" message)</Label>
                  <Input id="qb-phone" type="tel" inputMode="tel" value={walkIn.phone} onChange={(e) => setWalkIn({ ...walkIn, phone: e.target.value })} />
                </div>
                <Button type="submit" variant="outline"><Plus className="size-4" aria-hidden="true" />Add</Button>
              </form>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <caption className="sr-only">Today's tokens</caption>
                  <thead><tr className="border-b border-line"><th scope="col" className="px-3 py-2">Token</th><th scope="col" className="px-3 py-2">Name</th><th scope="col" className="px-3 py-2">Status</th><th scope="col" className="px-3 py-2"><span className="sr-only">Mark</span></th></tr></thead>
                  <tbody>
                    {toks.map((t) => (
                      <tr key={t.token} className="border-b border-line last:border-0">
                        <td className="px-3 py-2 tabular-nums">{t.token}</td>
                        <td className="px-3 py-2">{t.name}</td>
                        <td className="px-3 py-2">{t.status}</td>
                        <td className="px-3 py-2">
                          {t.status === "called" || t.status === "waiting" ? (
                            <span className="flex gap-2">
                              <Button size="sm" variant="outline" onClick={() => act("queue/mark", { token: t.token, status: "done" })}>Done</Button>
                              <Button size="sm" variant="ghost" onClick={() => act("queue/mark", { token: t.token, status: "skipped" })}>Did not come</Button>
                            </span>
                          ) : null}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </section>
  );
}
