// Calendar screen (signed-in portal): a month, a week or today's agenda, with the chosen day's bookings.
import * as React from "react";
import { addDays, addWeeks, format, isSameDay, isToday, parseISO, startOfToday, startOfWeek } from "date-fns";
import { CalendarCheck, ChevronLeft, ChevronRight, Clock, Plus, UserRound } from "lucide-react";
import { Section, Container, type Tone } from "./_kit";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "@/components/ui/sonner";

export const variants = ["month", "agenda", "week"] as const;
export type ScreenCalendarVariant = (typeof variants)[number];

export type EventStatus = "Confirmed" | "Waiting" | "Done" | "Cancelled";

export interface CalendarEvent {
  id: string;
  /** yyyy-mm-dd */
  date: string;
  /** 24-hour "HH:mm", on the hour or half hour */
  start: string;
  minutes: number;
  title: string;
  who: string;
  status: EventStatus;
}

export interface ScreenCalendarProps {
  variant?: ScreenCalendarVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  events?: CalendarEvent[];
  /** first and last hour shown in the week view (24-hour) */
  dayStart?: number;
  dayEnd?: number;
}

const today = startOfToday();
const on = (n: number) => format(addDays(today, n), "yyyy-MM-dd");

export const sample: Required<Omit<ScreenCalendarProps, "variant" | "tone">> = {
  title: "Bookings",
  intro: "Who is coming in, and when.",
  dayStart: 9,
  dayEnd: 18,
  events: [
    { id: "b1", date: on(0), start: "09:00", minutes: 45, title: "First consultation", who: "Priya Nair", status: "Done" },
    { id: "b2", date: on(0), start: "11:00", minutes: 60, title: "Home visit, Kothrud", who: "Ananya Kulkarni", status: "Confirmed" },
    { id: "b3", date: on(0), start: "13:00", minutes: 30, title: "Follow-up call", who: "Rohit Deshmukh", status: "Waiting" },
    { id: "b4", date: on(0), start: "16:00", minutes: 60, title: "Group session", who: "6 members", status: "Confirmed" },
    { id: "b5", date: on(1), start: "10:00", minutes: 60, title: "Site measurement", who: "Mehta Stores", status: "Confirmed" },
    { id: "b6", date: on(1), start: "15:00", minutes: 45, title: "Consultation", who: "Farah Khan", status: "Waiting" },
    { id: "b7", date: on(2), start: "12:00", minutes: 30, title: "Video call", who: "Arjun Rao", status: "Confirmed" },
    { id: "b8", date: on(3), start: "09:00", minutes: 60, title: "Annual service", who: "Kaveri Foods", status: "Confirmed" },
    { id: "b9", date: on(3), start: "14:00", minutes: 60, title: "Home visit, Baner", who: "Lata Iyer", status: "Cancelled" },
    { id: "b10", date: on(5), start: "11:00", minutes: 90, title: "Workshop", who: "12 members", status: "Confirmed" },
    { id: "b11", date: on(-1), start: "10:00", minutes: 45, title: "Consultation", who: "Gurpreet Singh", status: "Done" },
    { id: "b12", date: on(-2), start: "17:00", minutes: 30, title: "Follow-up call", who: "Neha Joshi", status: "Done" },
  ],
};

const STATUS_TONE: Record<EventStatus, "ok" | "warn" | "neutral" | "bad"> = {
  Confirmed: "ok",
  Waiting: "warn",
  Done: "neutral",
  Cancelled: "bad",
};

function timeLabel(hm: string) {
  const [h, m] = hm.split(":").map(Number);
  const d = new Date(2000, 0, 1, h, m);
  return format(d, "h:mm a");
}

function endLabel(e: CalendarEvent) {
  const [h, m] = e.start.split(":").map(Number);
  return format(new Date(2000, 0, 1, h, m + e.minutes), "h:mm a");
}

