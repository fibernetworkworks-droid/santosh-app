"use client"; // v0.999.82 D8: answering needs JavaScript - on a pre-rendered site page it is an island
// v0.999.82 D8 wave 3 block: Quiz - her questions, one at a time, each with its choices; the visitor picks, sees right
// or wrong with her explanation, and gets a score at the end. Only questions where SHE marked the right answer are
// used (Hoola never decides what is right). Nothing is stored or sent: it is for the visitor.
import * as React from "react";
import { Check, RotateCcw, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import { Section, Container, SectionHead, type Tone } from "./_kit";

export const variants = ["one-by-one"] as const;
export type QuizVariant = (typeof variants)[number];

export interface QuizQuestion {
  q: string;
  options: string[];
  answer: number;
  why?: string;
}

export interface QuizProps {
  variant?: QuizVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  questions?: QuizQuestion[];
}

export const sample: Required<Omit<QuizProps, "variant" | "tone">> = {
  title: "Test yourself",
  intro: "Three quick questions on what we covered this week.",
  questions: [
    { q: "Which colour do you get by mixing blue and yellow?", options: ["Green", "Purple", "Orange"], answer: 0 },
    { q: "Which paper soaks up water best?", options: ["Printer paper", "Cotton paper"], answer: 1, why: "Cotton holds water without curling." },
  ],
};

export default function Quiz({ variant = "one-by-one", tone, ...rest }: QuizProps) {
  const p = { ...sample, ...rest };
  const qs = p.questions.filter((x) => x.options.length >= 2 && x.answer >= 0 && x.answer < x.options.length);
  const [at, setAt] = React.useState(0);
  const [picked, setPicked] = React.useState<number | null>(null);
  const [score, setScore] = React.useState(0);
  const done = at >= qs.length;
  const cur = qs[at];
  const pick = (i: number) => {
    if (picked !== null) return;
    setPicked(i);
    if (i === cur.answer) setScore((s) => s + 1);
  };
  const next = () => { setAt((a) => a + 1); setPicked(null); };
  const again = () => { setAt(0); setPicked(null); setScore(0); };
  return (
    <Section block="quiz" variant={variant} tone={tone ?? "surface"}>
      <Container>
        <div className="mx-auto max-w-2xl">
          <SectionHead title={p.title} intro={p.intro} align="center" />
          <div className="flex flex-col gap-6 rounded-card border border-line bg-bg p-6 sm:p-8" aria-live="polite">
            <Progress value={qs.length ? (Math.min(at, qs.length) / qs.length) * 100 : 0} aria-label="Questions answered" />
            {done ? (
              <div className="flex flex-col items-center gap-4 py-6 text-center">
                <p className="font-head text-4xl font-semibold tabular-nums">{score} / {qs.length}</p>
                <p className="text-muted">{score === qs.length ? "All right - well done." : "Have another go, or read the lesson again."}</p>
                <Button variant="secondary" onClick={again}><RotateCcw className="size-4" aria-hidden="true" />Start again</Button>
              </div>
            ) : (
              <>
                <p className="text-sm tabular-nums text-muted">Question {at + 1} of {qs.length}</p>
                <h3 className="text-balance font-head text-xl font-semibold">{cur.q}</h3>
                <ul className="flex flex-col gap-3">
                  {cur.options.map((o, i) => {
                    const right = picked !== null && i === cur.answer;
                    const wrong = picked === i && i !== cur.answer;
                    return (
                      <li key={i}>
                        <button type="button" onClick={() => pick(i)} disabled={picked !== null}
                          className={cn("flex w-full items-center gap-3 rounded-control border border-line bg-surface px-4 py-3 text-left transition-colors hover:border-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:cursor-default",
                            right && "border-ok bg-ok/10", wrong && "border-bad bg-bad/10")}>
                          <span className="flex-1">{o}</span>
                          {right ? <Check className="size-5 text-ok" aria-label="Right answer" /> : null}
                          {wrong ? <X className="size-5 text-bad" aria-label="Not this one" /> : null}
                        </button>
                      </li>
                    );
                  })}
                </ul>
                {picked !== null ? (
                  <div className="flex flex-col gap-4">
                    <p className={picked === cur.answer ? "text-ok" : "text-bad"}>
                      {picked === cur.answer ? "Right." : `The answer is: ${cur.options[cur.answer]}.`}{cur.why ? ` ${cur.why}` : ""}
                    </p>
                    <Button onClick={next} className="w-fit">{at + 1 < qs.length ? "Next question" : "See my score"}</Button>
                  </div>
                ) : null}
              </>
            )}
          </div>
        </div>
      </Container>
    </Section>
  );
}
