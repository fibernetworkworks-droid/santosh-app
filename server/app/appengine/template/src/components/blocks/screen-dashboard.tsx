// Dashboard screen (signed-in portal): KPI tiles, a chart, the things that need her, recent activity.
import * as React from "react";
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { ArrowDownRight, ArrowUpRight, Check, Clock, FilePlus2, Plus, Send, UserPlus } from "lucide-react";
import { Section, Container, rupees, type Tone } from "./_kit";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { ChartContainer, ChartTooltip, ChartTooltipContent, CHART_COLORS } from "@/components/ui/chart";
import { toast } from "@/components/ui/sonner";

export const variants = ["overview", "rail", "greeting"] as const;
export type ScreenDashboardVariant = (typeof variants)[number];

export interface Kpi {
  label: string;
  value: number;
  /** how the number is written */
  kind?: "money" | "count" | "percent";
  /** change against the last period, in percent (+ up, - down) */
  change: number;
  /** true when a fall is the good direction (refunds, waiting time) */
  lowerIsBetter?: boolean;
}

export interface ChartPoint {
  label: string;
  current: number;
  previous: number;
}

export interface ActionItem {
  id: string;
  title: string;
  who: string;
  due: string;
  urgent?: boolean;
}

export interface ActivityItem {
  who: string;
  what: string;
  when: string;
}

export interface OwnItem {
  title: string;
  line: string;
  progress: number;
}

export interface ScreenDashboardProps {
  variant?: ScreenDashboardVariant;
  tone?: Tone;
  title?: string;
  greeting?: string;
  kpis?: Kpi[];
  week?: ChartPoint[];
  month?: ChartPoint[];
  chartTitle?: string;
  actions?: ActionItem[];
  activity?: ActivityItem[];
  items?: OwnItem[];
}

export const sample: Required<Omit<ScreenDashboardProps, "variant" | "tone">> = {
  title: "Overview",
  greeting: "Good morning, Meera",
  kpis: [
    { label: "Collected this month", value: 482300, kind: "money", change: 12.4 },
    { label: "New enquiries", value: 86, kind: "count", change: 8.1 },
    { label: "Open bookings", value: 34, kind: "count", change: -4.2 },
    { label: "Unpaid invoices", value: 41800, kind: "money", change: -9.6, lowerIsBetter: true },
  ],
  week: [
    { label: "Mon", current: 52000, previous: 46000 },
    { label: "Tue", current: 61000, previous: 51000 },
    { label: "Wed", current: 48000, previous: 55000 },
    { label: "Thu", current: 73000, previous: 58000 },
    { label: "Fri", current: 81000, previous: 64000 },
    { label: "Sat", current: 96000, previous: 79000 },
    { label: "Sun", current: 71300, previous: 66000 },
  ],
  month: [
    { label: "Week 1", current: 104000, previous: 98000 },
    { label: "Week 2", current: 121500, previous: 102000 },
    { label: "Week 3", current: 118300, previous: 111000 },
    { label: "Week 4", current: 138500, previous: 119000 },
  ],
  chartTitle: "Money collected",
  actions: [
    { id: "a1", title: "Approve refund of ₹1,850", who: "Rohit Deshmukh, Nagpur", due: "Today", urgent: true },
    { id: "a2", title: "Reply to a bulk order enquiry", who: "Sana Traders, Indore", due: "Today", urgent: true },
    { id: "a3", title: "Confirm Saturday's 4 pm booking", who: "Priya Nair, Kochi", due: "Tomorrow" },
    { id: "a4", title: "Send the GST invoice for October", who: "Kaveri Foods, Mysuru", due: "Fri" },
  ],
  activity: [
    { who: "Anjali", what: "marked order ORD-1042 as delivered", when: "10 min ago" },
    { who: "Payment", what: "₹12,400 received from Mehta Stores by UPI", when: "42 min ago" },
    { who: "Vikram", what: "added a new customer, Farah Khan from Lucknow", when: "1 h ago" },
    { who: "Booking", what: "Arjun Rao moved his visit to 21 Nov, 11 am", when: "3 h ago" },
    { who: "Anjali", what: "replied to 6 WhatsApp enquiries", when: "Yesterday" },
  ],
  items: [
    { title: "Diwali hampers", line: "148 of 200 packed", progress: 74 },
    { title: "Pune shop opening", line: "6 of 9 tasks done", progress: 66 },
    { title: "October accounts", line: "Waiting for 3 bills", progress: 88 },
  ],
};

function formatValue(k: Kpi): string {
  if (k.kind === "money") return rupees(k.value);
  if (k.kind === "percent") return `${k.value}%`;
  return k.value.toLocaleString("en-IN");
}

function shortRupees(n: number): string {
  if (n >= 100000) return `₹${(n / 100000).toFixed(1)}L`;
  if (n >= 1000) return `₹${Math.round(n / 1000)}k`;
  return rupees(n);
}

