"use client"; // v0.999.80 D8: calculating needs JavaScript - on a pre-rendered site page it is an island
// v0.999.80 D8 wave 3 block: Tool panel - a working calculator on her page. The sums are Hoola's own, written once and
// checked (no formula comes from a model or from the page): loan EMI, GST, discount / percent, BMI, age, bill split.
// The visitor types numbers; the answer updates as they type. A tool not in this list is written specially (custom).
import * as React from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Section, Container, SectionHead, rupees, type Tone } from "./_kit";

export const variants = ["panel"] as const;
export type ToolPanelVariant = (typeof variants)[number];
export const tools = ["emi", "gst", "percent", "bmi", "age", "split"] as const;
export type ToolKind = (typeof tools)[number];

export interface ToolPanelProps {
  variant?: ToolPanelVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  tool?: ToolKind;
  note?: string;
}

export const sample: Required<Omit<ToolPanelProps, "variant" | "tone">> = {
  title: "Work out your monthly payment",
  intro: "Type the amount, the interest and the months.",
  tool: "emi",
  note: "For planning only: your bank's letter has the real number.",
};

interface Field { key: string; label: string; start: string; unit?: string }

const FIELDS: Record<ToolKind, Field[]> = {
  emi: [{ key: "p", label: "Loan amount", start: "500000", unit: "₹" }, { key: "r", label: "Interest a year", start: "9", unit: "%" },
    { key: "n", label: "Months", start: "60" }],
  gst: [{ key: "a", label: "Price before GST", start: "1000", unit: "₹" }, { key: "g", label: "GST rate", start: "18", unit: "%" }],
  percent: [{ key: "a", label: "Price", start: "2000", unit: "₹" }, { key: "d", label: "Discount", start: "15", unit: "%" }],
  bmi: [{ key: "w", label: "Weight", start: "65", unit: "kg" }, { key: "h", label: "Height", start: "165", unit: "cm" }],
  age: [{ key: "y", label: "Year of birth", start: "1990" }],
  split: [{ key: "a", label: "Bill total", start: "2400", unit: "₹" }, { key: "n", label: "People", start: "4" },
    { key: "t", label: "Tip", start: "0", unit: "%" }],
};

const r2 = (x: number) => Math.round(x * 100) / 100;
const money = (x: number) => rupees(Math.round(x));

/** The answer lines for the numbers typed - [label, value] pairs, or one line saying what is missing. */
export function answer(tool: ToolKind, v: Record<string, number>, year = new Date().getFullYear()): [string, string][] {
  const bad = Object.values(v).some((x) => !Number.isFinite(x) || x < 0);
  if (bad) return [["", "Type numbers of zero or more."]];
  if (tool === "emi") {
    const r = v.r / 1200, n = Math.round(v.n);
    if (!v.p || n < 1) return [["", "Type the amount and the months."]];
    const emi = r === 0 ? v.p / n : (v.p * r * (1 + r) ** n) / ((1 + r) ** n - 1);
    return [["Every month", money(emi)], ["Interest in all", money(emi * n - v.p)], ["You pay in all", money(emi * n)]];
  }
  if (tool === "gst") {
    const tax = (v.a * v.g) / 100;
    return [["GST", money(tax)], ["CGST + SGST (each)", money(tax / 2)], ["Price with GST", money(v.a + tax)]];
  }
  if (tool === "percent") {
    const off = (v.a * Math.min(v.d, 100)) / 100;
    return [["You save", money(off)], ["You pay", money(v.a - off)]];
  }
  if (tool === "bmi") {
    if (!v.h) return [["", "Type your height."]];
    const b = v.w / (v.h / 100) ** 2;
    const band = b < 18.5 ? "below the usual range" : b < 25 ? "in the usual range" : b < 30 ? "above the usual range" : "well above the usual range";
    return [["BMI", String(r2(b))], ["For adults this is", band]];
  }
  if (tool === "age") {
    if (!v.y || v.y > year) return [["", "Type a year that has passed."]];
    return [["Age this year", `${year - Math.round(v.y)} years`]];
  }
  const n = Math.max(Math.round(v.n), 1);
  const all = v.a * (1 + v.t / 100);
  return [["Each person pays", money(all / n)], ["Total with tip", money(all)]];
}

export default function ToolPanel({ variant = "panel", tone, ...rest }: ToolPanelProps) {
  const p = { ...sample, ...rest };
  const tool: ToolKind = (tools as readonly string[]).includes(p.tool) ? p.tool : "emi";
  const id = React.useId();
  const [vals, setVals] = React.useState<Record<string, string>>(() => Object.fromEntries(FIELDS[tool].map((f) => [f.key, f.start])));
  const nums = Object.fromEntries(Object.entries(vals).map(([k, x]) => [k, x.trim() === "" ? 0 : Number(x)]));
  const out = answer(tool, nums);
  return (
    <Section block="tool_panel" variant={variant} tone={tone ?? "surface"}>
      <Container>
        <SectionHead title={p.title} intro={p.intro} />
        <div className="grid gap-8 rounded-card border border-line bg-bg p-6 sm:p-8 md:grid-cols-2">
          <div className="flex flex-col gap-5">
            {FIELDS[tool].map((f) => (
              <div key={f.key} className="flex flex-col gap-2">
                <Label htmlFor={`${id}-${f.key}`}>{f.label}{f.unit ? ` (${f.unit})` : ""}</Label>
                <Input id={`${id}-${f.key}`} type="number" inputMode="decimal" min={0} value={vals[f.key] ?? ""}
                  onChange={(e) => setVals((s) => ({ ...s, [f.key]: e.target.value }))} />
              </div>
            ))}
          </div>
          <dl className="flex flex-col justify-center gap-4 rounded-card bg-primary/5 p-6" aria-live="polite">
            {out.map(([k, x], i) =>
              k ? (
                <div key={i} className="flex flex-col gap-1">
                  <dt className="text-sm text-muted">{k}</dt>
                  <dd className={i === 0 ? "font-head text-3xl font-semibold tabular-nums text-primary" : "text-lg font-medium tabular-nums"}>{x}</dd>
                </div>
              ) : (
                <p key={i} className="text-muted">{x}</p>
              ),
            )}
          </dl>
        </div>
        {p.note ? <p className="mt-4 text-sm text-muted">{p.note}</p> : null}
      </Container>
    </Section>
  );
}
