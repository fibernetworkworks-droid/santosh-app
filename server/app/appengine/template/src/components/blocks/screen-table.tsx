// Data table screen (signed-in portal): search, status chips, sortable heads, a row menu and paging.
import * as React from "react";
import { format, parseISO } from "date-fns";
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  Copy,
  Eye,
  MoreHorizontal,
  Plus,
  Search,
  Trash2,
  BadgeCheck,
} from "lucide-react";
import { Section, Container, rupees, type Tone } from "./_kit";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { toast } from "@/components/ui/sonner";

export const variants = ["standard", "dense", "cards"] as const;
export type ScreenTableVariant = (typeof variants)[number];

export type RowStatus = "Paid" | "Pending" | "Overdue" | "Draft";

export interface TableRowData {
  id: string;
  name: string;
  city: string;
  amount: number;
  /** yyyy-mm-dd */
  date: string;
  status: RowStatus;
}

export interface ScreenTableProps {
  variant?: ScreenTableVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  rows?: TableRowData[];
  pageSize?: number;
}

export const sample: Required<Omit<ScreenTableProps, "variant" | "tone">> = {
  title: "Invoices",
  intro: "Every bill you have sent, newest first.",
  pageSize: 6,
  rows: [
    { id: "INV-1048", name: "Mehta Stores", city: "Ahmedabad", amount: 12400, date: "2026-11-19", status: "Paid" },
    { id: "INV-1047", name: "Kaveri Foods", city: "Mysuru", amount: 38650, date: "2026-11-18", status: "Pending" },
    { id: "INV-1046", name: "Priya Nair", city: "Kochi", amount: 2499, date: "2026-11-17", status: "Paid" },
    { id: "INV-1045", name: "Sana Traders", city: "Indore", amount: 74200, date: "2026-11-15", status: "Overdue" },
    { id: "INV-1044", name: "Rohit Deshmukh", city: "Nagpur", amount: 1850, date: "2026-11-14", status: "Paid" },
    { id: "INV-1043", name: "Farah Khan", city: "Lucknow", amount: 6300, date: "2026-11-12", status: "Draft" },
    { id: "INV-1042", name: "Arjun Rao", city: "Hyderabad", amount: 15999, date: "2026-11-10", status: "Pending" },
    { id: "INV-1041", name: "Gurpreet Singh", city: "Ludhiana", amount: 9100, date: "2026-11-08", status: "Overdue" },
    { id: "INV-1040", name: "Lata Iyer", city: "Chennai", amount: 4250, date: "2026-11-06", status: "Paid" },
    { id: "INV-1039", name: "Bose & Sons", city: "Kolkata", amount: 52800, date: "2026-11-04", status: "Paid" },
    { id: "INV-1038", name: "Neha Joshi", city: "Pune", amount: 3200, date: "2026-11-02", status: "Pending" },
    { id: "INV-1037", name: "Om Hardware", city: "Jaipur", amount: 21450, date: "2026-10-30", status: "Paid" },
    { id: "INV-1036", name: "Ayesha Siddiqui", city: "Bhopal", amount: 7800, date: "2026-10-28", status: "Draft" },
    { id: "INV-1035", name: "Coastal Ice Co.", city: "Goa", amount: 11600, date: "2026-10-25", status: "Paid" },
  ],
};

const STATUSES: RowStatus[] = ["Paid", "Pending", "Overdue", "Draft"];
const STATUS_TONE: Record<RowStatus, "ok" | "warn" | "bad" | "neutral"> = {
  Paid: "ok",
  Pending: "warn",
  Overdue: "bad",
  Draft: "neutral",
};

type SortKey = "id" | "name" | "amount" | "date" | "status";

function StatusPill({ status }: { status: RowStatus }) {
  const dot = { Paid: "bg-ok", Pending: "bg-warn", Overdue: "bg-bad", Draft: "bg-muted" }[status];
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface px-2 py-0.5 text-xs font-medium">
      <span aria-hidden="true" className={cn("size-1.5 rounded-full", dot)} />
      {status}
    </span>
  );
}

