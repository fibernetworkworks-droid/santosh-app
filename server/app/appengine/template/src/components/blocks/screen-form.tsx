// Form screen (signed-in portal): labelled fields, help text, checks as she types, a clear submit.
import * as React from "react";
import { useForm, type UseFormReturn } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { format, startOfToday } from "date-fns";
import { ArrowLeft, ArrowRight, Check, CircleCheck } from "lucide-react";
import { Section, Container, type Tone } from "./_kit";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { DatePicker } from "@/components/ui/date-picker";
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/sonner";

export const variants = ["steps", "panels", "short"] as const;
export type ScreenFormVariant = (typeof variants)[number];

export interface ScreenFormProps {
  variant?: ScreenFormVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  /** the choices in the "What do you need?" box */
  services?: string[];
  submitLabel?: string;
  successTitle?: string;
  successLine?: string;
}

export const sample: Required<Omit<ScreenFormProps, "variant" | "tone">> = {
  title: "New request",
  intro: "Tell us what you need. It takes about a minute.",
  services: ["Home visit", "Consultation at the centre", "Video call", "Follow-up check", "Something else"],
  submitLabel: "Send request",
  successTitle: "Request sent",
  successLine: "We will confirm the time on WhatsApp within a few hours.",
};

const schema = z.object({
  name: z.string().trim().min(2, "Write your full name"),
  phone: z
    .string()
    .trim()
    .refine((v) => /^[6-9]\d{9}$/.test(v.replace(/[\s-]/g, "")), "A 10-digit mobile number, like 98765 43210"),
  email: z
    .string()
    .trim()
    .refine((v) => v === "" || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v), "That email does not look right"),
  service: z.string().min(1, "Choose one"),
  date: z.date({ error: "Pick a day" }).refine((d) => d >= startOfToday(), "Choose today or a later day"),
  city: z.string().trim().min(2, "Which city are you in?"),
  notes: z.string().max(400, "Keep it under 400 characters"),
  consent: z.boolean().refine((v) => v, "Tick this so we can reply to you"),
});

type Values = z.infer<typeof schema>;
type F = UseFormReturn<Values>;

const empty: Partial<Values> = { name: "", phone: "", email: "", service: "", city: "", notes: "", consent: false };

const STEPS: { title: string; line: string; fields: (keyof Values)[] }[] = [
  { title: "About you", line: "So we know who to reply to", fields: ["name", "phone", "email"] },
  { title: "What you need", line: "The service, the day and where", fields: ["service", "date", "city"] },
  { title: "Confirm", line: "Anything else, then send", fields: ["notes", "consent"] },
];

function useRequestForm() {
  return useForm<Values>({ resolver: zodResolver(schema), mode: "onTouched", defaultValues: empty });
}

