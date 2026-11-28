// Record detail screen (signed-in portal): who it is, its status, its fields, what happened, its files.
import * as React from "react";
import { ChevronDown, Download, FileText, Mail, MessageSquare, Pencil, Phone, MapPin } from "lucide-react";
import { Section, Container, rupees, type Tone } from "./_kit";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Separator } from "@/components/ui/separator";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { toast } from "@/components/ui/sonner";

export const variants = ["tabs", "split", "timeline"] as const;
export type ScreenDetailVariant = (typeof variants)[number];

export type RecordStatus = "Active" | "On hold" | "Closed";

export interface DetailField {
  label: string;
  value: string;
}

export interface DetailEvent {
  who: string;
  what: string;
  when: string;
}

export interface DetailPayment {
  ref: string;
  date: string;
  mode: string;
  amount: number;
  status: "Paid" | "Due";
}

export interface DetailFile {
  name: string;
  size: string;
  added: string;
}

export interface ScreenDetailProps {
  variant?: ScreenDetailVariant;
  tone?: Tone;
  name?: string;
  subtitle?: string;
  status?: RecordStatus;
  phone?: string;
  email?: string;
  city?: string;
  fields?: DetailField[];
  more?: DetailField[];
  activity?: DetailEvent[];
  payments?: DetailPayment[];
  files?: DetailFile[];
}

export const sample: Required<Omit<ScreenDetailProps, "variant" | "tone">> = {
  name: "Ananya Kulkarni",
  subtitle: "Customer since March 2024 · ID CUS-0381",
  status: "Active",
  phone: "+91 98220 41736",
  email: "ananya.k@example.in",
  city: "Pune, Maharashtra",
  fields: [
    { label: "Plan", value: "Yearly care plan" },
    { label: "Looked after by", value: "Vikram Shetty" },
    { label: "Language", value: "Marathi, English" },
    { label: "Next visit", value: "Sat, 22 Nov, 11:00 am" },
  ],
  more: [
    { label: "Address", value: "14, Shanti Kunj, Kothrud, Pune 411038" },
    { label: "GSTIN", value: "Not given" },
    { label: "Came through", value: "A friend's referral" },
    { label: "Preferred contact", value: "WhatsApp, after 6 pm" },
  ],
  activity: [
    { who: "Vikram Shetty", what: "booked the next visit for 22 Nov, 11 am", when: "Today, 9:40 am" },
    { who: "Payment", what: "₹4,500 received by UPI for the November instalment", when: "18 Nov" },
    { who: "Ananya", what: "asked on WhatsApp to move the visit to a Saturday", when: "16 Nov" },
    { who: "Vikram Shetty", what: "added the visit report and two photos", when: "8 Nov" },
    { who: "System", what: "renewed the yearly care plan", when: "1 Nov" },
  ],
  payments: [
    { ref: "PAY-2291", date: "18 Nov 2026", mode: "UPI", amount: 4500, status: "Paid" },
    { ref: "PAY-2240", date: "18 Oct 2026", mode: "UPI", amount: 4500, status: "Paid" },
    { ref: "PAY-2188", date: "18 Sep 2026", mode: "Card", amount: 4500, status: "Paid" },
    { ref: "PAY-2302", date: "18 Dec 2026", mode: "-", amount: 4500, status: "Due" },
  ],
  files: [
    { name: "Visit report, 8 Nov.pdf", size: "412 KB", added: "8 Nov" },
    { name: "Care plan agreement 2026.pdf", size: "1.2 MB", added: "1 Nov" },
    { name: "ID proof.jpg", size: "860 KB", added: "12 Mar 2024" },
  ],
};

const STATUS_TONE: Record<RecordStatus, "ok" | "warn" | "neutral"> = { Active: "ok", "On hold": "warn", Closed: "neutral" };

type D = Required<Omit<ScreenDetailProps, "variant" | "tone">>;

