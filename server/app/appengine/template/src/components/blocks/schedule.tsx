"use client"; // v0.999.79 D8: the day tabs need JavaScript - on a pre-rendered site page it is an island
// v0.999.79 D8 wave 3 block: Schedule - an event's programme: each day with its times and what happens. One day is a
// plain list; several days get a tab each (the first day open, every day readable without JavaScript in the HTML).
import * as React from "react";
import { MapPin } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Section, Container, SectionHead, type Tone } from "./_kit";

export const variants = ["agenda"] as const;
export type ScheduleVariant = (typeof variants)[number];

export interface ScheduleItem {
  time?: string;
  title: string;
  note?: string;
  place?: string;
}

export interface ScheduleDay {
  day: string;
  items: ScheduleItem[];
}

export interface ScheduleProps {
  variant?: ScheduleVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  days?: ScheduleDay[];
}

export const sample: Required<Omit<ScheduleProps, "variant" | "tone">> = {
  title: "The programme",
  intro: "Two days, one courtyard. Come for all of it or the part you love.",
  days: [
    { day: "Saturday 14 Dec", items: [
      { time: "5:00 pm", title: "Haldi under the mango trees", note: "Wear yellow, bring nothing." },
      { time: "8:00 pm", title: "Sangeet and dinner", place: "The lawn" },
    ] },
    { day: "Sunday 15 Dec", items: [{ time: "11:30 am", title: "The wedding", note: "Lunch follows." }] },
  ],
};

function Day({ items }: { items: ScheduleItem[] }) {
  return (
    <ol className="flex flex-col divide-y divide-line rounded-card border border-line bg-surface">
      {items.map((it, i) => (
        <li key={i} className="grid gap-1 p-5 sm:grid-cols-12 sm:gap-6 sm:p-6">
          <span className="font-medium tabular-nums text-primary sm:col-span-3">{it.time}</span>
          <div className="flex flex-col gap-1 sm:col-span-9">
            <h3 className="font-head text-lg font-semibold">{it.title}</h3>
            {it.note ? <p className="text-muted">{it.note}</p> : null}
            {it.place ? (
              <p className="inline-flex items-center gap-1.5 text-sm text-muted">
                <MapPin className="size-4" aria-hidden="true" />
                {it.place}
              </p>
            ) : null}
          </div>
        </li>
      ))}
    </ol>
  );
}

export default function Schedule({ variant = "agenda", tone, ...rest }: ScheduleProps) {
  const p = { ...sample, ...rest };
  const days = p.days.filter((d) => d.items.length);
  return (
    <Section block="schedule" variant={variant} tone={tone ?? "plain"}>
      <Container>
        <SectionHead title={p.title} intro={p.intro} />
        <div className="max-w-3xl">
          {days.length > 1 ? (
            <Tabs defaultValue="d0">
              <TabsList className="mb-6 flex-wrap">
                {days.map((d, i) => (
                  <TabsTrigger key={i} value={`d${i}`}>{d.day}</TabsTrigger>
                ))}
              </TabsList>
              {days.map((d, i) => (
                <TabsContent key={i} value={`d${i}`}>
                  <Day items={d.items} />
                </TabsContent>
              ))}
            </Tabs>
          ) : days.length ? (
            <div className="flex flex-col gap-4">
              {days[0].day ? <p className="font-medium">{days[0].day}</p> : null}
              <Day items={days[0].items} />
            </div>
          ) : null}
        </div>
      </Container>
    </Section>
  );
}
