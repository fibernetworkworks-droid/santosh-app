"use client"; // v0.999.64 D3: needs JavaScript in the browser - on a pre-rendered site page it is an island
// v0.999.51 D1 block: Booking. Three layouts - the next free times as chips, pick a service then a time with a summary
// beside it, and a week strip with the chosen day's times. Nothing is booked from here: the request is noted (a toast)
// and the business confirms it, as Hoola's booking flow does.
import * as React from "react";
import { addDays, format } from "date-fns";
import { CalendarCheck, Clock } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Section, Container, SectionHead, rupees, type Tone } from "./_kit";

export const variants = ["chips", "service", "week"] as const;
export type BookingSlotsVariant = (typeof variants)[number];

export interface BookingService {
  name: string;
  minutes: number;
  price?: number;
}

/** Free times for one day: `day` = days from today (0 = today), times in 24-hour "HH:mm"; `taken` are shown but disabled. */
export interface DaySlots {
  day: number;
  times: string[];
  taken?: string[];
}

export interface BookingSlotsProps {
  variant?: BookingSlotsVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  host?: string;
  services?: BookingService[];
  slots?: DaySlots[];
  note?: string;
  /** v0.999.77 D8: her website's booking address (written by Hoola): the real free times + a request she confirms */
  endpoint?: string;
}

export const sample: Required<Omit<BookingSlotsProps, "variant" | "tone">> = {
  title: "Pick a time that suits you",
  intro: "These are the next free times. Choose one and we confirm it on WhatsApp.",
  host: "Ritu Sharma",
  services: [
    { name: "First consultation", minutes: 30, price: 500 },
    { name: "Follow-up visit", minutes: 20, price: 300 },
    { name: "Detailed session", minutes: 60, price: 1200 },
  ],
  slots: [
    { day: 0, times: ["16:30", "17:15", "18:00", "18:45"], taken: ["17:15"] },
    { day: 1, times: ["10:00", "10:45", "11:30", "12:15", "15:00", "16:30", "17:15"], taken: ["10:45", "15:00"] },
    { day: 2, times: ["10:00", "11:30", "12:15", "16:30", "18:00"] },
    { day: 3, times: ["10:45", "11:30", "15:00", "17:15", "18:45"], taken: ["11:30"] },
    { day: 4, times: ["10:00", "12:15", "16:30"] },
    { day: 5, times: ["10:00", "10:45", "11:30", "12:15"], taken: ["10:00", "10:45"] },
  ],
  note: "Confirmation comes on WhatsApp within an hour. Change or cancel any time before the visit.",
  endpoint: "",
};