function Head({ title, sampleShown, children }: { title: string; sampleShown: boolean; children?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:mb-8 sm:flex-row sm:items-end sm:justify-between">
      <div className="flex min-w-0 items-center gap-3">
        <h2 className="truncate font-head text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h2>
        {sampleShown ? (
          <Badge tone="outline" title="These rows are sample data until your own records arrive">
            Sample
          </Badge>
        ) : null}
      </div>
      {children}
    </div>
  );
}

function KpiTile({ k, className }: { k: Kpi; className?: string }) {
  const up = k.change >= 0;
  const good = k.lowerIsBetter ? !up : up;
  const Arrow = up ? ArrowUpRight : ArrowDownRight;
  return (
    <Card className={cn("flex flex-col gap-3 p-5", className)}>
      <p className="text-sm text-muted">{k.label}</p>
      <p className="font-head text-2xl font-semibold tracking-tight tabular-nums sm:text-3xl">{formatValue(k)}</p>
      <p className={cn("flex items-center gap-1 text-xs font-medium", good ? "text-ok" : "text-bad")}>
        <Arrow className="size-3.5" aria-hidden="true" />
        <span className="tabular-nums">{Math.abs(k.change).toFixed(1)}%</span>
        <span className="font-normal text-muted">vs last period</span>
      </p>
    </Card>
  );
}

function ChartCard({ title, week, month, className }: { title: string; week: ChartPoint[]; month: ChartPoint[]; className?: string }) {
  const [range, setRange] = React.useState<"week" | "month">("week");
  const data = range === "week" ? week : month;
  const total = data.reduce((s, p) => s + p.current, 0);
  const before = data.reduce((s, p) => s + p.previous, 0);
  const change = before ? ((total - before) / before) * 100 : 0;
  const config = {
    current: { label: range === "week" ? "This week" : "This month", color: CHART_COLORS[0] },
    previous: { label: range === "week" ? "Last week" : "Last month", color: CHART_COLORS[1] },
  };
  return (
    <Card className={cn("min-w-0", className)}>
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <CardTitle>{title}</CardTitle>
          <CardDescription>
            <span className="font-medium tabular-nums text-ink">{rupees(total)}</span>{" "}
            <span className={change >= 0 ? "text-ok" : "text-bad"}>
              {change >= 0 ? "+" : ""}
              {change.toFixed(1)}%
            </span>{" "}
            against the period before
          </CardDescription>
        </div>
        <ToggleGroup
          type="single"
          value={range}
          onValueChange={(v) => v && setRange(v as "week" | "month")}
          aria-label="Chart range"
          className="rounded-control border border-line p-0.5"
        >
          <ToggleGroupItem value="week" size="sm" className="px-3">
            Week
          </ToggleGroupItem>
          <ToggleGroupItem value="month" size="sm" className="px-3">
            Month
          </ToggleGroupItem>
        </ToggleGroup>
      </CardHeader>
      <CardContent>
        <ChartContainer config={config} height={240}>
          <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--color-line)" />
            <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={8} />
            <YAxis tickLine={false} axisLine={false} width={48} tickFormatter={(v: number) => shortRupees(v)} />
            <ChartTooltip content={<ChartTooltipContent />} />
            <Area
              type="monotone"
              dataKey="previous"
              stroke="var(--color-previous)"
              fill="var(--color-previous)"
              fillOpacity={0.08}
              strokeDasharray="4 4"
              strokeWidth={1.5}
            />
            <Area type="monotone" dataKey="current" stroke="var(--color-current)" fill="var(--color-current)" fillOpacity={0.18} strokeWidth={2} />
          </AreaChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}

