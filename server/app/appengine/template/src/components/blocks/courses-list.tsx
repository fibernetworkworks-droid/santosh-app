"use client"; // v0.999.64 D3: needs JavaScript in the browser - on a pre-rendered site page it is an island
// v0.999.51 D1 block: Courses. Three layouts - a tab per class / group with course cards, a table of batches with an
// online / classroom filter, and one featured course with its syllabus beside the rest. "Book a demo" notes the
// request (a toast); fees show only when she gives them.
import * as React from "react";
import { CalendarDays, Clock, MonitorPlay, Users } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Section, Container, SectionHead, rupees, type Tone } from "./_kit";

export const variants = ["tabs", "table", "featured"] as const;
export type CoursesListVariant = (typeof variants)[number];

export type CourseMode = "Online" | "Classroom" | "Both";

export interface Course {
  name: string;
  group: string;
  line?: string;
  duration: string;
  batch: string;
  starts: string;
  mode: CourseMode;
  fee?: number;
  seats?: number;
  faculty?: string;
  outline?: string[];
}

export interface CoursesListProps {
  variant?: CoursesListVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  courses?: Course[];
  demoLabel?: string;
}

export const sample: Required<Omit<CoursesListProps, "variant" | "tone">> = {
  title: "Courses and batches",
  intro: "Small batches, fixed timings, and a free demo class before you join.",
  courses: [
    {
      name: "Class 10 Maths and Science",
      group: "Class 9 – 10",
      line: "Full syllabus with weekly tests and a doubt hour every Saturday.",
      duration: "10 months",
      batch: "Mon, Wed, Fri · 5 – 7 pm",
      starts: "2 June",
      mode: "Classroom",
      fee: 24000,
      seats: 6,
      faculty: "Sunil Kulkarni",
    },
    {
      name: "Class 9 Foundation",
      group: "Class 9 – 10",
      line: "Builds the base for board years: algebra, geometry and physics basics.",
      duration: "10 months",
      batch: "Tue, Thu · 5 – 7 pm",
      starts: "3 June",
      mode: "Both",
      fee: 18000,
      seats: 11,
    },
    {
      name: "Class 12 Physics",
      group: "Class 11 – 12",
      line: "Board and entrance questions side by side, chapter by chapter.",
      duration: "11 months",
      batch: "Mon to Fri · 7 – 8:30 am",
      starts: "15 April",
      mode: "Classroom",
      fee: 32000,
      seats: 4,
      faculty: "Dr. Anjali Pawar",
    },
    {
      name: "Class 11 Chemistry",
      group: "Class 11 – 12",
      line: "Organic made readable, with a printed notes set for every chapter.",
      duration: "11 months",
      batch: "Sat, Sun · 9 am – 12 pm",
      starts: "20 April",
      mode: "Online",
      seats: 20,
    },
    {
      name: "JEE Main crash course",
      group: "Entrance",
      line: "Ninety days, two full mock tests a week, and a review of every mistake.",
      duration: "3 months",
      batch: "Daily · 4 – 7 pm",
      starts: "5 January",
      mode: "Both",
      fee: 28000,
      seats: 9,
      faculty: "Rohit Agarwal",
      outline: [
        "Mechanics and the questions that repeat every year",
        "Electrostatics, current and magnetism",
        "Organic chemistry reactions, one map at a time",
        "Calculus and coordinate geometry drills",
        "Two full mocks a week with a mistake review",
      ],
    },
  ],
  demoLabel: "Book a free demo",
};

const MODE_TONE: Record<CourseMode, "primary" | "accent" | "outline"> = { Online: "accent", Classroom: "outline", Both: "primary" };

function fee(c: Course) {
  return c.fee ? rupees(c.fee) : "Fees on request";
}

function demo(c: Course) {
  toast.success("Demo request noted", { description: `${c.name}: we will call you with the next demo class time.` });
}