function clock(t: string): string {
  const [hs, ms] = t.split(":");
  const h = Number(hs);
  const m = Number(ms);
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}${m ? `:${String(m).padStart(2, "0")}` : ""} ${h < 12 ? "am" : "pm"}`;
}

function dayName(offset: number, base: Date): string {
  if (offset === 0) return "Today";
  if (offset === 1) return "Tomorrow";
  return format(addDays(base, offset), "EEEE");
}

type Pick = { day: number; time: string } | null;

function Chip({ time, taken, on, onPick, label }: { time: string; taken?: boolean; on: boolean; onPick: () => void; label: string }) {
  return (
    <button
      type="button"
      disabled={taken}
      aria-pressed={on}
      aria-label={taken ? `${label}, already booked` : label}
      onClick={onPick}
      className={cn(
        "inline-flex h-11 min-w-24 items-center justify-center rounded-control border px-4 text-sm font-medium tabular-nums transition-colors",
        on && "border-primary bg-primary text-primary-ink",
        !on && !taken && "border-line bg-surface text-ink hover:border-primary/60 hover:text-primary",
        taken && "cursor-not-allowed border-dashed border-line bg-transparent text-muted line-through opacity-60",
      )}
    >
      {clock(time)}
    </button>
  );
}

function Confirm({ pick, base, host, service, note, onDone, className }: {
  pick: Pick;
  base: Date;
  host: string;
  service?: BookingService;
  note: string;
  onDone: () => void;
  className?: string;
}) {
  const when = pick ? `${dayName(pick.day, base)}, ${format(addDays(base, pick.day), "d MMM")} at ${clock(pick.time)}` : "";
  const send = () => {
    if (!pick) return;
    toast.success("Request noted", {
      description: `${service ? service.name + ", " : ""}${when}${host ? ` with ${host}` : ""}. We will confirm on WhatsApp.`,
    });
    onDone();
  };
  return (
    <div className={cn("flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between", className)} aria-live="polite">
      <p className="min-w-0 text-base">
        {pick ? (
          <>
            <span className="text-muted">You picked </span>
            <span className="font-semibold text-ink">{when}</span>
            {host ? <span className="text-muted"> with {host}</span> : null}
          </>
        ) : (
          <span className="text-muted">{note}</span>
        )}
      </p>
      <Button size="lg" disabled={!pick} onClick={send} className="sm:shrink-0">
        <CalendarCheck className="size-5" aria-hidden="true" />
        Request this time
      </Button>
    </div>
  );
}

/** v0.999.77 D8: her REAL free times (only free times - no names, nothing booked shown) and a request she confirms. */
function LiveBooking({ tone, title, intro, note, endpoint = "" }: BookingSlotsProps) {
  const idBase = React.useId();
  const [slots, setSlots] = React.useState<{ slot: string; label: string }[] | null>(null);
  const [pick, setPick] = React.useState("");
  const [name, setName] = React.useState("");
  const [phone, setPhone] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [said, setSaid] = React.useState("");
  const [sent, setSent] = React.useState(false);
  React.useEffect(() => {
    let live = true;
    fetch(endpoint + "/slots", { cache: "no-store" })
      .then((r) => r.json())
      .then((j) => live && setSlots(Array.isArray(j.slots) ? j.slots.slice(0, 24) : []))
      .catch(() => live && setSlots([]));
    return () => {
      live = false;
    };
  }, [endpoint]);
  const phoneOk = phone.replace(/\D/g, "").length >= 10;
  const send = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pick || !name.trim() || !phoneOk) {
      setSaid("Pick a time and add your name and a 10-digit mobile number.");
      return;
    }
    setBusy(true);
    setSaid("");
    try {
      const res = await fetch(endpoint + "/book", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slot: pick, name: name.trim(), phone: phone.replace(/\D/g, "").slice(-10), website: "" }),
      });
      const out = await res.json().catch(() => ({}));
      if (!res.ok || !out.ok) {
        setSaid(out.error || "That time could not be asked for - pick another.");
        setBusy(false);
        return;
      }
      setSent(true);
    } catch {
      setSaid("It did not send - check your connection and try again.");
    }
    setBusy(false);
  };
  const label = slots?.find((x) => x.slot === pick)?.label || "";
  return (
    <Section block="booking_slots" variant="live" tone={tone ?? "surface"}>
      <Container>
        <SectionHead title={title} intro={intro} />
        {sent ? (
          <p className="max-w-2xl text-lg" role="status">
            <span className="font-semibold text-ink">Request sent for {label}.</span>{" "}
            <span className="text-muted">The time is kept for you; you get a confirmation once it is accepted.</span>
          </p>
        ) : slots === null ? (
          <p className="text-muted">Loading the free times…</p>
        ) : slots.length === 0 ? (
          <p className="text-muted">No free times are open right now. Please call or message to book.</p>
        ) : (
          <form onSubmit={send} className="flex flex-col gap-6" noValidate>
            <div role="group" aria-label="Free times" className="flex flex-wrap gap-2">
              {slots.map((x) => (
                <button
                  key={x.slot}
                  type="button"
                  aria-pressed={x.slot === pick}
                  onClick={() => setPick(x.slot)}
                  className={cn(
                    "inline-flex h-11 items-center justify-center rounded-control border px-4 text-sm font-medium tabular-nums transition-colors",
                    x.slot === pick ? "border-primary bg-primary text-primary-ink" : "border-line bg-bg text-ink hover:border-primary/60 hover:text-primary",
                  )}
                >
                  {x.label}
                </button>
              ))}
            </div>
            <div className="grid max-w-2xl gap-4 sm:grid-cols-2">
              <div className="flex flex-col gap-2">
                <Label htmlFor={`${idBase}-n`}>Your name</Label>
                <Input id={`${idBase}-n`} autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor={`${idBase}-p`}>Mobile number</Label>
                <Input id={`${idBase}-p`} type="tel" inputMode="tel" autoComplete="tel" placeholder="10 digits" value={phone} onChange={(e) => setPhone(e.target.value)} />
              </div>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm text-muted" role="status">{said || note}</p>
              <Button size="lg" type="submit" disabled={busy || !pick} className="sm:shrink-0">
                <CalendarCheck className="size-5" aria-hidden="true" />
                {busy ? "Sending…" : "Request this time"}
              </Button>
            </div>
          </form>
        )}
      </Container>
    </Section>
  );
}

export default function BookingSlots(props: BookingSlotsProps) {
  if (props.endpoint) {
    const d = { ...sample, ...props };
    return <LiveBooking {...d} />;
  }
  return <KitBooking {...props} />;
}

function KitBooking({ variant = "chips", tone, ...rest }: BookingSlotsProps) {
  const d = { ...sample, ...rest };
  const base = React.useMemo(() => new Date(), []);
  const [pick, setPick] = React.useState<Pick>(null);
  const [svc, setSvc] = React.useState(0);
  const nowAt = base.getHours() * 60 + base.getMinutes();
  /** A time is shown but not pickable when it is booked, or already past today. */
  const isTaken = (s: DaySlots, t: string) => {
    if (s.taken?.includes(t)) return true;
    const [h, m] = t.split(":").map(Number);
    return s.day === 0 && (h ?? 0) * 60 + (m ?? 0) <= nowAt;
  };
  const firstOpen = d.slots.find((s) => s.times.some((t) => !isTaken(s, t)))?.day ?? d.slots[0]?.day ?? 0;
  const [day, setDay] = React.useState(firstOpen);
  const label = (s: DaySlots, t: string) => `${dayName(s.day, base)} ${clock(t)}`;

  if (variant === "service") {
    const service = d.services[svc];
    const soon = d.slots.filter((s) => s.times.some((t) => !isTaken(s, t))).slice(0, 3);
    return (
      <Section block="booking_slots" variant={variant} tone={tone ?? "surface"}>
        <Container>
          <SectionHead title={d.title} intro={d.intro} />
          <div className="grid gap-10 lg:grid-cols-12 lg:gap-12">
            <fieldset className="min-w-0 lg:col-span-5">
              <legend className="mb-4 font-head text-lg font-semibold text-ink">1. What do you need?</legend>
              <div className="flex flex-col gap-3">
                {d.services.map((x, i) => (
                  <button
                    key={x.name}
                    type="button"
                    aria-pressed={i === svc}
                    onClick={() => setSvc(i)}
                    className={cn(
                      "flex items-center justify-between gap-4 rounded-card border p-4 text-left transition-colors",
                      i === svc ? "border-primary bg-primary/5" : "border-line bg-bg hover:border-ink/30",
                    )}
                  >
                    <span className="min-w-0">
                      <span className="block font-semibold text-ink">{x.name}</span>
                      <span className="mt-0.5 inline-flex items-center gap-1.5 text-sm text-muted">
                        <Clock className="size-3.5" aria-hidden="true" />
                        {x.minutes} min
                      </span>
                    </span>
                    {x.price ? <span className="shrink-0 font-semibold tabular-nums text-ink">{rupees(x.price)}</span> : null}
                  </button>
                ))}
              </div>
            </fieldset>
            <fieldset className="min-w-0 lg:col-span-7">
              <legend className="mb-4 font-head text-lg font-semibold text-ink">2. When?</legend>
              <div className="flex flex-col gap-6">
                {soon.map((s) => (
                  <div key={s.day}>
                    <h3 className="mb-3 text-sm font-semibold text-ink">
                      {dayName(s.day, base)} <span className="font-normal text-muted">{format(addDays(base, s.day), "d MMM")}</span>
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {s.times.map((t) => (
                        <Chip
                          key={t}
                          time={t}
                          label={label(s, t)}
                          taken={isTaken(s, t)}
                          on={pick?.day === s.day && pick.time === t}
                          onPick={() => setPick({ day: s.day, time: t })}
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </fieldset>
          </div>
          <div className="mt-10 rounded-card border border-line bg-bg p-5 sm:p-6">
            <p className="mb-4 flex flex-wrap items-baseline gap-x-3 gap-y-1 text-sm text-muted">
              <span className="font-semibold text-ink">{service?.name}</span>
              <span>{service?.minutes} min</span>
              {service?.price ? <span>{rupees(service.price)}, paid at the visit</span> : null}
            </p>
            <Confirm pick={pick} base={base} host={d.host} service={service} note={d.note} onDone={() => setPick(null)} />
          </div>
        </Container>
      </Section>
    );
  }

  if (variant === "week") {
    const shown = d.slots.find((s) => s.day === day) ?? d.slots[0];
    return (
      <Section block="booking_slots" variant={variant} tone={tone ?? "plain"}>
        <Container className="max-w-4xl">
          <SectionHead title={d.title} intro={d.intro} />
          <div role="group" aria-label="Days" className="grid grid-cols-3 gap-2 sm:grid-cols-6">
            {d.slots.map((s) => {
              const free = s.times.filter((t) => !isTaken(s, t)).length;
              const on = s.day === day;
              const date = addDays(base, s.day);
              return (
                <button
                  key={s.day}
                  type="button"
                  aria-pressed={on}
                  onClick={() => {
                    setDay(s.day);
                    setPick(null);
                  }}
                  className={cn(
                    "flex min-w-0 flex-col items-center gap-0.5 rounded-card border px-2 py-3 transition-colors",
                    on ? "border-ink bg-ink text-bg" : "border-line bg-surface text-ink hover:border-ink/40",
                  )}
                >
                  <span className={cn("text-xs font-medium", on ? "text-bg/70" : "text-muted")}>{format(date, "EEE")}</span>
                  <span className="font-head text-2xl font-semibold tabular-nums">{format(date, "d")}</span>
                  <span className={cn("text-xs", on ? "text-bg/70" : free ? "text-ok" : "text-muted")}>{free ? `${free} free` : "Full"}</span>
                </button>
              );
            })}
          </div>
          {shown ? (
            <div key={shown.day} className="mt-8 animate-fade-in">
              <h3 className="text-base font-semibold text-ink">
                {dayName(shown.day, base)}, {format(addDays(base, shown.day), "d MMMM")}
              </h3>
              <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
                {shown.times.map((t) => (
                  <Chip
                    key={t}
                    time={t}
                    label={label(shown, t)}
                    taken={isTaken(shown, t)}
                    on={pick?.day === shown.day && pick.time === t}
                    onPick={() => setPick({ day: shown.day, time: t })}
                  />
                ))}
              </div>
            </div>
          ) : null}
          <Confirm pick={pick} base={base} host={d.host} note={d.note} onDone={() => setPick(null)} className="mt-10 border-t border-line pt-6" />
        </Container>
      </Section>
    );
  }

  const next = d.slots.filter((s) => s.times.some((t) => !isTaken(s, t))).slice(0, 2);
  return (
    <Section block="booking_slots" variant={variant} tone={tone ?? "plain"}>
      <Container>
        <div className="grid gap-10 lg:grid-cols-12 lg:gap-16">
          <SectionHead title={d.title} intro={d.intro} className="lg:col-span-5 lg:mb-0" />
          <div className="min-w-0 lg:col-span-7">
            <div className="flex flex-col gap-8">
              {next.map((s) => (
                <div key={s.day}>
                  <h3 className="mb-3 flex items-baseline gap-2 text-base font-semibold text-ink">
                    {dayName(s.day, base)}
                    <span className="text-sm font-normal text-muted">{format(addDays(base, s.day), "EEE, d MMM")}</span>
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {s.times.map((t) => (
                      <Chip
                        key={t}
                        time={t}
                        label={label(s, t)}
                        taken={isTaken(s, t)}
                        on={pick?.day === s.day && pick.time === t}
                        onPick={() => setPick({ day: s.day, time: t })}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
            <Confirm pick={pick} base={base} host={d.host} note={d.note} onDone={() => setPick(null)} className="mt-10 border-t border-line pt-6" />
          </div>
        </div>
      </Container>
    </Section>
  );
}