function initials(name: string) {
  return name
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

function useRecord(d: D) {
  const [status, setStatus] = React.useState<RecordStatus>(d.status);
  const [events, setEvents] = React.useState<DetailEvent[]>(d.activity);
  const [note, setNote] = React.useState("");
  function changeStatus(s: RecordStatus) {
    if (s === status) return;
    setStatus(s);
    setEvents((e) => [{ who: "You", what: `changed the status to ${s}`, when: "Just now" }, ...e]);
    toast.success(`Status changed to ${s}`);
  }
  function addNote() {
    const text = note.trim();
    if (!text) return;
    setEvents((e) => [{ who: "You", what: `added a note: "${text}"`, when: "Just now" }, ...e]);
    setNote("");
    toast.success("Note added");
  }
  return { status, changeStatus, events, note, setNote, addNote };
}

type R = ReturnType<typeof useRecord>;

function StatusMenu({ r }: { r: R }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="secondary">
          Status
          <ChevronDown className="size-4" aria-hidden="true" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-44">
        <DropdownMenuLabel>Change status</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuRadioGroup value={r.status} onValueChange={(v) => r.changeStatus(v as RecordStatus)}>
          {(["Active", "On hold", "Closed"] as RecordStatus[]).map((s) => (
            <DropdownMenuRadioItem key={s} value={s}>
              {s}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function RecordHead({ d, r, sampleShown, compact }: { d: D; r: R; sampleShown: boolean; compact?: boolean }) {
  return (
    <div className={cn("flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between", compact ? "" : "mb-8")}>
      <div className="flex min-w-0 items-center gap-4">
        <Avatar className="size-14 shrink-0">
          <AvatarFallback className="bg-primary/10 text-lg font-semibold text-primary">{initials(d.name)}</AvatarFallback>
        </Avatar>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-head text-2xl font-semibold tracking-tight sm:text-3xl">{d.name}</h2>
            <Badge tone={STATUS_TONE[r.status]}>{r.status}</Badge>
            {sampleShown ? <Badge tone="outline">Sample</Badge> : null}
          </div>
          <p className="mt-1 truncate text-sm text-muted">{d.subtitle}</p>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" onClick={() => toast("Opening WhatsApp", { description: d.phone })}>
          <MessageSquare className="size-4" aria-hidden="true" />
          Message
        </Button>
        <StatusMenu r={r} />
        <Button onClick={() => toast("Editing opens here", { description: "Change any field, then save." })}>
          <Pencil className="size-4" aria-hidden="true" />
          Edit
        </Button>
      </div>
    </div>
  );
}

function FieldGrid({ fields, cols = 2 }: { fields: DetailField[]; cols?: 1 | 2 }) {
  return (
    <dl className={cn("grid gap-x-6 gap-y-4", cols === 2 ? "sm:grid-cols-2" : "")}>
      {fields.map((f) => (
        <div key={f.label} className="min-w-0">
          <dt className="text-xs text-muted">{f.label}</dt>
          <dd className="mt-0.5 break-words text-sm font-medium">{f.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function Contact({ d }: { d: D }) {
  const rows = [
    { icon: Phone, text: d.phone, label: "Phone" },
    { icon: Mail, text: d.email, label: "Email" },
    { icon: MapPin, text: d.city, label: "City" },
  ];
  return (
    <ul className="flex flex-col gap-3 text-sm">
      {rows.map((c) => (
        <li key={c.label} className="flex min-w-0 items-center gap-3">
          <c.icon className="size-4 shrink-0 text-muted" aria-label={c.label} />
          <span className="truncate">{c.text}</span>
        </li>
      ))}
    </ul>
  );
}

function Timeline({ r, withNote = true }: { r: R; withNote?: boolean }) {
  const id = React.useId();
  return (
    <div className="flex flex-col gap-6">
      {withNote ? (
        <div className="flex flex-col gap-2">
          <Label htmlFor={id}>Add a note</Label>
          <Textarea id={id} rows={2} value={r.note} onChange={(e) => r.setNote(e.target.value)} placeholder="What happened, what is next..." />
          <Button size="sm" className="self-end" disabled={!r.note.trim()} onClick={r.addNote}>
            Add note
          </Button>
        </div>
      ) : null}
      <ol className="relative flex flex-col gap-5 border-l border-line pl-5" aria-label="Activity">
        {r.events.map((e, n) => (
          <li key={`${e.when}-${n}`} className={cn("relative", n === 0 && e.when === "Just now" ? "animate-fade-in" : "")}>
            <span aria-hidden="true" className={cn("absolute -left-6 top-1.5 size-2 rounded-full ring-4 ring-surface", n === 0 ? "bg-primary" : "bg-line")} />
            <p className="text-sm">
              <span className="font-medium">{e.who}</span> <span className="text-muted">{e.what}</span>
            </p>
            <p className="mt-0.5 text-xs text-muted">{e.when}</p>
          </li>
        ))}
      </ol>
    </div>
  );
}

function Files({ files }: { files: DetailFile[] }) {
  return (
    <ul className="divide-y divide-line">
      {files.map((f) => (
        <li key={f.name} className="flex items-center gap-3 py-3">
          <FileText className="size-5 shrink-0 text-muted" aria-hidden="true" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{f.name}</p>
            <p className="text-xs text-muted">
              {f.size} · added {f.added}
            </p>
          </div>
          <Button variant="ghost" size="icon" aria-label={`Download ${f.name}`} onClick={() => toast("Download started", { description: f.name })}>
            <Download className="size-4" />
          </Button>
        </li>
      ))}
    </ul>
  );
}

function Payments({ rows }: { rows: DetailPayment[] }) {
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Payment</TableHead>
            <TableHead>Date</TableHead>
            <TableHead>Mode</TableHead>
            <TableHead className="text-right">Amount</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((p) => (
            <TableRow key={p.ref}>
              <TableCell className="whitespace-nowrap">
                <span className="font-medium tabular-nums">{p.ref}</span>
                {p.status === "Due" ? (
                  <Badge tone="warn" className="ml-2">
                    Due
                  </Badge>
                ) : null}
              </TableCell>
              <TableCell className="whitespace-nowrap text-muted">{p.date}</TableCell>
              <TableCell className="text-muted">{p.mode}</TableCell>
              <TableCell className="text-right font-medium tabular-nums">{rupees(p.amount)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function RecordTabs({ d, r, withSummary }: { d: D; r: R; withSummary?: boolean }) {
  const paid = d.payments.filter((p) => p.status === "Paid").reduce((s, p) => s + p.amount, 0);
  return (
    <Tabs defaultValue="details" className="min-w-0">
      <TabsList>
        <TabsTrigger value="details">Details</TabsTrigger>
        <TabsTrigger value="activity">
          Activity <span className="ml-1 tabular-nums text-muted">{r.events.length}</span>
        </TabsTrigger>
        <TabsTrigger value="files">
          Files <span className="ml-1 tabular-nums text-muted">{d.files.length}</span>
        </TabsTrigger>
      </TabsList>
      <TabsContent value="details" className="mt-4 flex flex-col gap-4">
        <Card>
          <CardHeader>
            <CardTitle>{withSummary ? "More about this customer" : "Details"}</CardTitle>
          </CardHeader>
          <CardContent>
            <FieldGrid fields={withSummary ? d.more : [...d.fields, ...d.more]} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-3">
            <CardTitle>Payments</CardTitle>
            <span className="text-sm text-muted">
              Paid so far <span className="font-medium tabular-nums text-ink">{rupees(paid)}</span>
            </span>
          </CardHeader>
          <CardContent>
            <Payments rows={d.payments} />
          </CardContent>
        </Card>
      </TabsContent>
      <TabsContent value="activity" className="mt-4">
        <Card>
          <CardContent className="pt-6">
            <Timeline r={r} />
          </CardContent>
        </Card>
      </TabsContent>
      <TabsContent value="files" className="mt-4">
        <Card>
          <CardContent className="py-2">
            <Files files={d.files} />
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  );
}

export default function ScreenDetail({ variant = "tabs", tone, ...rest }: ScreenDetailProps) {
  const d = { ...sample, ...rest };
  const sampleShown = rest.name === undefined;
  const r = useRecord(d);

  if (variant === "split") {
    return (
      <Section block="screen_detail" variant={variant} tone={tone ?? "plain"} tight>
        <Container wide>
          <div className="grid items-start gap-6 lg:grid-cols-3">
            <Card className="flex flex-col gap-6 p-6 lg:sticky lg:top-6">
              <div className="flex flex-col items-start gap-4">
                <Avatar className="size-16">
                  <AvatarFallback className="bg-primary/10 text-xl font-semibold text-primary">{initials(d.name)}</AvatarFallback>
                </Avatar>
                <div className="min-w-0">
                  <h2 className="font-head text-2xl font-semibold tracking-tight">{d.name}</h2>
                  <p className="mt-1 text-sm text-muted">{d.subtitle}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Badge tone={STATUS_TONE[r.status]}>{r.status}</Badge>
                    {sampleShown ? <Badge tone="outline">Sample</Badge> : null}
                  </div>
                </div>
              </div>
              <Contact d={d} />
              <Separator />
              <FieldGrid fields={d.fields} cols={1} />
              <div className="flex flex-wrap gap-2">
                <StatusMenu r={r} />
                <Button onClick={() => toast("Editing opens here", { description: "Change any field, then save." })}>
                  <Pencil className="size-4" aria-hidden="true" />
                  Edit
                </Button>
              </div>
            </Card>
            <div className="min-w-0 lg:col-span-2">
              <RecordTabs d={d} r={r} withSummary />
            </div>
          </div>
        </Container>
      </Section>
    );
  }

  if (variant === "timeline") {
    return (
      <Section block="screen_detail" variant={variant} tone={tone ?? "plain"} tight>
        <Container wide>
          <RecordHead d={d} r={r} sampleShown={sampleShown} />
          <div className="grid items-start gap-6 lg:grid-cols-5">
            <div className="flex min-w-0 flex-col gap-6 lg:col-span-3">
              <Card>
                <CardHeader>
                  <CardTitle>Contact</CardTitle>
                </CardHeader>
                <CardContent>
                  <Contact d={d} />
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>Details</CardTitle>
                </CardHeader>
                <CardContent>
                  <FieldGrid fields={[...d.fields, ...d.more]} />
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>Files</CardTitle>
                </CardHeader>
                <CardContent className="py-0 pb-2">
                  <Files files={d.files} />
                </CardContent>
              </Card>
            </div>
            <Card className="min-w-0 lg:col-span-2">
              <CardHeader>
                <CardTitle>What happened</CardTitle>
              </CardHeader>
              <CardContent>
                <Timeline r={r} />
              </CardContent>
            </Card>
          </div>
        </Container>
      </Section>
    );
  }

  return (
    <Section block="screen_detail" variant={variant} tone={tone ?? "plain"} tight>
      <Container>
        <RecordHead d={d} r={r} sampleShown={sampleShown} />
        <div className="mb-6 grid grid-cols-2 gap-4 rounded-card border border-line bg-surface p-5 sm:grid-cols-4">
          {d.fields.map((f) => (
            <div key={f.label} className="min-w-0">
              <p className="text-xs text-muted">{f.label}</p>
              <p className="mt-0.5 truncate text-sm font-medium">{f.value}</p>
            </div>
          ))}
        </div>
        <RecordTabs d={d} r={r} withSummary />
      </Container>
    </Section>
  );
}
