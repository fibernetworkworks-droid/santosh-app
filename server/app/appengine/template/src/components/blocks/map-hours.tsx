"use client"; // v0.999.64 D3: needs JavaScript in the browser - on a pre-rendered site page it is an island
// v0.999.51 D1 block: Map + hours. Three layouts - a map card beside the week's hours, a tab per branch, and one quiet
// line with how to reach. The "Open now" badge is worked out from HER hours in India time and refreshes every minute.
import * as React from "react";
import { Bus, Car, MapPin, Navigation, Phone, TrainFront } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { GridPattern } from "@/components/effects";
import { Section, Container, SectionHead, type Tone } from "./_kit";

export const variants = ["card", "branches", "minimal"] as const;
export type MapHoursVariant = (typeof variants)[number];

/** One day, Monday first. open / close are 24-hour "HH:mm"; no open = closed that day. close before open = past midnight. */
export interface DayHours {
  day: string;
  open?: string;
  close?: string;
}

export interface Branch {
  name: string;
  address: string;
  phone?: string;
  hours: DayHours[];
}

export interface ReachNote {
  how: "bus" | "metro" | "parking";
  text: string;
}

export interface MapHoursProps {
  variant?: MapHoursVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  address?: string;
  landmark?: string;
  mapsQuery?: string;
  hours?: DayHours[];
  holiday?: string;
  reach?: ReachNote[];
  branches?: Branch[];
}

const WEEK: DayHours[] = [
  { day: "Monday", open: "10:00", close: "20:00" },
  { day: "Tuesday", open: "10:00", close: "20:00" },
  { day: "Wednesday", open: "10:00", close: "20:00" },
  { day: "Thursday", open: "10:00", close: "20:00" },
  { day: "Friday", open: "10:00", close: "20:00" },
  { day: "Saturday", open: "10:00", close: "20:30" },
  { day: "Sunday", open: "10:00", close: "14:00" },
];

export const sample: Required<Omit<MapHoursProps, "variant" | "tone">> = {
  title: "Find us",
  intro: "Five minutes from Ramdaspeth square, on the first floor.",
  address: "12, Shanti Complex, Ramdaspeth, Nagpur 440010",
  landmark: "Opposite the Ramdaspeth post office. Look for the blue board above the chemist.",
  mapsQuery: "Shanti Complex Ramdaspeth Nagpur",
  hours: WEEK,
  holiday: "Closed on 26 January, 15 August, 2 October and Diwali day.",
  reach: [
    { how: "bus", text: "Aapli Bus routes 12 and 27 stop at Ramdaspeth square, a 4-minute walk." },
    { how: "metro", text: "Rachana Ring Road metro station is 1.5 km away; autos wait outside." },
    { how: "parking", text: "Two-wheelers park in front. Cars fit in the lane behind the building." },
  ],
  branches: [
    { name: "Ramdaspeth", address: "12, Shanti Complex, Ramdaspeth, Nagpur 440010", phone: "+91 98220 45117", hours: WEEK },
    {
      name: "Dharampeth",
      address: "4, Laxmi Bhuvan, West High Court Road, Dharampeth, Nagpur 440010",
      phone: "+91 98220 45118",
      hours: [
        { day: "Monday" },
        { day: "Tuesday", open: "11:00", close: "19:00" },
        { day: "Wednesday", open: "11:00", close: "19:00" },
        { day: "Thursday", open: "11:00", close: "19:00" },
        { day: "Friday", open: "11:00", close: "19:00" },
        { day: "Saturday", open: "11:00", close: "19:00" },
        { day: "Sunday", open: "11:00", close: "19:00" },
      ],
    },
  ],
};

const SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function mins(t?: string): number | null {
  if (!t) return null;
  const m = /^(\d{1,2}):(\d{2})$/.exec(t.trim());
  if (!m) return null;
  return Number(m[1]) * 60 + Number(m[2]);
}