function useEvents(source: CalendarEvent[]) {
  const [events, setEvents] = React.useState(source);
  function setStatus(id: string, status: EventStatus) {
    const e = events.find((x) => x.id === id);
    setEvents((list) => list.map((x) => (x.id === id ? { ...x, status } : x)));
    if (e) toast.success(`${e.who}: ${status.toLowerCase()}`, { description: `${e.title}, ${timeLabel(e.start)}` });
  }
  function hold(date: Date, hour: number) {
    const id = `new-${format(date, "yyyyMMdd")}-${hour}`;
    const start = `${String(hour).padStart(2, "0")}:00`;
    setEvents((list) => [...list, { id, date: format(date, "yyyy-MM-dd"), start, minutes: 60, title: "Held for a booking", who: "You", status: "Waiting" }]);
    toast.success("Slot held", {
      description: `${format(date, "EEE d MMM")}, ${timeLabel(start)}`,
      action: { label: "Undo", onClick: () => setEvents((list) => list.filter((x) => x.id !== id)) },
    });
  }
  const forDay = (d: Date) =>
    events.filter((e) => isSameDay(parseISO(e.date), d)).sort((a, b) => a.start.localeCompare(b.start));
  const busyDays = Array.from(new Set(events.filter((e) => e.status !== "Cancelled").map((e) => e.date))).map((s) => parseISO(s));
  return { events, setStatus, hold, forDay, busyDays };
}

type E = ReturnType<typeof useEvents>;

const DOT =
  "after:pointer-events-none after:absolute after:bottom-1 after:left-1/2 after:size-1 after:-translate-x-1/2 after:rounded-full after:bg-primary";

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

