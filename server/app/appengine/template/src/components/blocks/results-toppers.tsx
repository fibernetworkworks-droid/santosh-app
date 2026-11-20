"use client"; // v0.999.64 D3: needs JavaScript in the browser - on a pre-rendered site page it is an island
// v0.999.51 D1 block: Results (real only). Three layouts - student cards with the top result larger, a year-wise
// results table, and one big number beside the subject toppers. Results are hers to give: while the block is showing
// the sample students it says so on the page.
import * as React from "react";
import { Award, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { NumberTicker } from "@/components/effects";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Section, Container, SectionHead, type Tone } from "./_kit";

export const variants = ["cards", "table", "spotlight"] as const;
export type ResultsToppersVariant = (typeof variants)[number];

export interface Topper {
  name: string;
  exam: string;
  year: string;
  percent?: number;
  score?: number;
  max?: number;
  rank?: string;
  subject?: string;
  photo?: string;
}

export interface ResultsToppersProps {
  variant?: ResultsToppersVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  students?: Topper[];
  headline?: { value: number; suffix?: string; label: string };
  consentNote?: string;
}

export const sample: Required<Omit<ResultsToppersProps, "variant" | "tone">> = {
  title: "Results our students earned",
  intro: "Marks as published by the boards, shared with each student's and parent's permission.",
  students: [
    { name: "Aditi Deshpande", exam: "SSC Class 10", year: "2025", percent: 98.4, score: 492, max: 500, subject: "Mathematics", rank: "Centre topper" },
    { name: "Omkar Bhosale", exam: "SSC Class 10", year: "2025", percent: 96.8, score: 484, max: 500, subject: "Science" },
    { name: "Sana Qureshi", exam: "HSC Class 12", year: "2025", percent: 95.2, score: 571, max: 600, subject: "Physics" },
    { name: "Yash Mehta", exam: "HSC Class 12", year: "2025", percent: 93.5, score: 561, max: 600, subject: "Chemistry" },
    { name: "Ishaan Jadhav", exam: "SSC Class 10", year: "2024", percent: 97.2, score: 486, max: 500, subject: "Mathematics" },
    { name: "Pooja Nair", exam: "HSC Class 12", year: "2024", percent: 94.0, score: 564, max: 600, subject: "Biology" },
  ],
  headline: { value: 38, suffix: "", label: "students scored above 90% in the 2025 board exams" },
  consentNote: "Sample results shown. Replace them with your students' real marks, shared with their permission.",
};

function initials(name: string) {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p[0] ?? "")
    .join("")
    .toUpperCase();
}

function pct(s: Topper): string {
  if (s.percent !== undefined) return `${s.percent.toFixed(1)}%`;
  if (s.score !== undefined && s.max) return `${((s.score / s.max) * 100).toFixed(1)}%`;
  return "";
}

function marks(s: Topper): string {
  return s.score !== undefined && s.max ? `${s.score} / ${s.max}` : "";
}

function Face({ s, big, inverse }: { s: Topper; big?: boolean; inverse?: boolean }) {
  const box = big ? "size-20 text-2xl" : "size-12 text-base";
  const tint = inverse ? "bg-primary-ink/15 text-primary-ink" : "bg-primary/10 text-primary";
  if (s.photo) return <img src={s.photo} alt={s.name} loading="lazy" className={cn("shrink-0 rounded-full object-cover", box)} />;
  return (
    <span role="img" aria-label={s.name} className={cn("inline-flex shrink-0 items-center justify-center rounded-full font-head font-semibold", tint, box)}>
      {initials(s.name)}
    </span>
  );
}

function SampleNote({ show, text }: { show: boolean; text: string }) {
  if (!show || !text) return null;
  return (
    <p className="mt-8 flex items-start gap-2 text-sm text-muted">
      <Info className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      {text}
    </p>
  );
}

const score = (s: Topper) => s.percent ?? (s.score !== undefined && s.max ? (s.score / s.max) * 100 : 0);

