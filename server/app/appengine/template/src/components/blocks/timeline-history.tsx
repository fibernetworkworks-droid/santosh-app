// v0.999.51 D1 block: Timeline / schedule. Three layouts - a vertical timeline of her own dates, year chips that open
// one milestone at a time, and an event agenda with a tab per day.
import * as React from "react";
import { Clock, MapPin } from "lucide-react";
import { cn } from "@/lib/utils";
import { Reveal } from "@/components/effects";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Section, Container, SectionHead, Picture, type Tone } from "./_kit";

export const variants = ["vertical", "years", "agenda"] as const;
export type TimelineHistoryVariant = (typeof variants)[number];

export interface Milestone {
  year: string;
  title: string;
  text: string;
  photo?: string;
}

export interface AgendaSlot {
  time: string;
  title: string;
  who?: string;
  place?: string;
}

export interface AgendaDay {
  label: string;
  date: string;
  slots: AgendaSlot[];
}

export interface TimelineHistoryProps {
  variant?: TimelineHistoryVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  milestones?: Milestone[];
  days?: AgendaDay[];
  /** heading + intro for the agenda layout (a schedule reads differently from a history) */
  agendaTitle?: string;
  agendaIntro?: string;
}

export const sample: Required<Omit<TimelineHistoryProps, "variant" | "tone">> = {
  title: "How we got here",
  intro: "A few dates that matter to us, in order.",
  milestones: [
    { year: "2012", title: "A single room in Sadashiv Peth", text: "Two people, one phone line and a notebook of first customers in Pune." },
    { year: "2015", title: "The first hundred regulars", text: "Word of mouth did the work. We moved to a ground-floor space on Tilak Road." },
    { year: "2019", title: "A second branch in Kothrud", text: "Same team habits, a bigger room, and weekend hours for working families." },
    { year: "2022", title: "Orders on WhatsApp", text: "Half of our bookings now start with a message. Replies come from a person, not a bot." },
    { year: "2025", title: "Ten thousand visits", text: "We counted. Most of them were people coming back." },
  ],
  days: [
    {
      label: "Day 1",
      date: "Sat, 14 Feb",
      slots: [
        { time: "9:30 am", title: "Registration and chai", place: "Front lawn" },
        { time: "10:30 am", title: "Opening talk: what changed this year", who: "Priya Nair", place: "Main hall" },
        { time: "12:00 pm", title: "Hands-on session in small groups", who: "Rahul Verma", place: "Rooms 2 and 3" },
        { time: "1:30 pm", title: "Lunch", place: "Dining hall" },
        { time: "3:00 pm", title: "Open questions with the panel", who: "Panel of four", place: "Main hall" },
      ],
    },
    {
      label: "Day 2",
      date: "Sun, 15 Feb",
      slots: [
        { time: "10:00 am", title: "Field visit", who: "Sneha Iyer", place: "Meet at the gate" },
        { time: "1:00 pm", title: "Lunch", place: "Dining hall" },
        { time: "2:30 pm", title: "Show and tell: what each group made", place: "Main hall" },
        { time: "4:30 pm", title: "Certificates and closing", who: "Priya Nair", place: "Main hall" },
      ],
    },
  ],
  agendaTitle: "The two days, hour by hour",
  agendaIntro: "Timings may move by a few minutes; the order stays the same.",
};