function AgendaList({ e, day, big }: { e: E; day: Date; big?: boolean }) {
  const list = e.forDay(day);
  if (list.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-card border border-dashed border-line px-6 py-10 text-center">
        <CalendarCheck className="size-6 text-muted" aria-hidden="true" />
        <p className="text-sm font-medium">Nothing booked</p>
        <p className="text-sm text-muted">The whole day is free.</p>
      </div>
    );
  }
  return (
    <ol className="flex flex-col gap-2">
      {list.map((ev) => {
        const dim = ev.status === "Cancelled" || ev.status === "Done";
        return (
          <li
            key={ev.id}
            className={cn(
              "flex flex-col gap-3 rounded-card border border-line bg-surface p-4 sm:flex-row sm:items-center",
              big ? "sm:p-5" : "",
              dim ? "opacity-70" : "",
            )}
          >
            <div className="flex shrink-0 items-baseline gap-2 sm:w-28 sm:flex-col sm:gap-0">
              <span className="font-medium tabular-nums">{timeLabel(ev.start)}</span>
              <span className="text-xs tabular-nums text-muted">to {endLabel(ev)}</span>
            </div>
            <span aria-hidden="true" className={cn("hidden h-10 w-1 shrink-0 rounded-full sm:block", ev.status === "Confirmed" ? "bg-primary" : ev.status === "Waiting" ? "bg-warn" : "bg-line")} />
            <div className="min-w-0 flex-1">
              <p className={cn("text-sm font-medium", ev.status === "Cancelled" ? "line-through" : "")}>{ev.title}</p>
              <p className="mt-0.5 flex items-center gap-1.5 text-sm text-muted">
                <UserRound className="size-3.5" aria-hidden="true" />
                {ev.who}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={STATUS_TONE[ev.status]}>{ev.status}</Badge>
              {ev.status === "Waiting" ? (
                <Button size="sm" variant="secondary" onClick={() => e.setStatus(ev.id, "Confirmed")}>
                  Confirm
                </Button>
              ) : null}
              {ev.status === "Confirmed" ? (
                <Button size="sm" variant="ghost" onClick={() => e.setStatus(ev.id, "Done")}>
                  Mark done
                </Button>
              ) : null}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

function MonthCalendar({ e, day, setDay }: { e: E; day: Date; setDay: (d: Date) => void }) {
  return (
    <Calendar
      mode="single"
      required
      selected={day}
      onSelect={(d) => d && setDay(d)}
      defaultMonth={day}
      modifiers={{ busy: e.busyDays }}
      modifiersClassNames={{ busy: DOT }}
      className="mx-auto rounded-card"
    />
  );
}

function WeekGrid({ e, from, to }: { e: E; from: number; to: number }) {
  const [week, setWeek] = React.useState(startOfWeek(today, { weekStartsOn: 1 }));
  const days = Array.from({ length: 7 }, (_, i) => addDays(week, i));
  const hours = Array.from({ length: Math.max(1, to - from) }, (_, i) => from + i);
  return (
    <Card className="min-w-0 overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3">
        <p className="font-medium">
          {format(days[0], "d MMM")} - {format(days[6], "d MMM yyyy")}
        </p>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="icon" aria-label="Previous week" onClick={() => setWeek((w) => addWeeks(w, -1))}>
            <ChevronLeft className="size-4" />
          </Button>
          <Button variant="secondary" onClick={() => setWeek(startOfWeek(today, { weekStartsOn: 1 }))}>
            This week
          </Button>
          <Button variant="secondary" size="icon" aria-label="Next week" onClick={() => setWeek((w) => addWeeks(w, 1))}>
            <ChevronRight className="size-4" />
          </Button>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-3xl table-fixed border-collapse text-sm">
          <caption className="sr-only">Week of {format(days[0], "d MMMM")}. Free slots can be held for a booking.</caption>
          <thead>
            <tr>
              <th scope="col" className="w-16 border-b border-line">
                <span className="sr-only">Time</span>
              </th>
              {days.map((d) => (
                <th key={d.toISOString()} scope="col" className="border-b border-l border-line px-2 py-2 text-center font-medium">
                  <span className="block text-xs text-muted">{format(d, "EEE")}</span>
                  <span
                    className={cn(
                      "mx-auto mt-0.5 flex size-7 items-center justify-center rounded-full tabular-nums",
                      isToday(d) ? "bg-primary text-primary-ink" : "",
                    )}
                  >
                    {format(d, "d")}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {hours.map((h) => (
              <tr key={h}>
                <th scope="row" className="border-b border-line px-2 py-1 text-right align-top text-xs font-normal tabular-nums text-muted">
                  {format(new Date(2000, 0, 1, h), "h a")}
                </th>
                {days.map((d) => {
                  const ev = e.forDay(d).find((x) => Number(x.start.split(":")[0]) === h && x.status !== "Cancelled");
                  const past = d < today;
                  return (
                    <td key={d.toISOString()} className="h-14 border-b border-l border-line p-1 align-top">
                      {ev ? (
                        <div
                          className={cn(
                            "flex h-full flex-col justify-center overflow-hidden rounded-control border-l-2 px-2 py-1",
                            ev.status === "Waiting" ? "border-warn bg-warn/10" : ev.status === "Done" ? "border-line bg-ink/5" : "border-primary bg-primary/10",
                          )}
                        >
                          <p className="truncate text-xs font-medium">{ev.who}</p>
                          <p className="truncate text-xs text-muted">{ev.title}</p>
                        </div>
                      ) : past ? null : (
                        <button
                          type="button"
                          onClick={() => e.hold(d, h)}
                          aria-label={`Hold ${format(d, "EEEE d MMMM")} at ${format(new Date(2000, 0, 1, h), "h a")}`}
                          className="group flex h-full w-full items-center justify-center rounded-control text-xs text-muted transition-colors hover:bg-primary/5 hover:text-primary focus-visible:outline-2 focus-visible:outline-primary"
                        >
                          <span className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
                            <Plus className="size-3" aria-hidden="true" />
                            Free
                          </span>
                        </button>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

export default function ScreenCalendar({ variant = "month", tone, ...rest }: ScreenCalendarProps) {
  const d = { ...sample, ...rest };
  const sampleShown = rest.events === undefined;
  const e = useEvents(d.events);
  const [day, setDay] = React.useState<Date>(today);
  const count = e.forDay(day).filter((x) => x.status !== "Cancelled").length;

  if (variant === "agenda") {
    const todays = e.forDay(today);
    const next = todays.find((x) => x.status === "Confirmed" || x.status === "Waiting");
    return (
      <Section block="screen_calendar" variant={variant} tone={tone ?? "plain"} tight>
        <Container wide>
          <Head title={`Today, ${format(today, "EEEE d MMMM")}`} intro={d.intro} sampleShown={sampleShown}>
            <Button onClick={() => toast("New booking opens here", { description: "Pick the person, the service and a free time." })}>
              <Plus className="size-4" aria-hidden="true" />
              New booking
            </Button>
          </Head>
          <div className="grid items-start gap-6 lg:grid-cols-3">
            <div className="flex min-w-0 flex-col gap-4 lg:col-span-2">
              {next ? (
                <div className="flex flex-wrap items-center gap-3 rounded-card bg-primary/10 px-4 py-3 text-sm">
                  <Clock className="size-4 text-primary" aria-hidden="true" />
                  <span>
                    Next: <span className="font-medium">{next.who}</span> at {timeLabel(next.start)}, {next.title.toLowerCase()}
                  </span>
                </div>
              ) : null}
              <AgendaList e={e} day={today} big />
            </div>
            <Card>
              <CardHeader>
                <CardTitle>Other days</CardTitle>
                <CardDescription>Days with a dot have bookings.</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-4">
                <MonthCalendar e={e} day={day} setDay={setDay} />
                {!isSameDay(day, today) ? (
                  <div className="flex flex-col gap-2 border-t border-line pt-4">
                    <p className="text-sm font-medium">{format(day, "EEEE d MMM")}</p>
                    {e.forDay(day).length === 0 ? (
                      <p className="text-sm text-muted">Nothing booked.</p>
                    ) : (
                      <ul className="flex flex-col gap-1.5">
                        {e.forDay(day).map((x) => (
                          <li key={x.id} className="flex items-center justify-between gap-3 text-sm">
                            <span className="min-w-0 truncate">
                              <span className="tabular-nums text-muted">{timeLabel(x.start)}</span> {x.who}
                            </span>
                            <Badge tone={STATUS_TONE[x.status]}>{x.status}</Badge>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                ) : null}
              </CardContent>
            </Card>
          </div>
        </Container>
      </Section>
    );
  }

  if (variant === "week") {
    return (
      <Section block="screen_calendar" variant={variant} tone={tone ?? "plain"} tight>
        <Container wide>
          <Head title={d.title} intro="Booked times are filled in. Tap a free slot to hold it for a booking." sampleShown={sampleShown}>
            <div className="flex flex-wrap items-center gap-4 text-xs text-muted">
              <span className="flex items-center gap-1.5">
                <span aria-hidden="true" className="size-2.5 rounded-full bg-primary" /> Confirmed
              </span>
              <span className="flex items-center gap-1.5">
                <span aria-hidden="true" className="size-2.5 rounded-full bg-warn" /> Waiting
              </span>
              <span className="flex items-center gap-1.5">
                <span aria-hidden="true" className="size-2.5 rounded-full bg-line" /> Done
              </span>
            </div>
          </Head>
          <div className="grid items-start gap-6 xl:grid-cols-7">
            <div className="min-w-0 xl:col-span-5">
              <WeekGrid e={e} from={d.dayStart} to={d.dayEnd} />
            </div>
            <Card className="min-w-0 xl:col-span-2">
              <CardContent className="flex flex-col gap-4 px-4 pt-4">
                <MonthCalendar e={e} day={day} setDay={setDay} />
                <div className="border-t border-line px-2 pt-4">
                  <p className="mb-3 text-sm font-medium">
                    {format(day, "EEEE d MMM")} <span className="font-normal text-muted">· {count} booked</span>
                  </p>
                  <ul className="flex flex-col gap-2">
                    {e.forDay(day).map((x) => (
                      <li key={x.id} className="flex items-center justify-between gap-3 text-sm">
                        <span className="min-w-0 truncate">
                          <span className="tabular-nums text-muted">{timeLabel(x.start)}</span> {x.who}
                        </span>
                        <Badge tone={STATUS_TONE[x.status]}>{x.status}</Badge>
                      </li>
                    ))}
                    {e.forDay(day).length === 0 ? <li className="text-sm text-muted">Nothing booked.</li> : null}
                  </ul>
                </div>
              </CardContent>
            </Card>
          </div>
        </Container>
      </Section>
    );
  }

  return (
    <Section block="screen_calendar" variant={variant} tone={tone ?? "plain"} tight>
      <Container wide>
        <Head title={d.title} intro={d.intro} sampleShown={sampleShown}>
          <Button variant="secondary" onClick={() => setDay(today)}>
            Today
          </Button>
        </Head>
        <div className="grid items-start gap-6 lg:grid-cols-5">
          <Card className="lg:col-span-2">
            <CardContent className="pt-6">
              <MonthCalendar e={e} day={day} setDay={setDay} />
              <p className="mt-4 flex items-center justify-center gap-2 text-xs text-muted">
                <span aria-hidden="true" className="size-1.5 rounded-full bg-primary" /> A dot means something is booked
              </p>
            </CardContent>
          </Card>
          <div className="min-w-0 lg:col-span-3">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="font-head text-xl font-semibold">{isToday(day) ? "Today" : format(day, "EEEE")}</h3>
                <p className="text-sm text-muted">
                  {format(day, "d MMMM yyyy")} · {count} {count === 1 ? "booking" : "bookings"}
                </p>
              </div>
              <Button
                onClick={() => toast("New booking opens here", { description: `For ${format(day, "EEE d MMM")}` })}
              >
                <Plus className="size-4" aria-hidden="true" />
                Add booking
              </Button>
            </div>
            <AgendaList e={e} day={day} />
          </div>
        </div>
      </Container>
    </Section>
  );
}