/** "20:30" -> "8:30 pm", "10:00" -> "10 am". */
export function clock(t?: string): string {
  const v = mins(t);
  if (v === null) return "";
  const h = Math.floor(v / 60) % 24;
  const mm = v % 60;
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}${mm ? `:${String(mm).padStart(2, "0")}` : ""} ${h < 12 ? "am" : "pm"}`;
}

function span(d: DayHours): string {
  return d.open && d.close ? `${clock(d.open)} – ${clock(d.close)}` : "Closed";
}

/** The week in a line: "Mon – Sat 10 am – 8 pm · Sun 10 am – 2 pm". */
export function weekLine(hours: DayHours[]): string {
  const out: string[] = [];
  let i = 0;
  while (i < hours.length) {
    let j = i;
    while (j + 1 < hours.length && span(hours[j + 1]) === span(hours[i])) j++;
    const days = i === j ? SHORT[i] : `${SHORT[i]} – ${SHORT[j]}`;
    out.push(`${days} ${span(hours[i])}`);
    i = j + 1;
  }
  return out.join(" · ");
}

/** Day of week (0 = Monday) and minutes past midnight, in India time. */
function nowInIndia(): { dow: number; at: number } {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Kolkata",
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date());
  const get = (k: string) => parts.find((p) => p.type === k)?.value ?? "";
  const dow = Math.max(0, SHORT.indexOf(get("weekday").slice(0, 3)));
  return { dow, at: Number(get("hour")) * 60 + Number(get("minute")) };
}

export interface OpenState {
  open: boolean;
  soon: boolean;
  line: string;
  today: number;
}

export function openState(hours: DayHours[], now: { dow: number; at: number }): OpenState {
  const n = hours.length || 7;
  const day = (k: number) => hours[((k % n) + n) % n];
  const today = day(now.dow);
  const o = mins(today?.open);
  const c = mins(today?.close);
  const prev = day(now.dow - 1);
  const po = mins(prev?.open);
  const pc = mins(prev?.close);
  if (po !== null && pc !== null && pc <= po && now.at < pc) {
    return { open: true, soon: pc - now.at <= 30, line: `closes at ${clock(prev?.close)}`, today: now.dow };
  }
  if (o !== null && c !== null) {
    const overnight = c <= o;
    if (now.at >= o && (overnight || now.at < c)) {
      const left = overnight ? 24 * 60 - now.at + c : c - now.at;
      return { open: true, soon: left <= 30, line: `closes at ${clock(today?.close)}`, today: now.dow };
    }
    if (now.at < o) return { open: false, soon: false, line: `opens today at ${clock(today?.open)}`, today: now.dow };
  }
  for (let k = 1; k <= 7; k++) {
    const nd = day(now.dow + k);
    if (nd?.open && nd.close) {
      const when = k === 1 ? "tomorrow" : nd.day;
      return { open: false, soon: false, line: `opens ${when} at ${clock(nd.open)}`, today: now.dow };
    }
  }
  return { open: false, soon: false, line: "hours not set", today: now.dow };
}

function useOpenState(hours: DayHours[]): OpenState | null {
  const [s, setS] = React.useState<OpenState | null>(null);
  React.useEffect(() => {
    const tick = () => setS(openState(hours, nowInIndia()));
    tick();
    const t = setInterval(tick, 60_000);
    return () => clearInterval(t);
  }, [hours]);
  return s;
}

function OpenBadge({ s, className }: { s: OpenState | null; className?: string }) {
  if (!s) return null;
  return (
    <span className={cn("inline-flex flex-wrap items-center gap-2 text-sm", className)} aria-live="polite">
      <Badge tone={s.open ? (s.soon ? "warn" : "ok") : "neutral"} className="h-6 px-2.5">
        <span aria-hidden="true" className={cn("size-1.5 rounded-full", s.open ? "bg-current" : "bg-muted")} />
        {s.open ? (s.soon ? "Closing soon" : "Open now") : "Closed now"}
      </Badge>
      <span className="text-muted">{s.line}</span>
    </span>
  );
}

function HoursTable({ hours, today }: { hours: DayHours[]; today: number | null }) {
  return (
    <table className="w-full text-left text-sm">
      <caption className="sr-only">Opening hours</caption>
      <tbody>
        {hours.map((h, i) => {
          const isToday = today === i;
          return (
            <tr key={h.day} className={cn("border-b border-line last:border-0", isToday && "font-semibold text-ink")} aria-current={isToday ? "date" : undefined}>
              <th scope="row" className={cn("py-3 pr-4 font-normal", isToday ? "font-semibold text-ink" : "text-muted")}>
                {h.day}
                {isToday ? <span className="ml-2 text-xs font-medium text-primary">Today</span> : null}
              </th>
              <td className={cn("py-3 text-right tabular-nums", h.open ? "text-ink" : "text-muted")}>{span(h)}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function mapsHref(q: string) {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(q)}`;
}

function tel(phone: string) {
  return "tel:" + phone.replace(/[^\d+]/g, "");
}

const REACH_ICON = { bus: Bus, metro: TrainFront, parking: Car } as const;
const REACH_NAME = { bus: "By bus", metro: "By metro", parking: "Parking" } as const;

function BranchPanel({ b }: { b: Branch }) {
  const s = useOpenState(b.hours);
  return (
    <div className="grid gap-8 rounded-card border border-line bg-surface p-6 sm:p-8 lg:grid-cols-2 lg:gap-12">
      <div className="min-w-0">
        <h3 className="font-head text-2xl font-semibold tracking-tight text-ink">{b.name}</h3>
        <OpenBadge s={s} className="mt-3" />
        <p className="mt-6 flex items-start gap-3 text-ink">
          <MapPin className="mt-0.5 size-5 shrink-0 text-muted" aria-hidden="true" />
          {b.address}
        </p>
        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <Button asChild>
            <a href={mapsHref(b.address)} target="_blank" rel="noreferrer" className="no-underline">
              <Navigation className="size-4" aria-hidden="true" />
              Directions
            </a>
          </Button>
          {b.phone ? (
            <Button asChild variant="secondary">
              <a href={tel(b.phone)} className="no-underline">
                <Phone className="size-4" aria-hidden="true" />
                {b.phone}
              </a>
            </Button>
          ) : null}
        </div>
      </div>
      <HoursTable hours={b.hours} today={s?.today ?? null} />
    </div>
  );
}

