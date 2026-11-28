"use client"; // v0.999.82 D8 wave 6: the catalogue's filter bar - an island above the list
// Hoola App Engine - Hoola's own kit file. Search, her own filter columns, a price range and a sort over EVERY item of
// the list, as her HTML website's catalogue has it. It reads the list's compact index (public/catalog/<list>.json,
// written by Hoola) only when the visitor starts filtering; until then the page is the pre-rendered list.
import * as React from "react";
import { Search, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";

type Row = [string, string, string, number | null, string, string[]];   // slug, title, price text, price, photo, filters

export interface CatalogFilterProps {
  src: string;
  list: string;
  label: string;
  facets: { key: string; label: string }[];
  gridId: string;
}

const SORTS = [["order", "Her order"], ["low", "Price: low to high"], ["high", "Price: high to low"], ["name", "Name"]] as const;
const SHOWN = 96;

export default function CatalogFilter({ src, list, label, facets, gridId }: CatalogFilterProps) {
  const [rows, setRows] = React.useState<Row[] | null>(null);
  const [failed, setFailed] = React.useState(false);
  const [q, setQ] = React.useState("");
  const [pick, setPick] = React.useState<Record<number, string>>({});
  const [lo, setLo] = React.useState("");
  const [hi, setHi] = React.useState("");
  const [sort, setSort] = React.useState("order");
  const id = React.useId();
  const active = !!(q.trim() || Object.values(pick).some(Boolean) || lo || hi || sort !== "order");

  const load = React.useCallback(() => {
    if (rows || failed) return;
    fetch(src).then((r) => (r.ok ? r.json() : Promise.reject(new Error("no index"))))
      .then((d: { items?: Row[] }) => setRows(Array.isArray(d.items) ? d.items : []))
      .catch(() => setFailed(true));
  }, [rows, failed, src]);

  React.useEffect(() => {                            // the visitor started filtering before touching the bar
    if (active) load();
  }, [active, load]);

  React.useEffect(() => {
    const g = document.getElementById(gridId);
    if (g) g.hidden = active && !!rows;
  }, [active, rows, gridId]);

  const values = React.useMemo(() => facets.map((_, i) => {
    const n: Record<string, number> = {};
    for (const r of rows || []) if (r[5][i]) n[r[5][i]] = (n[r[5][i]] || 0) + 1;
    return Object.entries(n).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0, 12);
  }), [rows, facets]);

  const hits = React.useMemo(() => {
    if (!rows) return [];
    const words = q.trim().toLowerCase().split(/\s+/).filter(Boolean);
    const min = lo === "" ? null : Number(lo), max = hi === "" ? null : Number(hi);
    const out = rows.filter((r) => words.every((w) => r[1].toLowerCase().includes(w) || r[5].some((v) => v.toLowerCase().includes(w)))
      && Object.entries(pick).every(([i, v]) => !v || r[5][Number(i)] === v)
      && (min === null || (r[3] !== null && r[3] >= min)) && (max === null || (r[3] !== null && r[3] <= max)));
    if (sort === "low") out.sort((a, b) => (a[3] ?? Infinity) - (b[3] ?? Infinity));
    if (sort === "high") out.sort((a, b) => (b[3] ?? -1) - (a[3] ?? -1));
    if (sort === "name") out.sort((a, b) => a[1].localeCompare(b[1]));
    return out;
  }, [rows, q, pick, lo, hi, sort]);

  const clear = () => { setQ(""); setPick({}); setLo(""); setHi(""); setSort("order"); };

  return (
    <div className="mx-auto mb-8 flex w-full max-w-6xl flex-col gap-4 px-4 sm:px-6" onFocusCapture={load} onPointerEnter={load}>
      <div className="flex flex-wrap items-end gap-3">
        <div className="relative min-w-56 flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" aria-hidden="true" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder={`Search the ${label.toLowerCase()}`}
            aria-label={`Search the ${label.toLowerCase()}`} className="pl-9" />
        </div>
        <div className="flex items-end gap-2">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-muted">Price from</span>
            <Input type="number" inputMode="numeric" min={0} value={lo} onChange={(e) => setLo(e.target.value)} className="w-28" />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-muted">to</span>
            <Input type="number" inputMode="numeric" min={0} value={hi} onChange={(e) => setHi(e.target.value)} className="w-28" />
          </label>
        </div>
        <div className="flex flex-col gap-1 text-sm">
          <span id={`${id}-sort`} className="text-muted">Sort</span>
          <Select value={sort} onValueChange={setSort}>
            <SelectTrigger aria-labelledby={`${id}-sort`} className="w-48"><SelectValue /></SelectTrigger>
            <SelectContent>
              {SORTS.map(([k, l]) => <SelectItem key={k} value={k}>{l}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        {active ? <Button variant="ghost" onClick={clear}><X className="size-4" aria-hidden="true" />Clear</Button> : null}
      </div>
      {rows ? facets.map((f, i) => values[i].length ? (
        <div key={f.key} className="flex flex-wrap items-center gap-2" role="group" aria-label={f.label}>
          <span className="text-sm text-muted">{f.label}</span>
          {values[i].map(([v, n]) => (
            <button key={v} type="button" aria-pressed={pick[i] === v} onClick={() => setPick((p) => ({ ...p, [i]: p[i] === v ? "" : v }))}
              className={cn("min-h-9 rounded-control border border-line px-3 text-sm transition-colors hover:border-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
                pick[i] === v ? "border-primary bg-primary text-primary-ink" : "bg-surface text-ink")}>
              {v} <span className="tabular-nums opacity-70">{n}</span>
            </button>
          ))}
        </div>
      ) : null) : null}
      {failed ? <p className="text-sm text-muted">The filter could not load; the full list is below.</p> : null}
      {active && rows ? (
        <div className="flex flex-col gap-4" aria-live="polite">
          <p className="text-sm text-muted">{hits.length} found{hits.length > SHOWN ? ` · the first ${SHOWN} shown` : ""}</p>
          <ul className="grid grid-cols-2 gap-4 sm:gap-6 md:grid-cols-3 lg:grid-cols-4">
            {hits.slice(0, SHOWN).map((r) => (
              <li key={r[0]}>
                <a href={`./${list}/${r[0]}`} className="group flex h-full flex-col gap-3 rounded-card no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
                  {r[4] ? <img src={r[4]} alt={r[1]} loading="lazy" className="aspect-square w-full rounded-card object-cover" />
                    : <span aria-hidden="true" className="aspect-square w-full rounded-card bg-primary/10" />}
                  <span className="font-medium text-ink group-hover:text-primary">{r[1]}</span>
                  {r[2] ? <span className="font-semibold tabular-nums">{r[2]}</span> : null}
                </a>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