function NameField({ form }: { form: F }) {
  return (
    <FormField
      control={form.control}
      name="name"
      render={({ field }) => (
        <FormItem>
          <FormLabel>Full name</FormLabel>
          <FormControl>
            <Input autoComplete="name" placeholder="Meera Kulkarni" {...field} />
          </FormControl>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

function PhoneField({ form }: { form: F }) {
  return (
    <FormField
      control={form.control}
      name="phone"
      render={({ field }) => (
        <FormItem>
          <FormLabel>Mobile number</FormLabel>
          <FormControl>
            <Input type="tel" inputMode="numeric" autoComplete="tel-national" placeholder="98765 43210" {...field} />
          </FormControl>
          <FormDescription>We send the confirmation here on WhatsApp.</FormDescription>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

function EmailField({ form }: { form: F }) {
  return (
    <FormField
      control={form.control}
      name="email"
      render={({ field }) => (
        <FormItem>
          <FormLabel>
            Email <span className="font-normal text-muted">(optional)</span>
          </FormLabel>
          <FormControl>
            <Input type="email" autoComplete="email" placeholder="meera@example.in" {...field} />
          </FormControl>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

function ServiceField({ form, services }: { form: F; services: string[] }) {
  return (
    <FormField
      control={form.control}
      name="service"
      render={({ field }) => (
        <FormItem>
          <FormLabel>What do you need?</FormLabel>
          <Select value={field.value} onValueChange={(v) => field.onChange(v)}>
            <FormControl>
              <SelectTrigger onBlur={field.onBlur}>
                <SelectValue placeholder="Choose a service" />
              </SelectTrigger>
            </FormControl>
            <SelectContent>
              {services.map((s) => (
                <SelectItem key={s} value={s}>
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

function DateField({ form }: { form: F }) {
  return (
    <FormField
      control={form.control}
      name="date"
      render={({ field }) => (
        <FormItem>
          <FormLabel>Preferred day</FormLabel>
          <FormControl>
            <DatePicker value={field.value} onChange={(d) => field.onChange(d)} placeholder="Pick a day" />
          </FormControl>
          <FormDescription>We will offer the nearest free time on that day.</FormDescription>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

function CityField({ form }: { form: F }) {
  return (
    <FormField
      control={form.control}
      name="city"
      render={({ field }) => (
        <FormItem>
          <FormLabel>City</FormLabel>
          <FormControl>
            <Input autoComplete="address-level2" placeholder="Pune" {...field} />
          </FormControl>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

function NotesField({ form }: { form: F }) {
  const n = form.watch("notes")?.length ?? 0;
  return (
    <FormField
      control={form.control}
      name="notes"
      render={({ field }) => (
        <FormItem>
          <FormLabel>
            Anything we should know? <span className="font-normal text-muted">(optional)</span>
          </FormLabel>
          <FormControl>
            <Textarea rows={4} placeholder="Gate code, a preferred time, who will be there..." {...field} />
          </FormControl>
          <div className="flex items-start justify-between gap-3">
            <FormMessage />
            <span className={cn("ml-auto text-xs tabular-nums", n > 400 ? "text-bad" : "text-muted")}>{n}/400</span>
          </div>
        </FormItem>
      )}
    />
  );
}

function ConsentField({ form }: { form: F }) {
  return (
    <FormField
      control={form.control}
      name="consent"
      render={({ field }) => (
        <FormItem>
          <div className="flex items-start gap-3">
            <FormControl>
              <Checkbox className="mt-0.5" checked={field.value} onCheckedChange={(c) => field.onChange(c === true)} />
            </FormControl>
            <div className="flex flex-col gap-1">
              <FormLabel className="font-normal leading-snug">You may contact me on WhatsApp or a call about this request.</FormLabel>
              <FormMessage />
            </div>
          </div>
        </FormItem>
      )}
    />
  );
}

function Head({ title, intro, sampleShown, children }: { title: string; intro: string; sampleShown: boolean; children?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:mb-8 sm:flex-row sm:items-end sm:justify-between">
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

function Done({ title, line, values, onAgain }: { title: string; line: string; values: Values | null; onAgain: () => void }) {
  return (
    <div className="flex flex-col items-center gap-4 px-6 py-12 text-center animate-fade-up" role="status">
      <span className="flex size-12 items-center justify-center rounded-full bg-ok/10 text-ok">
        <CircleCheck className="size-6" aria-hidden="true" />
      </span>
      <h3 className="font-head text-xl font-semibold">{title}</h3>
      <p className="max-w-sm text-sm text-muted">{line}</p>
      {values ? (
        <p className="text-sm">
          {values.service} on <span className="font-medium">{format(values.date, "EEE, d MMM")}</span> in {values.city}
        </p>
      ) : null}
      <Button variant="secondary" onClick={onAgain}>
        Send another request
      </Button>
    </div>
  );
}

function useSubmit(form: F, title: string, line: string) {
  const [sent, setSent] = React.useState<Values | null>(null);
  const submit = form.handleSubmit((v) => {
    setSent(v);
    toast.success(title, { description: line });
  });
  const again = () => {
    form.reset(empty);
    setSent(null);
  };
  return { sent, submit, again };
}

function Summary({ form }: { form: F }) {
  const v = form.watch();
  const rows: [string, string][] = [
    ["Name", v.name || "-"],
    ["Mobile", v.phone || "-"],
    ["Service", v.service || "-"],
    ["Day", v.date ? format(v.date, "EEE, d MMM yyyy") : "-"],
    ["City", v.city || "-"],
  ];
  return (
    <dl className="flex flex-col gap-3 text-sm">
      {rows.map(([k, val]) => (
        <div key={k} className="flex items-baseline justify-between gap-4">
          <dt className="text-muted">{k}</dt>
          <dd className={cn("min-w-0 truncate text-right", val === "-" ? "text-muted" : "font-medium")}>{val}</dd>
        </div>
      ))}
    </dl>
  );
}

function StepsForm({ d, sampleShown }: { d: Required<Omit<ScreenFormProps, "variant" | "tone">>; sampleShown: boolean }) {
  const form = useRequestForm();
  const { sent, submit, again } = useSubmit(form, d.successTitle, d.successLine);
  const [step, setStep] = React.useState(0);

  async function next() {
    const ok = await form.trigger(STEPS[step].fields);
    if (ok) setStep((s) => Math.min(STEPS.length - 1, s + 1));
  }

  return (
    <div className="mx-auto max-w-3xl">
      <Head title={d.title} intro={d.intro} sampleShown={sampleShown} />
      <ol className="mb-6 grid grid-cols-3 gap-2" aria-label="Steps">
        {STEPS.map((s, n) => {
          const state = sent || n < step ? "done" : n === step ? "now" : "next";
          return (
            <li key={s.title} aria-current={state === "now" ? "step" : undefined} className="flex flex-col gap-2">
              <span className={cn("h-1 rounded-full transition-colors", state === "next" ? "bg-line" : "bg-primary")} />
              <span className="flex items-center gap-2 text-sm">
                <span
                  className={cn(
                    "flex size-5 shrink-0 items-center justify-center rounded-full text-xs font-medium",
                    state === "done" ? "bg-primary text-primary-ink" : state === "now" ? "border border-primary text-primary" : "border border-line text-muted",
                  )}
                >
                  {state === "done" ? <Check className="size-3" aria-hidden="true" /> : n + 1}
                </span>
                <span className={cn("truncate", state === "next" ? "text-muted" : "font-medium")}>{s.title}</span>
              </span>
              <span className="hidden text-xs text-muted sm:block">{s.line}</span>
            </li>
          );
        })}
      </ol>
      <Card>
        {sent ? (
          <Done title={d.successTitle} line={d.successLine} values={sent} onAgain={() => {
                again();
                setStep(0);
              }} />
        ) : (
          <Form {...form}>
            <form onSubmit={submit} noValidate>
              <CardHeader>
                <CardTitle>{STEPS[step].title}</CardTitle>
                <CardDescription>
                  Step {step + 1} of {STEPS.length}
                </CardDescription>
              </CardHeader>
              <CardContent key={step} className="flex flex-col gap-5 animate-fade-in">
                {step === 0 ? (
                  <>
                    <NameField form={form} />
                    <div className="grid gap-5 sm:grid-cols-2">
                      <PhoneField form={form} />
                      <EmailField form={form} />
                    </div>
                  </>
                ) : step === 1 ? (
                  <>
                    <ServiceField form={form} services={d.services} />
                    <div className="grid gap-5 sm:grid-cols-2">
                      <DateField form={form} />
                      <CityField form={form} />
                    </div>
                  </>
                ) : (
                  <>
                    <div className="rounded-control bg-bg p-4">
                      <Summary form={form} />
                    </div>
                    <NotesField form={form} />
                    <ConsentField form={form} />
                  </>
                )}
              </CardContent>
              <div className="flex items-center justify-between gap-3 border-t border-line px-6 py-4">
                <Button type="button" variant="ghost" disabled={step === 0} onClick={() => setStep((s) => s - 1)}>
                  <ArrowLeft className="size-4" aria-hidden="true" />
                  Back
                </Button>
                {step < STEPS.length - 1 ? (
                  <Button type="button" onClick={next}>
                    Continue
                    <ArrowRight className="size-4" aria-hidden="true" />
                  </Button>
                ) : (
                  <Button type="submit" disabled={form.formState.isSubmitting}>
                    {d.submitLabel}
                  </Button>
                )}
              </div>
            </form>
          </Form>
        )}
      </Card>
    </div>
  );
}

function PanelsForm({ d, sampleShown }: { d: Required<Omit<ScreenFormProps, "variant" | "tone">>; sampleShown: boolean }) {
  const form = useRequestForm();
  const { sent, submit, again } = useSubmit(form, d.successTitle, d.successLine);
  const errors = Object.keys(form.formState.errors).length;
  return (
    <>
      <Head title={d.title} intro={d.intro} sampleShown={sampleShown} />
      <Form {...form}>
        <form onSubmit={submit} noValidate className="grid items-start gap-6 lg:grid-cols-3">
          <div className="flex min-w-0 flex-col gap-6 lg:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle>About you</CardTitle>
                <CardDescription>So we know who to reply to.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-5 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <NameField form={form} />
                </div>
                <PhoneField form={form} />
                <EmailField form={form} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>What you need</CardTitle>
                <CardDescription>The service, the day and where.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-5 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <ServiceField form={form} services={d.services} />
                </div>
                <DateField form={form} />
                <CityField form={form} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Anything else</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-5">
                <NotesField form={form} />
                <ConsentField form={form} />
              </CardContent>
            </Card>
          </div>
          <Card className="lg:sticky lg:top-6">
            {sent ? (
              <Done title={d.successTitle} line={d.successLine} values={sent} onAgain={again} />
            ) : (
              <>
                <CardHeader>
                  <CardTitle>Summary</CardTitle>
                  <CardDescription>Fills in as you type.</CardDescription>
                </CardHeader>
                <CardContent className="flex flex-col gap-5">
                  <Summary form={form} />
                  <Separator />
                  {errors > 0 ? (
                    <p className="text-sm text-bad" role="alert">
                      {errors === 1 ? "One field needs a look." : `${errors} fields need a look.`}
                    </p>
                  ) : (
                    <p className="text-sm text-muted">Nothing is booked until we confirm with you.</p>
                  )}
                  <Button type="submit" size="lg" className="w-full">
                    {d.submitLabel}
                  </Button>
                </CardContent>
              </>
            )}
          </Card>
        </form>
      </Form>
    </>
  );
}

function ShortForm({ d, sampleShown }: { d: Required<Omit<ScreenFormProps, "variant" | "tone">>; sampleShown: boolean }) {
  const form = useRequestForm();
  const { sent, submit, again } = useSubmit(form, d.successTitle, d.successLine);
  return (
    <div className="mx-auto max-w-xl">
      <Card>
        {sent ? (
          <Done title={d.successTitle} line={d.successLine} values={sent} onAgain={again} />
        ) : (
          <>
            <CardHeader>
              <div className="flex items-center gap-3">
                <h2 className="font-head text-2xl font-semibold tracking-tight">{d.title}</h2>
                {sampleShown ? <Badge tone="outline">Sample</Badge> : null}
              </div>
              <CardDescription>{d.intro}</CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...form}>
                <form onSubmit={submit} noValidate className="flex flex-col gap-5">
                  <NameField form={form} />
                  <PhoneField form={form} />
                  <ServiceField form={form} services={d.services} />
                  <div className="grid gap-5 sm:grid-cols-2">
                    <DateField form={form} />
                    <CityField form={form} />
                  </div>
                  <ConsentField form={form} />
                  <Button type="submit" size="lg" className="w-full">
                    {d.submitLabel}
                  </Button>
                  <p className="text-center text-xs text-muted">Fields are checked as you go. Nothing is booked until we confirm.</p>
                </form>
              </Form>
            </CardContent>
          </>
        )}
      </Card>
    </div>
  );
}

export default function ScreenForm({ variant = "steps", tone, ...rest }: ScreenFormProps) {
  const d = { ...sample, ...rest };
  const sampleShown = rest.services === undefined;
  return (
    <Section block="screen_form" variant={variant} tone={tone ?? "plain"} tight>
      <Container>
        {variant === "panels" ? <PanelsForm d={d} sampleShown={sampleShown} /> : variant === "short" ? <ShortForm d={d} sampleShown={sampleShown} /> : <StepsForm d={d} sampleShown={sampleShown} />}
      </Container>
    </Section>
  );
}