export default function MapHours({ variant = "card", tone, ...rest }: MapHoursProps) {
  const d = { ...sample, ...rest };
  const s = useOpenState(d.hours);

  if (variant === "branches") {
    const first = d.branches[0]?.name ?? "";
    return (
      <Section block="map_hours" variant={variant} tone={tone ?? "plain"}>
        <Container>
          <SectionHead title={d.title} intro={`${d.branches.length} places, each with its own hours.`} />
          <Tabs defaultValue={first}>
            <TabsList className="h-auto flex-wrap border border-line">
              {d.branches.map((b) => (
                <TabsTrigger key={b.name} value={b.name} className="h-10 px-5">
                  {b.name}
                </TabsTrigger>
              ))}
            </TabsList>
            {d.branches.map((b) => (
              <TabsContent key={b.name} value={b.name} className="mt-6">
                <BranchPanel b={b} />
              </TabsContent>
            ))}
          </Tabs>
          {d.holiday ? <p className="mt-6 text-sm text-muted">{d.holiday}</p> : null}
        </Container>
      </Section>
    );
  }

  if (variant === "minimal") {
    return (
      <Section block="map_hours" variant={variant} tone={tone ?? "surface"} tight>
        <Container>
          <div className="flex flex-col gap-6 border-b border-line pb-8 lg:flex-row lg:items-end lg:justify-between">
            <div className="min-w-0">
              <h2 className="font-head text-2xl font-semibold tracking-tight sm:text-3xl">{d.title}</h2>
              <p className="mt-3 text-lg text-ink">{weekLine(d.hours)}</p>
              <OpenBadge s={s} className="mt-3" />
            </div>
            <div className="flex min-w-0 flex-col gap-3 lg:items-end lg:text-right">
              <p className="text-ink">{d.address}</p>
              <a
                href={mapsHref(d.mapsQuery || d.address)}
                target="_blank"
                rel="noreferrer"
                className="inline-flex min-h-10 items-center gap-2 font-semibold text-primary underline-offset-4 hover:underline"
              >
                <Navigation className="size-4" aria-hidden="true" />
                Get directions
              </a>
            </div>
          </div>
          <ul className="mt-8 grid gap-6 sm:grid-cols-3">
            {d.reach.map((r) => {
              const Icon = REACH_ICON[r.how];
              return (
                <li key={r.how + r.text} className="flex items-start gap-3">
                  <Icon className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden="true" />
                  <div className="min-w-0">
                    <h3 className="text-sm font-semibold text-ink">{REACH_NAME[r.how]}</h3>
                    <p className="mt-1 text-sm leading-relaxed text-muted">{r.text}</p>
                  </div>
                </li>
              );
            })}
          </ul>
        </Container>
      </Section>
    );
  }

  return (
    <Section block="map_hours" variant={variant} tone={tone ?? "plain"}>
      <Container>
        <SectionHead title={d.title} intro={d.intro} />
        <div className="grid gap-8 lg:grid-cols-12 lg:gap-12">
          <a
            href={mapsHref(d.mapsQuery || d.address)}
            target="_blank"
            rel="noreferrer"
            aria-label={`Open ${d.address} in Google Maps`}
            className="group relative flex min-h-80 flex-col justify-end overflow-hidden rounded-card border border-line bg-primary/5 p-6 text-ink no-underline lg:col-span-7"
          >
            <GridPattern className="text-primary/15" size={36} />
            <span aria-hidden="true" className="absolute left-1/2 top-1/3 flex -translate-x-1/2 -translate-y-1/2 flex-col items-center">
              <span className="flex size-14 items-center justify-center rounded-full bg-primary text-primary-ink shadow-card transition-transform group-hover:-translate-y-1">
                <MapPin className="size-7" />
              </span>
              <span className="mt-2 h-2 w-6 rounded-full bg-ink/15" />
            </span>
            <span className="relative rounded-card border border-line bg-surface p-4 shadow-card">
              <span className="block font-semibold">{d.address}</span>
              <span className="mt-1 block text-sm text-muted">{d.landmark}</span>
              <span className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-primary">
                <Navigation className="size-4" aria-hidden="true" />
                Open in Google Maps
              </span>
            </span>
          </a>
          <div className="min-w-0 lg:col-span-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h3 className="font-head text-xl font-semibold text-ink">Opening hours</h3>
              <OpenBadge s={s} />
            </div>
            <div className="mt-4 border-t border-line">
              <HoursTable hours={d.hours} today={s?.today ?? null} />
            </div>
            {d.holiday ? <p className="mt-4 text-sm text-muted">{d.holiday}</p> : null}
          </div>
        </div>
      </Container>
    </Section>
  );
}