function useTable(source: TableRowData[], pageSize: number) {
  const [rows, setRows] = React.useState(source);
  const [query, setQuery] = React.useState("");
  const [status, setStatus] = React.useState<RowStatus | "All">("All");
  const [sort, setSort] = React.useState<{ key: SortKey; dir: "asc" | "desc" }>({ key: "date", dir: "desc" });
  const [page, setPage] = React.useState(0);
  const [picked, setPicked] = React.useState<string[]>([]);

  const shown = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = rows.filter(
      (r) =>
        (status === "All" || r.status === status) &&
        (!q || [r.id, r.name, r.city].some((v) => v.toLowerCase().includes(q))),
    );
    const sign = sort.dir === "asc" ? 1 : -1;
    return [...list].sort((a, b) => {
      const x = a[sort.key];
      const y = b[sort.key];
      return (typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y))) * sign;
    });
  }, [rows, query, status, sort]);

  const pages = Math.max(1, Math.ceil(shown.length / pageSize));
  const safePage = Math.min(page, pages - 1);
  const pageRows = shown.slice(safePage * pageSize, safePage * pageSize + pageSize);

  const counts = React.useMemo(() => {
    const c: Record<string, number> = { All: rows.length };
    for (const s of STATUSES) c[s] = rows.filter((r) => r.status === s).length;
    return c;
  }, [rows]);

  function toggleSort(key: SortKey) {
    setSort((s) => (s.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: key === "name" || key === "id" ? "asc" : "desc" }));
  }

  function remove(ids: string[]) {
    const gone = rows.filter((r) => ids.includes(r.id));
    setRows((rs) => rs.filter((r) => !ids.includes(r.id)));
    setPicked((p) => p.filter((x) => !ids.includes(x)));
    toast(ids.length === 1 ? `${ids[0]} deleted` : `${ids.length} invoices deleted`, {
      action: { label: "Undo", onClick: () => setRows((rs) => [...rs, ...gone]) },
    });
  }

  function markPaid(ids: string[]) {
    setRows((rs) => rs.map((r) => (ids.includes(r.id) ? { ...r, status: "Paid" } : r)));
    setPicked([]);
    toast.success(ids.length === 1 ? `${ids[0]} marked as paid` : `${ids.length} invoices marked as paid`);
  }

  function duplicate(id: string) {
    const r = rows.find((x) => x.id === id);
    if (!r) return;
    const next = `INV-${Math.max(...rows.map((x) => Number(x.id.replace(/\D/g, "")) || 0)) + 1}`;
    setRows((rs) => [{ ...r, id: next, status: "Draft", date: format(new Date(), "yyyy-MM-dd") }, ...rs]);
    toast.success(`${next} created as a draft`, { description: `A copy of ${id}` });
  }

  return {
    rows,
    query,
    setQuery: (v: string) => {
      setQuery(v);
      setPage(0);
    },
    status,
    setStatus: (s: RowStatus | "All") => {
      setStatus(s);
      setPage(0);
    },
    sort,
    toggleSort,
    page: safePage,
    pages,
    setPage,
    shown,
    pageRows,
    counts,
    picked,
    setPicked,
    remove,
    markPaid,
    duplicate,
  };
}

type TableState = ReturnType<typeof useTable>;

function Head({ title, intro, sampleShown, children }: { title: string; intro: string; sampleShown: boolean; children?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        <div className="flex items-center gap-3">
          <h2 className="font-head text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h2>
          {sampleShown ? <Badge tone="outline">Sample</Badge> : null}
        </div>
        <p className="mt-1 text-sm text-muted">{intro}</p>
      </div>
      {children}
    </div>
  );
}

function SearchBox({ t, className }: { t: TableState; className?: string }) {
  return (
    <div className={cn("relative min-w-0", className)}>
      <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" aria-hidden="true" />
      <Input
        value={t.query}
        onChange={(e) => t.setQuery(e.target.value)}
        placeholder="Search by name, city or number"
        aria-label="Search invoices"
        className="pl-9"
      />
    </div>
  );
}

function StatusChips({ t }: { t: TableState }) {
  return (
    <div role="group" aria-label="Filter by status" className="flex flex-wrap gap-2">
      {(["All", ...STATUSES] as const).map((s) => {
        const on = t.status === s;
        return (
          <button
            key={s}
            type="button"
            aria-pressed={on}
            onClick={() => t.setStatus(s)}
            className={cn(
              "inline-flex h-10 items-center gap-2 rounded-full border px-3.5 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary sm:h-9",
              on ? "border-primary bg-primary/10 text-primary" : "border-line bg-surface text-ink hover:bg-ink/5",
            )}
          >
            {s}
            <span className={cn("tabular-nums text-xs", on ? "text-primary" : "text-muted")}>{t.counts[s]}</span>
          </button>
        );
      })}
    </div>
  );
}