export default function TimelineHistory({ variant = "vertical", tone, ...rest }: TimelineHistoryProps) {
  const d = { ...sample, ...rest };
  const [picked, setPicked] = React.useState(Math.max(0, d.milestones.length - 1));
  const panelId = React.useId();

  if (variant === "years") {
    const m = d.milestones[Math.min(picked, d.milestones.length - 1)];
    return (
      <Section block="timeline_history" variant={variant} tone={tone ?? "surface"}>
        <Container>
          <SectionHead title={d.title} intro={d.intro} />
          <div role="group" aria-label="Pick a year" className="relative flex flex-wrap gap-2 sm:flex-nowrap sm:gap-0">
            <div aria-hidden="true" className="absolute left-0 right-0 top-1/2 hidden h-px bg-line sm:block" />
            {d.milestones.map((x, i) => (
              <div key={x.year} className="relative sm:flex sm:flex-1 sm:justify-center sm:first:justify-start sm:last:justify-end">
                <button
                  type="button"
                  aria-pressed={i === picked}
                  aria-controls={panelId}
                  onClick={() => setPicked(i)}
                  className={cn(
                    "relative inline-flex h-10 items-center rounded-full border px-4 text-sm font-semibold tabular-nums transition-colors",
                    i === picked ? "border-primary bg-primary text-primary-ink" : "border-line bg-bg text-ink hover:border-primary/50",
                  )}
                >
                  {x.year}
                </button>
              </div>
            ))}
          </div>
          {m ? (
            <div id={panelId} aria-live="polite" key={m.year} className="mt-12 grid animate-fade-in items-center gap-8 lg:grid-cols-2 lg:gap-16">
              <div className="min-w-0">
                <p className="font-head text-6xl font-semibold tracking-tight text-primary sm:text-7xl">{m.year}</p>
                <h3 className="mt-4 text-2xl font-semibold text-ink">{m.title}</h3>
                <p className="mt-3 max-w-prose text-lg leading-relaxed text-muted">{m.text}</p>
              </div>
              <Picture src={m.photo} alt={`${m.year}: ${m.title}`} label={m.title} ratio="3/2" />
            </div>
          ) : null}
        </Container>
      </Section>
    );
  }

  if (variant === "agenda") {
    const first = d.days[0]?.label ?? "";
    return (
      <Section block="timeline_history" variant={variant} tone={tone ?? "plain"}>
        <Container className="max-w-4xl">
          <SectionHead title={d.agendaTitle} intro={d.agendaIntro} />
          <Tabs defaultValue={first}>
            <TabsList className="h-auto flex-wrap border border-line">
              {d.days.map((day) => (
                <TabsTrigger key={day.label} value={day.label} className="h-10 px-4">
                  <span>{day.label}</span>
                  <span className="font-normal text-muted">{day.date}</span>
                </TabsTrigger>
              ))}
            </TabsList>
            {d.days.map((day) => (
              <TabsContent key={day.label} value={day.label} className="mt-8">
                <ol className="border-t border-line">
                  {day.slots.map((s) => (
                    <li key={s.time + s.title} className="grid grid-cols-1 gap-1 border-b border-line py-5 sm:grid-cols-12 sm:gap-6">
                      <p className="inline-flex items-center gap-2 text-sm font-semibold tabular-nums text-primary sm:col-span-3 sm:text-base">
                        <Clock className="size-4" aria-hidden="true" />
                        {s.time}
                      </p>
                      <div className="min-w-0 sm:col-span-9">
                        <h3 className="text-lg font-semibold text-ink">{s.title}</h3>
                        {s.who || s.place ? (
                          <p className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted">
                            {s.who ? <span>{s.who}</span> : null}
                            {s.place ? (
                              <span className="inline-flex items-center gap-1">
                                <MapPin className="size-3.5" aria-hidden="true" />
                                {s.place}
                              </span>
                            ) : null}
                          </p>
                        ) : null}
                      </div>
                    </li>
                  ))}
                </ol>
              </TabsContent>
            ))}
          </Tabs>
        </Container>
      </Section>
    );
  }

  return (
    <Section block="timeline_history" variant={variant} tone={tone ?? "plain"}>
      <Container className="max-w-4xl">
        <SectionHead title={d.title} intro={d.intro} />
        <ol className="relative">
          <div aria-hidden="true" className="absolute bottom-2 left-1.5 top-2 w-px bg-line sm:left-30" />
          {d.milestones.map((m, i) => (
            <li key={m.year} className="relative pb-12 pl-10 last:pb-0 sm:flex sm:gap-12 sm:pl-0">
              <span
                aria-hidden="true"
                className="absolute left-0 top-2.5 size-3 rounded-full border-2 border-primary bg-bg sm:left-30 sm:-translate-x-1/2"
              />
              <p className="font-head text-2xl font-semibold tabular-nums text-primary sm:w-24 sm:shrink-0 sm:text-right sm:text-3xl">{m.year}</p>
              <Reveal delay={i * 60} className="mt-1 min-w-0 sm:mt-0">
                <h3 className="text-xl font-semibold text-ink sm:pt-1">{m.title}</h3>
                <p className="mt-2 max-w-prose leading-relaxed text-muted">{m.text}</p>
              </Reveal>
            </li>
          ))}
        </ol>
      </Container>
    </Section>
  );
}