export default function ResultsToppers({ variant = "cards", tone, ...rest }: ResultsToppersProps) {
  const d = { ...sample, ...rest };
  const isSample = rest.students === undefined;
  const years = Array.from(new Set(d.students.map((s) => s.year))).sort((a, b) => b.localeCompare(a));
  const [year, setYear] = React.useState(years[0] ?? "");

  if (variant === "table") {
    const rows = d.students.filter((s) => s.year === year).sort((a, b) => score(b) - score(a));
    return (
      <Section block="results_toppers" variant={variant} tone={tone ?? "plain"}>
        <Container className="max-w-4xl">
          <SectionHead title={d.title} intro={d.intro} />
          {years.length > 1 ? (
            <div role="group" aria-label="Year" className="mb-6 flex flex-wrap gap-2">
              {years.map((y) => (
                <button
                  key={y}
                  type="button"
                  aria-pressed={y === year}
                  onClick={() => setYear(y)}
                  className={cn(
                    "inline-flex h-10 items-center rounded-full border px-5 text-sm font-semibold tabular-nums transition-colors",
                    y === year ? "border-ink bg-ink text-bg" : "border-line bg-surface text-ink hover:border-ink/40",
                  )}
                >
                  {y}
                </button>
              ))}
            </div>
          ) : null}
          <div className="overflow-x-auto rounded-card border border-line">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10 sm:w-14">#</TableHead>
                  <TableHead>Student</TableHead>
                  <TableHead className="hidden sm:table-cell">Exam</TableHead>
                  <TableHead className="hidden text-right sm:table-cell">Marks</TableHead>
                  <TableHead className="text-right">Percent</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((s, i) => (
                  <TableRow key={s.name + s.exam}>
                    <TableCell className="tabular-nums text-muted">{i + 1}</TableCell>
                    <TableCell>
                      <span className="block font-semibold text-ink">{s.name}</span>
                      <span className="block text-xs text-muted sm:hidden">{s.exam}</span>
                      {s.rank ? <span className="text-xs font-medium text-primary">{s.rank}</span> : null}
                    </TableCell>
                    <TableCell className="hidden text-ink sm:table-cell">{s.exam}</TableCell>
                    <TableCell className="hidden text-right tabular-nums text-muted sm:table-cell">{marks(s)}</TableCell>
                    <TableCell className="text-right font-head text-lg font-semibold tabular-nums text-ink">{pct(s)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <SampleNote show={isSample} text={d.consentNote} />
        </Container>
      </Section>
    );
  }

  if (variant === "spotlight") {
    const bySubject = new Map<string, Topper>();
    for (const s of d.students) {
      if (!s.subject) continue;
      const cur = bySubject.get(s.subject);
      if (!cur || score(s) > score(cur)) bySubject.set(s.subject, s);
    }
    const toppers = Array.from(bySubject.entries());
    return (
      <Section block="results_toppers" variant={variant} tone={tone ?? "surface"}>
        <Container>
          <div className="grid gap-12 lg:grid-cols-12 lg:gap-16">
            <div className="min-w-0 lg:col-span-5">
              <h2 className="font-head text-3xl font-semibold tracking-tight sm:text-4xl">{d.title}</h2>
              <p className="mt-10 font-head text-7xl font-semibold leading-none tracking-tight text-primary sm:text-8xl">
                <NumberTicker value={d.headline.value} suffix={d.headline.suffix} />
              </p>
              <p className="mt-4 max-w-sm text-lg leading-snug text-ink">{d.headline.label}</p>
              <p className="mt-6 max-w-sm text-sm text-muted">{d.intro}</p>
            </div>
            <div className="min-w-0 lg:col-span-7">
              <h3 className="font-head text-lg font-semibold text-ink">Subject toppers</h3>
              <ul className="mt-4 divide-y divide-line border-y border-line">
                {toppers.map(([subject, s]) => (
                  <li key={subject} className="grid grid-cols-1 gap-2 py-5 sm:grid-cols-12 sm:items-center sm:gap-4">
                    <p className="text-sm font-medium text-muted sm:col-span-3">{subject}</p>
                    <div className="flex min-w-0 items-center gap-3 sm:col-span-6">
                      <Face s={s} />
                      <div className="min-w-0">
                        <p className="font-semibold text-ink">{s.name}</p>
                        <p className="text-sm text-muted">
                          {s.exam}, {s.year}
                        </p>
                      </div>
                    </div>
                    <p className="font-head text-2xl font-semibold tabular-nums text-ink sm:col-span-3 sm:text-right">{pct(s)}</p>
                  </li>
                ))}
              </ul>
              <SampleNote show={isSample} text={d.consentNote} />
            </div>
          </div>
        </Container>
      </Section>
    );
  }

  const sorted = [...d.students].sort((a, b) => score(b) - score(a));
  const [top, ...rest2] = sorted;
  const cards = rest2.slice(0, 4);
  const more = rest2.slice(4);
  return (
    <Section block="results_toppers" variant={variant} tone={tone ?? "plain"}>
      <Container>
        <SectionHead title={d.title} intro={d.intro} />
        <ul className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
          {top ? (
            <li className="col-span-2 flex min-w-0 flex-col justify-between rounded-card bg-primary p-6 text-primary-ink sm:p-8 lg:row-span-2">
              <div className="flex items-center gap-4">
                <Face s={top} big inverse />
                <div className="min-w-0">
                  <h3 className="font-head text-2xl font-semibold text-primary-ink">{top.name}</h3>
                  <p className="text-primary-ink/80">
                    {top.exam}, {top.year}
                  </p>
                </div>
              </div>
              <div className="mt-10">
                <p className="font-head text-6xl font-semibold leading-none tracking-tight tabular-nums sm:text-7xl">{pct(top)}</p>
                <p className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-primary-ink/80">
                  {marks(top) ? <span>{marks(top)}</span> : null}
                  {top.rank ? (
                    <span className="inline-flex items-center gap-1.5 font-medium text-primary-ink">
                      <Award className="size-4" aria-hidden="true" />
                      {top.rank}
                    </span>
                  ) : null}
                </p>
              </div>
            </li>
          ) : null}
          {cards.map((s) => (
            <li key={s.name + s.exam} className="flex min-w-0 flex-col rounded-card border border-line bg-surface p-4 sm:p-5">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <Face s={s} />
                <div className="min-w-0">
                  <h3 className="font-semibold text-ink">{s.name}</h3>
                  <p className="text-xs text-muted">
                    {s.exam}, {s.year}
                  </p>
                </div>
              </div>
              <p className="mt-4 font-head text-2xl font-semibold tabular-nums text-ink sm:mt-5 sm:text-3xl">{pct(s)}</p>
              {s.subject ? <p className="text-sm text-muted">{s.subject}</p> : null}
            </li>
          ))}
        </ul>
        {more.length ? (
          <p className="mt-6 text-sm text-muted">
            <span className="font-medium text-ink">Also among the top results: </span>
            {more.map((s) => `${s.name} (${pct(s)}, ${s.exam} ${s.year})`).join(" · ")}
          </p>
        ) : null}
        <SampleNote show={isSample} text={d.consentNote} />
      </Container>
    </Section>
  );
}
