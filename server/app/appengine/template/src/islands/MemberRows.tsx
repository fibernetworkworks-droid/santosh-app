"use client"; // v0.999.82 D8 wave 7: her real lists on the signed-in pages of a React website - an island
// Hoola App Engine - Hoola's own kit file. It shows a signed-in member the rows of one of her website's lists that the
// rules let them see (their own, or all for staff), lets them add one where the rules allow, a count per list for a
// dashboard, and their account (sign out, sign out everywhere, a copy of their data, delete the account after a
// confirm). Every rule is checked on Hoola's server; a visitor who is not signed in is sent to the sign-in page.
import * as React from "react";
import { Download, LogOut, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { signOut, siteApp, useMember, useSchema, type Field, type List } from "@/lib/member";

export interface MemberRowsProps {
  site: string;
  /** the list's key on her website; empty = the first list the member may see */
  list?: string;
  mode?: "rows" | "add" | "counts" | "account";
  title?: string;
  intro?: string;
  /** the sign-in page, e.g. ./sign-in */
  signin?: string;
}

type Row = Record<string, unknown> & { id: string; created?: string; mine?: boolean };

const shown = (l: List, staff: boolean) => l.fields.filter((x) => staff || !x.private).slice(0, 5);
const canAdd = (l: List, signed: boolean) => (l.rules?.create === "public" || (l.rules?.create === "member" && signed));
const text = (v: unknown) => (v === true ? "Yes" : v === false ? "No" : v === null || v === undefined ? "" : String(v));

function AddForm({ site, l, onDone }: { site: string; l: List; onDone: () => void }) {
  const [v, setV] = React.useState<Record<string, string | boolean>>({});
  const [err, setErr] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      const data: Record<string, unknown> = {};
      for (const f of l.fields) if (v[f.key] !== undefined && v[f.key] !== "") data[f.key] = f.type === "number" ? Number(v[f.key]) : v[f.key];
      await siteApp(site, `c/${encodeURIComponent(l.key)}`, "POST", data);
      setV({});
      onDone();
    } catch (x) {
      setErr((x as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const input = (f: Field) => {
    const id = `mr-${l.key}-${f.key}`;
    const val = v[f.key];
    if (f.type === "yes_no")
      return <Checkbox id={id} checked={val === true} onCheckedChange={(c) => setV({ ...v, [f.key]: c === true })} />;
    if (f.type === "choice" && f.options?.length)
      return (
        <Select value={String(val ?? "")} onValueChange={(o) => setV({ ...v, [f.key]: o })}>
          <SelectTrigger id={id} className="w-full sm:w-72"><SelectValue placeholder="Choose" /></SelectTrigger>
          <SelectContent>
            {f.options.map((o) => <SelectItem key={o} value={o}>{o}</SelectItem>)}
          </SelectContent>
        </Select>
      );
    if (f.type === "long_text") return <Textarea id={id} value={String(val ?? "")} onChange={(e) => setV({ ...v, [f.key]: e.target.value })} />;
    const type = { number: "number", email: "email", phone: "tel", date: "date", url: "url" }[f.type || ""] || "text";
    return <Input id={id} type={type} value={String(val ?? "")} onChange={(e) => setV({ ...v, [f.key]: e.target.value })} />;
  };
  return (
    <form onSubmit={save} className="flex flex-col gap-4">
      {l.fields.filter((f) => !f.private).map((f) => (
        <div key={f.key} className="flex flex-col gap-2">
          <Label htmlFor={`mr-${l.key}-${f.key}`}>{f.label || f.key}{f.required ? " *" : ""}</Label>
          {input(f)}
        </div>
      ))}
      {err ? <p role="alert" className="text-sm text-bad">{err}</p> : null}
      <Button type="submit" disabled={busy} className="w-fit">{busy ? "Saving" : `Add to ${l.label || l.key}`}</Button>
    </form>
  );
}

function Account({ site }: { site: string }) {
  const { me } = useMember(site);
  const [sure, setSure] = React.useState(false);
  const [said, setSaid] = React.useState("");
  if (!me) return null;
  const copy = async () => {
    const d = await siteApp<unknown>(site, "me/export");
    const url = URL.createObjectURL(new Blob([JSON.stringify(d, null, 2)], { type: "application/json" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "my-data.json";
    a.click();
    URL.revokeObjectURL(url);
  };
  const gone = async () => {
    try {
      await siteApp(site, "me/delete", "POST", { confirm: true });
      await signOut(site);
    } catch (x) {
      setSaid((x as Error).message);
    }
  };
  return (
    <div className="flex flex-col gap-4">
      <p>{me.name || me.email}{me.email && me.name ? ` · ${me.email}` : ""}{me.role && me.role !== "member" ? ` · ${me.role}` : ""}</p>
      <div className="flex flex-wrap gap-3">
        <Button variant="outline" onClick={() => signOut(site)}><LogOut className="size-4" aria-hidden="true" />Sign out</Button>
        <Button variant="outline" onClick={() => siteApp(site, "logout-all", "POST", {}).then(() => signOut(site))}>Sign out everywhere</Button>
        <Button variant="outline" onClick={copy}><Download className="size-4" aria-hidden="true" />A copy of my data</Button>
        {sure ? (
          <Button variant="destructive" onClick={gone}><Trash2 className="size-4" aria-hidden="true" />Yes, delete my account</Button>
        ) : (
          <Button variant="ghost" onClick={() => setSure(true)}>Delete my account</Button>
        )}
      </div>
      {sure ? <p className="text-sm text-muted">This removes your account and what you added. It cannot be undone.</p> : null}
      {said ? <p role="alert" className="text-sm text-bad">{said}</p> : null}
    </div>
  );
}

export default function MemberRows({ site, list, mode = "rows", title, intro, signin }: MemberRowsProps) {
  const { me, ready } = useMember(site);
  const schema = useSchema(site);
  const [rows, setRows] = React.useState<Row[] | null>(null);
  const [counts, setCounts] = React.useState<Record<string, number>>({});
  const [err, setErr] = React.useState("");
  const [adding, setAdding] = React.useState(mode === "add");
  const staff = !!me && (me.role === "staff" || me.role === "admin");
  const lists = schema?.collections || [];
  const l = lists.find((x) => x.key === list) || lists[0];

  const load = React.useCallback(() => {
    if (!me || !l) return;
    if (mode === "counts") {
      Promise.all(lists.slice(0, 6).map((x) => siteApp<{ rows: Row[] }>(site, `c/${encodeURIComponent(x.key)}`)
        .then((d) => [x.key, d.rows.length] as const).catch(() => [x.key, -1] as const)))
        .then((all) => setCounts(Object.fromEntries(all)));
      return;
    }
    siteApp<{ rows: Row[] }>(site, `c/${encodeURIComponent(l.key)}`)
      .then((d) => setRows(d.rows || []))
      .catch((x: Error) => setErr(x.message));
  }, [me, l, lists, mode, site]);
  React.useEffect(() => { load(); }, [load]);

  const head = (title || intro) ? (
    <CardHeader>
      {title ? <CardTitle>{title}</CardTitle> : null}
      {intro ? <CardDescription>{intro}</CardDescription> : null}
    </CardHeader>
  ) : null;
  const wrap = (body: React.ReactNode) => (
    <section className="mx-auto my-8 w-full max-w-6xl px-4 sm:px-6" data-hoola-live="">
      <Card>{head}<CardContent className={head ? "" : "pt-6"}>{body}</CardContent></Card>
    </section>
  );

  if (!site || !ready) return null;
  if (!me) {
    return wrap(
      <div className="flex flex-wrap items-center gap-4">
        <p className="text-muted">Sign in to see this.</p>
        {signin ? <Button asChild><a href={signin}>Sign in</a></Button> : null}
      </div>,
    );
  }
  if (mode === "account") return wrap(<Account site={site} />);
  if (schema?.error) return wrap(<p className="text-sm text-bad">{schema.error}</p>);
  if (!l) return wrap(<p className="text-muted">Nothing here yet.</p>);
  if (mode === "counts") {
    return wrap(
      <ul className="grid grid-cols-2 gap-4 md:grid-cols-3">
        {lists.slice(0, 6).map((x) => (
          <li key={x.key} className="rounded-card border border-line p-4">
            <p className="text-sm text-muted">{x.label || x.key}</p>
            <p className="text-3xl font-semibold tabular-nums">{counts[x.key] === undefined ? "…" : counts[x.key] < 0 ? "—" : counts[x.key]}</p>
          </li>
        ))}
      </ul>,
    );
  }
  const cols = shown(l, staff);
  const addable = canAdd(l, true);
  return wrap(
    <div className="flex flex-col gap-6">
      {err ? <p role="alert" className="text-sm text-bad">{err}</p> : null}
      {mode !== "add" ? (
        rows === null ? <p className="text-muted">Loading…</p> : rows.length === 0 ? (
          <p className="text-muted">Nothing in {l.label || l.key} yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">{l.label || l.key}</caption>
              <thead>
                <tr className="border-b border-line">
                  {cols.map((c) => <th key={c.key} scope="col" className="px-3 py-2 font-medium">{c.label || c.key}</th>)}
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id} className="border-b border-line last:border-0">
                    {cols.map((c) => <td key={c.key} className="px-3 py-2">{text(r[c.key])}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      ) : null}
      {addable ? (
        adding ? <AddForm site={site} l={l} onDone={() => { if (mode !== "add") setAdding(false); load(); }} /> : (
          <Button variant="outline" className="w-fit" onClick={() => setAdding(true)}>
            <Plus className="size-4" aria-hidden="true" />Add to {l.label || l.key}
          </Button>
        )
      ) : null}
    </div>,
  );
}
