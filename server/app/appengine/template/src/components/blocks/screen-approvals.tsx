// Approvals screen (signed-in portal): requests waiting on her, each approved or rejected with a reason.
import * as React from "react";
import { Check, ChevronRight, Inbox, Receipt, RotateCcw, ShoppingCart, Tag, Plane, X } from "lucide-react";
import { Section, Container, rupees, type Tone } from "./_kit";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/sonner";

export const variants = ["list", "inbox", "grouped"] as const;
export type ScreenApprovalsVariant = (typeof variants)[number];

export type ApprovalKind = "Leave" | "Expense" | "Refund" | "Discount" | "Purchase";

export interface ApprovalItem {
  id: string;
  kind: ApprovalKind;
  what: string;
  who: string;
  role: string;
  when: string;
  amount?: number;
  /** a short line from the person who asked */
  note: string;
  details: { label: string; value: string }[];
}

export interface ScreenApprovalsProps {
  variant?: ScreenApprovalsVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  items?: ApprovalItem[];
}

export const sample: Required<Omit<ScreenApprovalsProps, "variant" | "tone">> = {
  title: "Approvals",
  intro: "Requests waiting for your decision.",
  items: [
    {
      id: "AP-512",
      kind: "Expense",
      what: "Travel to the Nashik site",
      who: "Vikram Shetty",
      role: "Field lead",
      when: "Today, 9:12 am",
      amount: 3840,
      note: "Bus both ways and two nights' stay. Bills attached.",
      details: [
        { label: "Dates", value: "17-19 Nov 2026" },
        { label: "Bills", value: "4 attached" },
        { label: "Budget left this month", value: "₹11,200" },
      ],
    },
    {
      id: "AP-511",
      kind: "Refund",
      what: "Refund for a damaged parcel",
      who: "Anjali Mehta",
      role: "Customer care",
      when: "Today, 8:40 am",
      amount: 1850,
      note: "Customer Rohit Deshmukh sent photos of the broken jar.",
      details: [
        { label: "Order", value: "ORD-1031" },
        { label: "Paid by", value: "UPI" },
        { label: "Photos", value: "3 attached" },
      ],
    },
    {
      id: "AP-510",
      kind: "Leave",
      what: "Leave, 2 days",
      who: "Farah Khan",
      role: "Designer",
      when: "Yesterday",
      note: "My cousin's wedding in Lucknow. Work is handed over to Anjali.",
      details: [
        { label: "Dates", value: "27-28 Nov 2026" },
        { label: "Leave left", value: "9 days" },
        { label: "Cover", value: "Anjali Mehta" },
      ],
    },
    {
      id: "AP-509",
      kind: "Discount",
      what: "15% off a bulk order",
      who: "Anjali Mehta",
      role: "Customer care",
      when: "Yesterday",
      amount: 11130,
      note: "Sana Traders will order every month if we agree.",
      details: [
        { label: "Order value", value: "₹74,200" },
        { label: "Usual limit", value: "10%" },
        { label: "Customer", value: "Sana Traders, Indore" },
      ],
    },
    {
      id: "AP-508",
      kind: "Purchase",
      what: "Packing boxes, 500 pieces",
      who: "Vikram Shetty",
      role: "Field lead",
      when: "18 Nov",
      amount: 9250,
      note: "Stock runs out next week, Diwali orders are up.",
      details: [
        { label: "Supplier", value: "Om Packaging, Pune" },
        { label: "Delivery", value: "3 days" },
        { label: "Last price", value: "₹17.50 a box" },
      ],
    },
  ],
};

const KIND_ICON: Record<ApprovalKind, React.ComponentType<{ className?: string }>> = {
  Leave: Plane,
  Expense: Receipt,
  Refund: RotateCcw,
  Discount: Tag,
  Purchase: ShoppingCart,
};

type Decision = { result: "Approved" | "Rejected"; reason?: string };