function SortHead({ t, k, label, className }: { t: TableState; k: SortKey; label: string; className?: string }) {
  const on = t.sort.key === k;
  const Icon = !on ? ArrowUpDown : t.sort.dir === "asc" ? ArrowUp : ArrowDown;
  return (
    <TableHead className={className} aria-sort={on ? (t.sort.dir === "asc" ? "ascending" : "descending") : "none"}>
      <button
        type="button"
        onClick={() => t.toggleSort(k)}
        className={cn(
          "-mx-2 inline-flex h-8 items-center gap-1.5 rounded-control px-2 font-medium transition-colors hover:bg-ink/5 focus-visible:outline-2 focus-visible:outline-primary",
          on ? "text-ink" : "text-muted",
        )}
      >
        {label}
        <Icon className="size-3.5" aria-hidden="true" />
      </button>
    </TableHead>
  );
}

function RowMenu({ t, row, onOpen }: { t: TableState; row: TableRowData; onOpen: (r: TableRowData) => void }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label={`Actions for ${row.id}`}>
          <MoreHorizontal className="size-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuItem onSelect={() => onOpen(row)}>
          <Eye className="size-4" aria-hidden="true" />
          Open
        </DropdownMenuItem>
        <DropdownMenuItem disabled={row.status === "Paid"} onSelect={() => t.markPaid([row.id])}>
          <BadgeCheck className="size-4" aria-hidden="true" />
          Mark as paid
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => t.duplicate(row.id)}>
          <Copy className="size-4" aria-hidden="true" />
          Duplicate
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem className="text-bad focus:text-bad" onSelect={() => t.remove([row.id])}>
          <Trash2 className="size-4" aria-hidden="true" />
          Delete
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function Pager({ t, pageSize }: { t: TableState; pageSize: number }) {
  const from = t.shown.length ? t.page * pageSize + 1 : 0;
  const to = Math.min(t.shown.length, (t.page + 1) * pageSize);
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 px-1 pt-4 text-sm text-muted">
      <p className="tabular-nums" aria-live="polite">
        {from}-{to} of {t.shown.length}
      </p>
      <div className="flex items-center gap-2">
        <Button variant="secondary" size="icon" aria-label="Previous page" disabled={t.page === 0} onClick={() => t.setPage(t.page - 1)}>
          <ChevronLeft className="size-4" />
        </Button>
        <span className="tabular-nums text-ink">
          Page {t.page + 1} of {t.pages}
        </span>
        <Button variant="secondary" size="icon" aria-label="Next page" disabled={t.page >= t.pages - 1} onClick={() => t.setPage(t.page + 1)}>
          <ChevronRight className="size-4" />
        </Button>
      </div>
    </div>
  );
}

function NoRows({ t }: { t: TableState }) {
  return (
    <div className="flex flex-col items-center gap-3 px-4 py-12 text-center">
      <p className="font-medium">No invoices match</p>
      <p className="text-sm text-muted">Try another name or clear the filters.</p>
      <Button
        variant="secondary"
        size="sm"
        onClick={() => {
          t.setQuery("");
          t.setStatus("All");
        }}
      >
        Clear filters
      </Button>
    </div>
  );
}