function Meta({ c }: { c: Course }) {
  return (
    <ul className="flex flex-col gap-2 text-sm text-muted">
      <li className="flex items-center gap-2">
        <Clock className="size-4 shrink-0" aria-hidden="true" />
        <span className="text-ink">{c.batch}</span>
      </li>
      <li className="flex items-center gap-2">
        <CalendarDays className="size-4 shrink-0" aria-hidden="true" />
        Starts {c.starts} · {c.duration}
      </li>
      {c.seats !== undefined ? (
        <li className="flex items-center gap-2">
          <Users className="size-4 shrink-0" aria-hidden="true" />
          <span className={cn(c.seats <= 5 && "font-medium text-warn")}>{c.seats} seats left</span>
        </li>
      ) : null}
    </ul>
  );
}

export default function CoursesList({ variant = "tabs", tone, ...rest }: CoursesListProps) {
  const d = { ...sample, ...rest };
  const groups = Array.from(new Set(d.courses.map((c) => c.group)));
  const [mode, setMode] = React.useState<"All" | "Online" | "Classroom">("All");

  if (variant === "table") {
    const rows = d.courses.filter((c) => mode === "All" || c.mode === mode || c.mode === "Both");
    return (
      <Section block="courses_list" variant={variant} tone={tone ?? "plain"}>
        <Container>
          <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
            <SectionHead title={d.title} intro={d.intro} className="mb-0 sm:mb-0" />
            <div role="group" aria-label="How you attend" className="inline-flex w-fit rounded-control border border-line bg-surface p-1">
              {(["All", "Online", "Classroom"] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  aria-pressed={mode === m}
                  onClick={() => setMode(m)}
                  className={cn(
                    "inline-flex h-10 items-center rounded-control px-4 text-sm font-medium transition-colors",
                    mode === m ? "bg-ink text-bg" : "text-muted hover:text-ink",
                  )}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>
          <ul className="mt-8 divide-y divide-line border-y border-line md:hidden">
            {rows.map((c) => (
              <li key={c.name} className="flex flex-col gap-2 py-5">
                <div className="flex items-start justify-between gap-3">
                  <p className="min-w-0 font-semibold text-ink">{c.name}</p>
                  <p className="shrink-0 text-sm font-medium tabular-nums text-ink">{fee(c)}</p>
                </div>
                <p className="text-sm text-ink">{c.batch}</p>
                <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted">
                  <Badge tone={MODE_TONE[c.mode]}>{c.mode === "Both" ? "Online + classroom" : c.mode}</Badge>
                  <span>Starts {c.starts}</span>
                  {c.seats !== undefined ? <span className={cn(c.seats <= 5 && "font-semibold text-warn")}>{c.seats} seats left</span> : null}
                </p>
              </li>
            ))}
          </ul>
          <div className="mt-10 hidden overflow-x-auto rounded-card border border-line md:block">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Course</TableHead>
                  <TableHead>Timing</TableHead>
                  <TableHead>Starts</TableHead>
                  <TableHead>Mode</TableHead>
                  <TableHead className="text-right">Seats</TableHead>
                  <TableHead className="text-right">Fee</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((c) => (
                  <TableRow key={c.name}>
                    <TableCell>
                      <span className="block font-semibold text-ink">{c.name}</span>
                      <span className="text-xs text-muted">
                        {c.group} · {c.duration}
                      </span>
                    </TableCell>
                    <TableCell className="text-ink">{c.batch}</TableCell>
                    <TableCell className="whitespace-nowrap text-ink">{c.starts}</TableCell>
                    <TableCell>
                      <Badge tone={MODE_TONE[c.mode]}>{c.mode === "Both" ? "Online + classroom" : c.mode}</Badge>
                    </TableCell>
                    <TableCell className={cn("text-right tabular-nums", c.seats !== undefined && c.seats <= 5 ? "font-semibold text-warn" : "text-ink")}>
                      {c.seats ?? "–"}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-right tabular-nums text-ink">{fee(c)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <p className="mt-4 text-sm text-muted" aria-live="polite">
            {rows.length} of {d.courses.length} batches shown. Highlighted seat counts are nearly full.
          </p>
        </Container>
      </Section>
    );
  }

  if (variant === "featured") {
    const lead = d.courses.find((c) => c.outline?.length) ?? d.courses[0];
    const others = d.courses.filter((c) => c !== lead);
    return (
      <Section block="courses_list" variant={variant} tone={tone ?? "surface"}>
        <Container>
          <SectionHead title={d.title} intro={d.intro} />
          <div className="grid gap-12 lg:grid-cols-12 lg:gap-16">
            {lead ? (
              <article className="min-w-0 lg:col-span-7">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={MODE_TONE[lead.mode]}>{lead.mode === "Both" ? "Online + classroom" : lead.mode}</Badge>
                  <span className="text-sm text-muted">{lead.group}</span>
                </div>
                <h3 className="mt-4 font-head text-3xl font-semibold tracking-tight text-ink sm:text-4xl">{lead.name}</h3>
                {lead.line ? <p className="mt-3 max-w-prose text-lg leading-relaxed text-muted">{lead.line}</p> : null}
                {lead.outline?.length ? (
                  <ol className="relative mt-8 flex flex-col gap-5 border-l border-line pl-6">
                    {lead.outline.map((o, i) => (
                      <li key={o} className="relative">
                        <span aria-hidden="true" className="absolute -left-7.5 top-1.5 size-3 rounded-full border-2 border-primary bg-surface" />
                        <span className="text-sm font-semibold tabular-nums text-primary">Part {i + 1}</span>
                        <p className="text-ink">{o}</p>
                      </li>
                    ))}
                  </ol>
                ) : null}
                <div className="mt-8 grid gap-6 border-t border-line pt-6 sm:grid-cols-2">
                  <Meta c={lead} />
                  <div className="flex flex-col gap-3 sm:items-end">
                    <p className="font-head text-2xl font-semibold tabular-nums text-ink">{fee(lead)}</p>
                    {lead.faculty ? <p className="text-sm text-muted">Taught by {lead.faculty}</p> : null}
                    <Button size="lg" onClick={() => demo(lead)}>
                      <MonitorPlay className="size-5" aria-hidden="true" />
                      {d.demoLabel}
                    </Button>
                  </div>
                </div>
              </article>
            ) : null}
            <div className="min-w-0 lg:col-span-5">
              <h3 className="font-head text-lg font-semibold text-ink">Other courses</h3>
              <ul className="mt-4 divide-y divide-line border-y border-line">
                {others.map((c) => (
                  <li key={c.name} className="flex items-start justify-between gap-4 py-4">
                    <div className="min-w-0">
                      <p className="font-semibold text-ink">{c.name}</p>
                      <p className="mt-0.5 text-sm text-muted">
                        {c.batch} · {c.duration}
                      </p>
                    </div>
                    <p className="shrink-0 text-right text-sm font-medium tabular-nums text-ink">{fee(c)}</p>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </Container>
      </Section>
    );
  }

  return (
    <Section block="courses_list" variant={variant} tone={tone ?? "plain"}>
      <Container>
        <SectionHead title={d.title} intro={d.intro} />
        <Tabs defaultValue={groups[0] ?? ""}>
          <TabsList className="h-auto flex-wrap border border-line">
            {groups.map((g) => (
              <TabsTrigger key={g} value={g} className="h-10 px-4">
                {g}
                <span className="font-normal text-muted">{d.courses.filter((c) => c.group === g).length}</span>
              </TabsTrigger>
            ))}
          </TabsList>
          {groups.map((g) => (
            <TabsContent key={g} value={g} className="mt-8">
              <ul className="grid gap-6 md:grid-cols-2">
                {d.courses
                  .filter((c) => c.group === g)
                  .map((c) => (
                    <li key={c.name} className="flex min-w-0 flex-col rounded-card border border-line bg-surface p-6 transition-shadow hover:shadow-card">
                      <div className="flex items-start justify-between gap-4">
                        <h3 className="min-w-0 font-head text-xl font-semibold tracking-tight text-ink">{c.name}</h3>
                        <Badge tone={MODE_TONE[c.mode]}>{c.mode === "Both" ? "Online + classroom" : c.mode}</Badge>
                      </div>
                      {c.line ? <p className="mt-2 leading-relaxed text-muted">{c.line}</p> : null}
                      <div className="mt-5">
                        <Meta c={c} />
                      </div>
                      <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-5">
                        <p className="font-semibold tabular-nums text-ink">{fee(c)}</p>
                        <Button variant="outline" onClick={() => demo(c)}>
                          {d.demoLabel}
                        </Button>
                      </div>
                    </li>
                  ))}
              </ul>
            </TabsContent>
          ))}
        </Tabs>
      </Container>
    </Section>
  );
}