function initials(name: string) {
  return name
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

function useQueue(items: ApprovalItem[]) {
  const [decided, setDecided] = React.useState<Record<string, Decision>>({});
  const [rejecting, setRejecting] = React.useState<ApprovalItem | null>(null);
  const undo = (id: string) =>
    setDecided((d) => {
      const n = { ...d };
      delete n[id];
      return n;
    });
  function approve(i: ApprovalItem) {
    setDecided((d) => ({ ...d, [i.id]: { result: "Approved" } }));
    toast.success("Approved", { description: `${i.what} for ${i.who}`, action: { label: "Undo", onClick: () => undo(i.id) } });
  }
  function reject(i: ApprovalItem, reason: string) {
    setDecided((d) => ({ ...d, [i.id]: { result: "Rejected", reason } }));
    toast("Rejected", { description: `${i.who} will see your reason.`, action: { label: "Undo", onClick: () => undo(i.id) } });
  }
  const pending = items.filter((i) => !decided[i.id]);
  return { decided, pending, approve, reject, rejecting, setRejecting };
}

type Q = ReturnType<typeof useQueue>;

function RejectDialog({ q }: { q: Q }) {
  const [reason, setReason] = React.useState("");
  const id = React.useId();
  const item = q.rejecting;
  const ok = reason.trim().length >= 3;
  return (
    <AlertDialog
      open={item !== null}
      onOpenChange={(o) => {
        if (!o) {
          q.setRejecting(null);
          setReason("");
        }
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Reject this request?</AlertDialogTitle>
          <AlertDialogDescription>
            {item ? `${item.what}, from ${item.who}.` : ""} They will get your reason with the decision.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <div className="flex flex-col gap-2">
          <Label htmlFor={id}>Reason</Label>
          <Textarea
            id={id}
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="For example: please attach the hotel bill first"
          />
        </div>
        <AlertDialogFooter>
          <AlertDialogCancel>Keep it waiting</AlertDialogCancel>
          <AlertDialogAction
            disabled={!ok}
            className={buttonVariants({ variant: "danger" })}
            onClick={() => {
              if (item && ok) q.reject(item, reason.trim());
              setReason("");
            }}
          >
            Reject
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

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

function Decide({ q, i, size = "md" }: { q: Q; i: ApprovalItem; size?: "sm" | "md" }) {
  const d = q.decided[i.id];
  if (d) {
    return (
      <Badge tone={d.result === "Approved" ? "ok" : "bad"} className="py-1">
        {d.result === "Approved" ? <Check aria-hidden="true" /> : <X aria-hidden="true" />}
        {d.result}
      </Badge>
    );
  }
  return (
    <div className="flex gap-2">
      <Button variant="secondary" size={size} onClick={() => q.setRejecting(i)} aria-label={`Reject: ${i.what} from ${i.who}`}>
        Reject
      </Button>
      <Button size={size} onClick={() => q.approve(i)} aria-label={`Approve: ${i.what} from ${i.who}`}>
        Approve
      </Button>
    </div>
  );
}

function Empty() {
  return (
    <div className="flex flex-col items-center gap-3 px-6 py-14 text-center">
      <span className="flex size-12 items-center justify-center rounded-full bg-ok/10 text-ok">
        <Check className="size-6" aria-hidden="true" />
      </span>
      <p className="font-medium">You are all caught up</p>
      <p className="text-sm text-muted">New requests will show up here.</p>
    </div>
  );
}

function ListView({ q, items }: { q: Q; items: ApprovalItem[] }) {
  const [show, setShow] = React.useState<"pending" | "decided">("pending");
  const list = show === "pending" ? q.pending : items.filter((i) => q.decided[i.id]);
  return (
    <>
      <div role="group" aria-label="Show" className="mb-4 inline-flex rounded-control border border-line bg-surface p-1">
        {(
          [
            ["pending", `Waiting (${q.pending.length})`],
            ["decided", `Decided (${items.length - q.pending.length})`],
          ] as const
        ).map(([k, label]) => (
          <button
            key={k}
            type="button"
            aria-pressed={show === k}
            onClick={() => setShow(k)}
            className={cn(
              "h-9 rounded-control px-3 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-primary",
              show === k ? "bg-primary/10 text-primary" : "text-muted hover:text-ink",
            )}
          >
            {label}
          </button>
        ))}
      </div>
      <Card className="overflow-hidden">
        {list.length === 0 ? (
          show === "pending" ? (
            <Empty />
          ) : (
            <p className="px-6 py-12 text-center text-sm text-muted">Nothing decided yet.</p>
          )
        ) : (
          <ul className="divide-y divide-line">
            {list.map((i) => {
              const Icon = KIND_ICON[i.kind];
              const d = q.decided[i.id];
              return (
                <li key={i.id} className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:p-5">
                  <div className="flex min-w-0 flex-1 items-start gap-3">
                    <Avatar className="size-10 shrink-0">
                      <AvatarFallback className="bg-primary/10 text-sm font-medium text-primary">{initials(i.who)}</AvatarFallback>
                    </Avatar>
                    <div className="min-w-0">
                      <h3 className="flex flex-wrap items-center gap-x-2 text-sm font-medium">
                        {i.what}
                        {i.amount ? <span className="tabular-nums text-ink">{rupees(i.amount)}</span> : null}
                      </h3>
                      <p className="mt-0.5 text-sm text-muted">
                        {i.who} · {i.role} · {i.when}
                      </p>
                      <p className="mt-1.5 flex items-center gap-1.5 text-xs text-muted">
                        <Icon className="size-3.5" />
                        {i.kind}
                        {d?.reason ? <span className="text-bad">· Reason: {d.reason}</span> : null}
                      </p>
                    </div>
                  </div>
                  <Decide q={q} i={i} />
                </li>
              );
            })}
          </ul>
        )}
      </Card>
    </>
  );
}

function InboxView({ q, items }: { q: Q; items: ApprovalItem[] }) {
  const [openId, setOpenId] = React.useState(items[0]?.id ?? "");
  const current = items.find((i) => i.id === openId) ?? items[0];
  function pickNext(after: string) {
    const rest = q.pending.filter((i) => i.id !== after);
    if (rest[0]) setOpenId(rest[0].id);
  }
  return (
    <div className="grid min-w-0 overflow-hidden rounded-card border border-line bg-surface shadow-card lg:grid-cols-5">
      <ul className="max-h-none divide-y divide-line border-b border-line lg:col-span-2 lg:max-h-160 lg:overflow-y-auto lg:border-b-0 lg:border-r" aria-label="Requests">
        {items.map((i) => {
          const on = current?.id === i.id;
          const d = q.decided[i.id];
          return (
            <li key={i.id}>
              <button
                type="button"
                aria-current={on ? "true" : undefined}
                onClick={() => setOpenId(i.id)}
                className={cn(
                  "flex w-full items-start gap-3 px-4 py-3.5 text-left transition-colors focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primary",
                  on ? "bg-primary/5" : "hover:bg-ink/5",
                )}
              >
                <span aria-hidden="true" className={cn("mt-2 size-2 shrink-0 rounded-full", d ? "bg-transparent" : "bg-primary")} />
                <span className="min-w-0 flex-1">
                  <span className="flex items-baseline justify-between gap-2">
                    <span className={cn("truncate text-sm", d ? "text-muted" : "font-medium")}>{i.who}</span>
                    <span className="shrink-0 text-xs text-muted">{i.when}</span>
                  </span>
                  <span className="mt-0.5 block truncate text-sm">{i.what}</span>
                  <span className="mt-1 flex items-center gap-2 text-xs text-muted">
                    {i.kind}
                    {i.amount ? <span className="tabular-nums">· {rupees(i.amount)}</span> : null}
                    {d ? <span className={d.result === "Approved" ? "text-ok" : "text-bad"}>· {d.result}</span> : null}
                  </span>
                </span>
                <ChevronRight className="mt-1 size-4 shrink-0 text-muted lg:hidden" aria-hidden="true" />
              </button>
            </li>
          );
        })}
      </ul>
      <div className="min-w-0 p-5 sm:p-8 lg:col-span-3">
        {current ? (
          <div key={current.id} className="flex flex-col gap-6 animate-fade-in">
            <div className="flex items-start gap-4">
              <Avatar className="size-12 shrink-0">
                <AvatarFallback className="bg-primary/10 font-medium text-primary">{initials(current.who)}</AvatarFallback>
              </Avatar>
              <div className="min-w-0">
                <p className="text-sm text-muted">
                  {current.kind} request · {current.id}
                </p>
                <h3 className="mt-1 font-head text-xl font-semibold">{current.what}</h3>
                <p className="mt-1 text-sm text-muted">
                  {current.who}, {current.role} · {current.when}
                </p>
              </div>
            </div>
            {current.amount ? (
              <p className="font-head text-4xl font-semibold tracking-tight tabular-nums">{rupees(current.amount)}</p>
            ) : null}
            <blockquote className="border-l-2 border-line pl-4 text-sm">{current.note}</blockquote>
            <dl className="grid gap-4 sm:grid-cols-3">
              {current.details.map((x) => (
                <div key={x.label} className="min-w-0">
                  <dt className="text-xs text-muted">{x.label}</dt>
                  <dd className="mt-0.5 text-sm font-medium">{x.value}</dd>
                </div>
              ))}
            </dl>
            {q.decided[current.id]?.reason ? (
              <p className="rounded-control bg-bad/10 px-3 py-2 text-sm text-bad">Reason sent: {q.decided[current.id]?.reason}</p>
            ) : null}
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-5">
              <p className="text-sm text-muted">{q.pending.length} still waiting</p>
              {q.decided[current.id] ? (
                <Decide q={q} i={current} />
              ) : (
                <div className="flex gap-2">
                  <Button variant="secondary" onClick={() => q.setRejecting(current)}>
                    Reject
                  </Button>
                  <Button
                    onClick={() => {
                      q.approve(current);
                      pickNext(current.id);
                    }}
                  >
                    Approve and next
                  </Button>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2 py-12 text-center text-muted">
            <Inbox className="size-6" aria-hidden="true" />
            <p className="text-sm">Pick a request to see it here.</p>
          </div>
        )}
      </div>
    </div>
  );
}

function GroupedView({ q, items }: { q: Q; items: ApprovalItem[] }) {
  const kinds = Array.from(new Set(items.map((i) => i.kind)));
  if (q.pending.length === 0) {
    return (
      <Card>
        <Empty />
      </Card>
    );
  }
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {kinds.map((k) => {
        const inKind = q.pending.filter((i) => i.kind === k);
        if (inKind.length === 0) return null;
        const Icon = KIND_ICON[k];
        const total = inKind.reduce((s, i) => s + (i.amount ?? 0), 0);
        return (
          <Card key={k} className="min-w-0">
            <CardHeader className="flex flex-row items-center justify-between gap-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Icon className="size-4 text-muted" />
                {k}
                <span className="rounded-full bg-ink/5 px-2 py-0.5 text-xs font-medium tabular-nums text-muted">{inKind.length}</span>
              </CardTitle>
              {total > 0 ? <span className="text-sm tabular-nums text-muted">{rupees(total)} in all</span> : null}
            </CardHeader>
            <CardContent className="px-0 pb-2">
              <ul className="divide-y divide-line">
                {inKind.map((i) => (
                  <li key={i.id} className="flex flex-col gap-3 px-6 py-3 sm:flex-row sm:items-center">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium">
                        {i.what}
                        {i.amount ? <span className="ml-2 tabular-nums text-muted">{rupees(i.amount)}</span> : null}
                      </p>
                      <p className="truncate text-xs text-muted">
                        {i.who} · {i.when}
                      </p>
                    </div>
                    <Decide q={q} i={i} size="sm" />
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

export default function ScreenApprovals({ variant = "list", tone, ...rest }: ScreenApprovalsProps) {
  const d = { ...sample, ...rest };
  const sampleShown = rest.items === undefined;
  const q = useQueue(d.items);
  return (
    <Section block="screen_approvals" variant={variant} tone={tone ?? "plain"} tight>
      <Container wide={variant !== "list"}>
        <Head title={d.title} intro={d.intro} sampleShown={sampleShown}>
          <p className="text-sm text-muted">
            <span className="font-medium tabular-nums text-ink">{q.pending.length}</span> waiting
            {q.pending.some((i) => i.amount) ? (
              <>
                {" "}
                · <span className="font-medium tabular-nums text-ink">{rupees(q.pending.reduce((s, i) => s + (i.amount ?? 0), 0))}</span> asked for
              </>
            ) : null}
          </p>
        </Head>
        {variant === "inbox" ? <InboxView q={q} items={d.items} /> : variant === "grouped" ? <GroupedView q={q} items={d.items} /> : <ListView q={q} items={d.items} />}
        <RejectDialog q={q} />
      </Container>
    </Section>
  );
}