function NeedsAction({ items, className }: { items: ActionItem[]; className?: string }) {
  const [done, setDone] = React.useState<string[]>([]);
  const open = items.filter((i) => !done.includes(i.id));
  return (
    <Card className={cn("min-w-0", className)}>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle>Needs your action</CardTitle>
        <Badge tone={open.length ? "warn" : "ok"}>{open.length ? `${open.length} open` : "All clear"}</Badge>
      </CardHeader>
      <CardContent className="px-0 pb-2">
        {open.length === 0 ? (
          <p className="px-6 pb-4 text-sm text-muted">Nothing waiting on you. New requests will show up here.</p>
        ) : (
          <ul className="divide-y divide-line">
            {open.map((i) => (
              <li key={i.id} className="flex items-center gap-3 px-6 py-3">
                <span
                  aria-hidden="true"
                  className={cn("size-2 shrink-0 rounded-full", i.urgent ? "bg-bad" : "bg-line")}
                />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{i.title}</p>
                  <p className="truncate text-xs text-muted">
                    {i.who} · <span className={i.urgent ? "text-bad" : undefined}>{i.due}</span>
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="icon"
                  aria-label={`Mark done: ${i.title}`}
                  onClick={() => {
                    setDone((d) => [...d, i.id]);
                    toast.success("Marked as done", {
                      description: i.title,
                      action: { label: "Undo", onClick: () => setDone((d) => d.filter((x) => x !== i.id)) },
                    });
                  }}
                >
                  <Check className="size-4" />
                </Button>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function ActivityFeed({ items, className }: { items: ActivityItem[]; className?: string }) {
  return (
    <Card className={cn("min-w-0", className)}>
      <CardHeader>
        <CardTitle>Recent activity</CardTitle>
      </CardHeader>
      <CardContent>
        <ol className="relative flex flex-col gap-5 border-l border-line pl-5">
          {items.map((a, n) => (
            <li key={n} className="relative">
              <span aria-hidden="true" className="absolute -left-6 top-1.5 size-2 rounded-full bg-primary ring-4 ring-surface" />
              <p className="text-sm">
                <span className="font-medium">{a.who}</span> <span className="text-muted">{a.what}</span>
              </p>
              <p className="mt-0.5 flex items-center gap-1 text-xs text-muted">
                <Clock className="size-3" aria-hidden="true" />
                {a.when}
              </p>
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  );
}

function QuickActions() {
  const quick = [
    { label: "New invoice", icon: FilePlus2 },
    { label: "Add customer", icon: UserPlus },
    { label: "Send reminder", icon: Send },
  ];
  return (
    <div className="flex flex-wrap gap-2">
      {quick.map((q, n) => (
        <Button
          key={q.label}
          variant={n === 0 ? "primary" : "secondary"}
          onClick={() => toast(`${q.label} opens here`, { description: "Hoola fills in what it already knows." })}
        >
          <q.icon className="size-4" aria-hidden="true" />
          {q.label}
        </Button>
      ))}
    </div>
  );
}

export default function ScreenDashboard({ variant = "overview", tone, ...rest }: ScreenDashboardProps) {
  const d = { ...sample, ...rest };
  const sampleShown = rest.kpis === undefined;

  if (variant === "rail") {
    return (
      <Section block="screen_dashboard" variant={variant} tone={tone ?? "plain"} tight>
        <Container wide>
          <Head title={d.title} sampleShown={sampleShown}>
            <Button variant="secondary" onClick={() => toast("Report ready", { description: "The month's summary is in your downloads." })}>
              Download report
            </Button>
          </Head>
          <div className="grid gap-4 lg:grid-cols-12">
            <div className="grid gap-4 sm:grid-cols-2 lg:col-span-4 lg:grid-cols-1">
              {d.kpis.map((k) => (
                <KpiTile key={k.label} k={k} />
              ))}
            </div>
            <div className="flex min-w-0 flex-col gap-4 lg:col-span-8">
              <ChartCard title={d.chartTitle} week={d.week} month={d.month} />
              <NeedsAction items={d.actions} />
            </div>
          </div>
        </Container>
      </Section>
    );
  }

  if (variant === "greeting") {
    return (
      <Section block="screen_dashboard" variant={variant} tone={tone ?? "plain"} tight>
        <Container wide>
          <div className="mb-8 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div className="min-w-0">
              <div className="flex items-center gap-3">
                <h2 className="font-head text-3xl font-semibold tracking-tight sm:text-4xl">{d.greeting}</h2>
                {sampleShown ? <Badge tone="outline">Sample</Badge> : null}
              </div>
              <p className="mt-2 text-muted">
                {d.actions.length} things need you today, and {rupees(d.kpis[0]?.value ?? 0)} has come in this month.
              </p>
            </div>
            <QuickActions />
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            {d.items.map((it) => (
              <Card key={it.title} className="flex flex-col gap-4 p-5 transition-transform hover:-translate-y-0.5">
                <div className="flex items-start justify-between gap-3">
                  <h3 className="font-head text-lg font-semibold">{it.title}</h3>
                  <span className="text-sm font-medium tabular-nums text-muted">{it.progress}%</span>
                </div>
                <Progress value={it.progress} className="h-1.5 bg-line/60" aria-label={`${it.title}: ${it.progress}% done`} />
                <p className="text-sm text-muted">{it.line}</p>
              </Card>
            ))}
          </div>
          <div className="mt-4 grid gap-4 lg:grid-cols-5">
            <ChartCard title={d.chartTitle} week={d.week} month={d.month} className="lg:col-span-3" />
            <ActivityFeed items={d.activity} className="lg:col-span-2" />
          </div>
        </Container>
      </Section>
    );
  }

  return (
    <Section block="screen_dashboard" variant={variant} tone={tone ?? "plain"} tight>
      <Container wide>
        <Head title={d.title} sampleShown={sampleShown}>
          <Button onClick={() => toast("New entry opens here", { description: "Pick an invoice, a booking or a customer." })}>
            <Plus className="size-4" aria-hidden="true" />
            New
          </Button>
        </Head>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {d.kpis.map((k) => (
            <KpiTile key={k.label} k={k} />
          ))}
        </div>
        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          <ChartCard title={d.chartTitle} week={d.week} month={d.month} className="lg:col-span-2" />
          <NeedsAction items={d.actions} />
        </div>
        <ActivityFeed items={d.activity} className="mt-4" />
      </Container>
    </Section>
  );
}