function RecordDialog({ row, onClose }: { row: TableRowData | null; onClose: () => void }) {
  return (
    <Dialog open={row !== null} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-md">
        {row ? (
          <>
            <DialogHeader>
              <DialogTitle>{row.id}</DialogTitle>
              <DialogDescription>
                {row.name}, {row.city}
              </DialogDescription>
            </DialogHeader>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
              <dt className="text-muted">Amount</dt>
              <dd className="text-right font-medium tabular-nums">{rupees(row.amount)}</dd>
              <dt className="text-muted">Date</dt>
              <dd className="text-right">{format(parseISO(row.date), "d MMM yyyy")}</dd>
              <dt className="text-muted">Status</dt>
              <dd className="flex justify-end">
                <StatusPill status={row.status} />
              </dd>
            </dl>
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

function day(d: string) {
  return format(parseISO(d), "d MMM");
}

export default function ScreenTable({ variant = "standard", tone, ...rest }: ScreenTableProps) {
  const d = { ...sample, ...rest };
  const sampleShown = rest.rows === undefined;
  const t = useTable(d.rows, d.pageSize);
  const [open, setOpen] = React.useState<TableRowData | null>(null);

  const addNew = () =>
    toast("New invoice opens here", { description: "Hoola fills the customer and GST details it already knows." });

  if (variant === "dense") {
    const allOnPage = t.pageRows.length > 0 && t.pageRows.every((r) => t.picked.includes(r.id));
    const someOnPage = t.pageRows.some((r) => t.picked.includes(r.id));
    return (
      <Section block="screen_table" variant={variant} tone={tone ?? "plain"} tight>
        <Container wide>
          <Head title={d.title} intro={d.intro} sampleShown={sampleShown}>
            <Button onClick={addNew}>
              <Plus className="size-4" aria-hidden="true" />
              Add new
            </Button>
          </Head>
          <Card className="min-w-0 overflow-hidden">
            <div className="flex flex-col gap-3 border-b border-line p-4 lg:flex-row lg:items-center lg:justify-between">
              <SearchBox t={t} className="lg:w-80" />
              <StatusChips t={t} />
            </div>
            {t.picked.length > 0 ? (
              <div className="flex flex-wrap items-center gap-3 border-b border-line bg-primary/5 px-4 py-2.5 text-sm animate-fade-in">
                <span className="font-medium tabular-nums">{t.picked.length} selected</span>
                <Button size="sm" variant="secondary" onClick={() => t.markPaid(t.picked)}>
                  Mark as paid
                </Button>
                <Button size="sm" variant="ghost" className="text-bad" onClick={() => t.remove(t.picked)}>
                  Delete
                </Button>
                <Button size="sm" variant="link" className="ml-auto" onClick={() => t.setPicked([])}>
                  Clear
                </Button>
              </div>
            ) : null}
            <div className="overflow-x-auto">
              <Table className="text-sm">
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-10">
                      <Checkbox
                        aria-label="Select all on this page"
                        checked={allOnPage ? true : someOnPage ? "indeterminate" : false}
                        onCheckedChange={(c) =>
                          t.setPicked((p) =>
                            c === true
                              ? Array.from(new Set([...p, ...t.pageRows.map((r) => r.id)]))
                              : p.filter((x) => !t.pageRows.some((r) => r.id === x)),
                          )
                        }
                      />
                    </TableHead>
                    <SortHead t={t} k="id" label="Number" />
                    <SortHead t={t} k="name" label="Customer" />
                    <SortHead t={t} k="date" label="Date" />
                    <SortHead t={t} k="status" label="Status" />
                    <SortHead t={t} k="amount" label="Amount" className="text-right" />
                    <TableHead className="w-12">
                      <span className="sr-only">Actions</span>
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {t.pageRows.map((r) => {
                    const on = t.picked.includes(r.id);
                    return (
                      <TableRow key={r.id} data-state={on ? "selected" : undefined} className="h-11">
                        <TableCell>
                          <Checkbox
                            aria-label={`Select ${r.id}`}
                            checked={on}
                            onCheckedChange={(c) => t.setPicked((p) => (c === true ? [...p, r.id] : p.filter((x) => x !== r.id)))}
                          />
                        </TableCell>
                        <TableCell className="whitespace-nowrap font-medium tabular-nums">{r.id}</TableCell>
                        <TableCell className="whitespace-nowrap">
                          {r.name} <span className="text-muted">· {r.city}</span>
                        </TableCell>
                        <TableCell className="whitespace-nowrap text-muted">{day(r.date)}</TableCell>
                        <TableCell>
                          <StatusPill status={r.status} />
                        </TableCell>
                        <TableCell className="text-right font-medium tabular-nums">{rupees(r.amount)}</TableCell>
                        <TableCell className="text-right">
                          <RowMenu t={t} row={r} onOpen={setOpen} />
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
              {t.pageRows.length === 0 ? <NoRows t={t} /> : null}
            </div>
            <div className="border-t border-line px-4 pb-4">
              <Pager t={t} pageSize={d.pageSize} />
            </div>
          </Card>
          <RecordDialog row={open} onClose={() => setOpen(null)} />
        </Container>
      </Section>
    );
  }

  if (variant === "cards") {
    return (
      <Section block="screen_table" variant={variant} tone={tone ?? "plain"} tight>
        <Container wide>
          <Head title={d.title} intro={d.intro} sampleShown={sampleShown}>
            <Button variant="secondary" onClick={addNew}>
              <Plus className="size-4" aria-hidden="true" />
              New invoice
            </Button>
          </Head>
          <div className="grid gap-6 lg:grid-cols-12">
            <aside className="flex flex-col gap-4 lg:col-span-3">
              <SearchBox t={t} />
              <div>
                <p className="mb-2 text-sm font-medium">Status</p>
                <StatusChips t={t} />
              </div>
              <div className="hidden rounded-card border border-line p-4 lg:block">
                <p className="text-sm text-muted">Waiting to be paid</p>
                <p className="mt-1 font-head text-2xl font-semibold tabular-nums">
                  {rupees(t.rows.filter((r) => r.status === "Pending" || r.status === "Overdue").reduce((s, r) => s + r.amount, 0))}
                </p>
              </div>
            </aside>
            <div className="min-w-0 lg:col-span-9">
              <ul className="flex flex-col gap-3 md:hidden">
                {t.pageRows.map((r) => (
                  <li key={r.id}>
                    <Card className="flex items-center gap-3 p-4">
                      <button
                        type="button"
                        onClick={() => setOpen(r)}
                        className="flex min-w-0 flex-1 flex-col items-start gap-1 rounded-control text-left focus-visible:outline-2 focus-visible:outline-primary"
                      >
                        <span className="flex w-full items-center justify-between gap-2">
                          <span className="truncate font-medium">{r.name}</span>
                          <span className="shrink-0 font-medium tabular-nums">{rupees(r.amount)}</span>
                        </span>
                        <span className="flex w-full items-center justify-between gap-2 text-xs text-muted">
                          <span className="truncate">
                            {r.id} · {r.city} · {day(r.date)}
                          </span>
                          <StatusPill status={r.status} />
                        </span>
                      </button>
                      <RowMenu t={t} row={r} onOpen={setOpen} />
                    </Card>
                  </li>
                ))}
              </ul>
              <Card className="hidden overflow-hidden md:block">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <SortHead t={t} k="name" label="Customer" />
                      <SortHead t={t} k="id" label="Number" />
                      <SortHead t={t} k="date" label="Date" />
                      <SortHead t={t} k="amount" label="Amount" className="text-right" />
                      <SortHead t={t} k="status" label="Status" />
                      <TableHead className="w-12">
                        <span className="sr-only">Actions</span>
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {t.pageRows.map((r) => (
                      <TableRow key={r.id} className="cursor-pointer" onClick={() => setOpen(r)}>
                        <TableCell>
                          <button
                            type="button"
                            className="rounded-control text-left font-medium hover:text-primary focus-visible:outline-2 focus-visible:outline-primary"
                            onClick={(e) => {
                              e.stopPropagation();
                              setOpen(r);
                            }}
                          >
                            {r.name}
                          </button>
                          <span className="block text-xs text-muted">{r.city}</span>
                        </TableCell>
                        <TableCell className="tabular-nums text-muted">{r.id}</TableCell>
                        <TableCell className="text-muted">{day(r.date)}</TableCell>
                        <TableCell className="text-right font-medium tabular-nums">{rupees(r.amount)}</TableCell>
                        <TableCell>
                          <StatusPill status={r.status} />
                        </TableCell>
                        <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
                          <RowMenu t={t} row={r} onOpen={setOpen} />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Card>
              {t.pageRows.length === 0 ? (
                <Card className="mt-3">
                  <NoRows t={t} />
                </Card>
              ) : null}
              <Pager t={t} pageSize={d.pageSize} />
            </div>
          </div>
          <RecordDialog row={open} onClose={() => setOpen(null)} />
        </Container>
      </Section>
    );
  }

  return (
    <Section block="screen_table" variant={variant} tone={tone ?? "plain"} tight>
      <Container wide>
        <Head title={d.title} intro={d.intro} sampleShown={sampleShown}>
          <Button onClick={addNew}>
            <Plus className="size-4" aria-hidden="true" />
            New invoice
          </Button>
        </Head>
        <div className="mb-4 flex flex-col gap-3">
          <SearchBox t={t} className="sm:max-w-sm" />
          <StatusChips t={t} />
        </div>
        <Card className="min-w-0 overflow-hidden">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <SortHead t={t} k="id" label="Number" />
                  <SortHead t={t} k="name" label="Customer" />
                  <TableHead>City</TableHead>
                  <SortHead t={t} k="date" label="Date" />
                  <SortHead t={t} k="amount" label="Amount" className="text-right" />
                  <SortHead t={t} k="status" label="Status" />
                  <TableHead className="w-12">
                    <span className="sr-only">Actions</span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {t.pageRows.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell className="whitespace-nowrap font-medium tabular-nums">{r.id}</TableCell>
                    <TableCell className="whitespace-nowrap">{r.name}</TableCell>
                    <TableCell className="whitespace-nowrap text-muted">{r.city}</TableCell>
                    <TableCell className="whitespace-nowrap text-muted">{day(r.date)}</TableCell>
                    <TableCell className="text-right font-medium tabular-nums">{rupees(r.amount)}</TableCell>
                    <TableCell>
                      <Badge tone={STATUS_TONE[r.status]}>{r.status}</Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <RowMenu t={t} row={r} onOpen={setOpen} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {t.pageRows.length === 0 ? <NoRows t={t} /> : null}
          </div>
        </Card>
        <Pager t={t} pageSize={d.pageSize} />
        <RecordDialog row={open} onClose={() => setOpen(null)} />
      </Container>
    </Section>
  );
}
