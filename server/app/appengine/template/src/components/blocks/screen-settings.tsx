// Settings screen (signed-in portal): groups of switches and choices, saved with one clear button.
import * as React from "react";
import { Bell, Building2, ChevronRight, Lock, Users } from "lucide-react";
import { Section, Container, type Tone } from "./_kit";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { toast } from "@/components/ui/sonner";

export const variants = ["sidebar", "panels", "list"] as const;
export type ScreenSettingsVariant = (typeof variants)[number];

export type SettingValue = string | boolean;

export interface SettingField {
  id: string;
  kind: "switch" | "select" | "text";
  label: string;
  line?: string;
  options?: string[];
}

export interface SettingGroup {
  id: string;
  title: string;
  line: string;
  icon?: "business" | "alerts" | "team" | "privacy";
  fields: SettingField[];
}

export interface ScreenSettingsProps {
  variant?: ScreenSettingsVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  groups?: SettingGroup[];
  values?: Record<string, SettingValue>;
}

export const sample: Required<Omit<ScreenSettingsProps, "variant" | "tone">> = {
  title: "Settings",
  intro: "How the portal works for you and your team.",
  groups: [
    {
      id: "profile",
      title: "Business profile",
      line: "The name and details customers see",
      icon: "business",
      fields: [
        { id: "name", kind: "text", label: "Business name", line: "Shown on bills, messages and the portal." },
        { id: "city", kind: "text", label: "City", line: "Used for local times and directions." },
        { id: "language", kind: "select", label: "Language for customers", options: ["English", "Hindi", "Marathi", "Tamil", "Kannada"], line: "Messages and bills go out in this language." },
        { id: "week", kind: "select", label: "Week starts on", options: ["Monday", "Sunday"] },
      ],
    },
    {
      id: "alerts",
      title: "Notifications",
      line: "What you hear about, and how",
      icon: "alerts",
      fields: [
        { id: "n_booking", kind: "switch", label: "New bookings", line: "A WhatsApp message the moment someone books." },
        { id: "n_payment", kind: "switch", label: "Payments received", line: "Every UPI or card payment, with the amount." },
        { id: "n_review", kind: "switch", label: "Approvals waiting", line: "When a request needs your decision." },
        { id: "n_digest", kind: "select", label: "Daily summary", options: ["Off", "8:00 am", "9:00 am", "7:00 pm"], line: "One message with the day's numbers." },
      ],
    },
    {
      id: "team",
      title: "Team",
      line: "Who can sign in, and what they can do",
      icon: "team",
      fields: [
        { id: "t_anjali", kind: "select", label: "Anjali Mehta", line: "anjali@example.in", options: ["Admin", "Staff", "View only"] },
        { id: "t_vikram", kind: "select", label: "Vikram Shetty", line: "vikram@example.in", options: ["Admin", "Staff", "View only"] },
        { id: "t_farah", kind: "select", label: "Farah Khan", line: "farah@example.in", options: ["Admin", "Staff", "View only"] },
        { id: "t_approve", kind: "switch", label: "Staff can approve refunds up to ₹2,000", line: "Larger refunds still come to you." },
      ],
    },
    {
      id: "privacy",
      title: "Privacy and data",
      line: "What is public, and how long records stay",
      icon: "privacy",
      fields: [
        { id: "p_prices", kind: "switch", label: "Show prices on the public page", line: "Turn off to share prices only on request." },
        { id: "p_booking", kind: "switch", label: "Let customers book online", line: "They pick a free slot; you confirm it." },
        { id: "p_keep", kind: "select", label: "Keep closed records for", options: ["1 year", "3 years", "8 years"], line: "GST law asks for at least 6 years of bills." },
      ],
    },
  ],
  values: {
    name: "Kaveri Home Care",
    city: "Pune",
    language: "English",
    week: "Monday",
    n_booking: true,
    n_payment: true,
    n_review: true,
    n_digest: "9:00 am",
    t_anjali: "Admin",
    t_vikram: "Staff",
    t_farah: "Staff",
    t_approve: false,
    p_prices: true,
    p_booking: true,
    p_keep: "8 years",
  },
};

const ICONS = { business: Building2, alerts: Bell, team: Users, privacy: Lock };

function useSettings(groups: SettingGroup[], initial: Record<string, SettingValue>) {
  const [values, setValues] = React.useState(initial);
  const [saved, setSaved] = React.useState(initial);
  const set = (id: string, v: SettingValue) => setValues((s) => ({ ...s, [id]: v }));
  const changed = (g?: SettingGroup) =>
    (g ? g.fields : groups.flatMap((x) => x.fields)).filter((f) => values[f.id] !== saved[f.id]).length;
  function save(g?: SettingGroup) {
    const fields = g ? g.fields : groups.flatMap((x) => x.fields);
    const n = changed(g);
    setSaved((s) => {
      const next = { ...s };
      for (const f of fields) next[f.id] = values[f.id];
      return next;
    });
    toast.success(g ? `${g.title} saved` : "Settings saved", { description: n === 1 ? "1 change saved." : `${n} changes saved.` });
  }
  function reset(g?: SettingGroup) {
    const fields = g ? g.fields : groups.flatMap((x) => x.fields);
    setValues((s) => {
      const next = { ...s };
      for (const f of fields) next[f.id] = saved[f.id];
      return next;
    });
  }
  return { values, set, changed, save, reset };
}

type S = ReturnType<typeof useSettings>;

function Control({ s, f, id }: { s: S; f: SettingField; id: string }) {
  const v = s.values[f.id];
  if (f.kind === "switch") {
    return <Switch id={id} checked={v === true} onCheckedChange={(c) => s.set(f.id, c)} aria-describedby={f.line ? `${id}-line` : undefined} />;
  }
  if (f.kind === "select") {
    return (
      <Select value={typeof v === "string" ? v : ""} onValueChange={(x) => s.set(f.id, x)}>
        <SelectTrigger id={id} className="w-full sm:w-44" aria-describedby={f.line ? `${id}-line` : undefined}>
          <SelectValue placeholder="Choose" />
        </SelectTrigger>
        <SelectContent>
          {(f.options ?? []).map((o) => (
            <SelectItem key={o} value={o}>
              {o}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    );
  }
  return (
    <Input
      id={id}
      value={typeof v === "string" ? v : ""}
      onChange={(e) => s.set(f.id, e.target.value)}
      className="w-full sm:w-64"
      aria-describedby={f.line ? `${id}-line` : undefined}
    />
  );
}

function FieldRow({ s, f }: { s: S; f: SettingField }) {
  const id = React.useId();
  const inline = f.kind === "switch";
  return (
    <div className={cn("flex gap-3 py-4", inline ? "items-center justify-between" : "flex-col sm:flex-row sm:items-center sm:justify-between")}>
      <div className="min-w-0">
        <Label htmlFor={id} className="leading-snug">
          {f.label}
        </Label>
        {f.line ? (
          <p id={`${id}-line`} className="mt-1 text-sm text-muted">
            {f.line}
          </p>
        ) : null}
      </div>
      <div className="shrink-0">
        <Control s={s} f={f} id={id} />
      </div>
    </div>
  );
}

function SaveBar({ s, g, className }: { s: S; g?: SettingGroup; className?: string }) {
  const n = s.changed(g);
  return (
    <div className={cn("flex flex-wrap items-center justify-end gap-3", className)}>
      <p className="mr-auto text-sm text-muted" aria-live="polite">
        {n === 0 ? "All changes saved" : n === 1 ? "1 unsaved change" : `${n} unsaved changes`}
      </p>
      <Button variant="ghost" disabled={n === 0} onClick={() => s.reset(g)}>
        Undo
      </Button>
      <Button disabled={n === 0} onClick={() => s.save(g)}>
        Save
      </Button>
    </div>
  );
}

function Head({ title, intro, sampleShown }: { title: string; intro: string; sampleShown: boolean }) {
  return (
    <div className="mb-6 sm:mb-8">
      <div className="flex items-center gap-3">
        <h2 className="font-head text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h2>
        {sampleShown ? <Badge tone="outline">Sample</Badge> : null}
      </div>
      <p className="mt-1 text-sm text-muted">{intro}</p>
    </div>
  );
}

export default function ScreenSettings({ variant = "sidebar", tone, ...rest }: ScreenSettingsProps) {
  const d = { ...sample, ...rest };
  const sampleShown = rest.groups === undefined;
  const s = useSettings(d.groups, d.values);
  const [groupId, setGroupId] = React.useState(d.groups[0]?.id ?? "");
  const group = d.groups.find((g) => g.id === groupId) ?? d.groups[0];

  if (variant === "panels") {
    return (
      <Section block="screen_settings" variant={variant} tone={tone ?? "plain"} tight>
        <Container className="max-w-4xl">
          <Head title={d.title} intro={d.intro} sampleShown={sampleShown} />
          <div className="flex flex-col gap-6">
            {d.groups.map((g) => (
              <Card key={g.id}>
                <CardHeader>
                  <CardTitle>{g.title}</CardTitle>
                  <CardDescription>{g.line}</CardDescription>
                </CardHeader>
                <CardContent className="divide-y divide-line py-0">
                  {g.fields.map((f) => (
                    <FieldRow key={f.id} s={s} f={f} />
                  ))}
                </CardContent>
                <CardFooter className="border-t border-line pt-4">
                  <SaveBar s={s} g={g} className="w-full" />
                </CardFooter>
              </Card>
            ))}
          </div>
        </Container>
      </Section>
    );
  }

  if (variant === "list") {
    const fields = d.groups.flatMap((g) => g.fields.filter((f) => f.kind !== "text"));
    return (
      <Section block="screen_settings" variant={variant} tone={tone ?? "plain"} tight>
        <Container className="max-w-2xl">
          <Head title={d.title} intro={d.intro} sampleShown={sampleShown} />
          <Card className="px-6">
            <div className="divide-y divide-line">
              {fields.map((f) => (
                <FieldRow key={f.id} s={s} f={f} />
              ))}
            </div>
          </Card>
          <SaveBar s={s} className="sticky bottom-4 mt-4 rounded-card border border-line bg-surface p-3 shadow-card" />
        </Container>
      </Section>
    );
  }

  return (
    <Section block="screen_settings" variant={variant} tone={tone ?? "plain"} tight>
      <Container>
        <Head title={d.title} intro={d.intro} sampleShown={sampleShown} />
        <div className="grid items-start gap-6 lg:grid-cols-4">
          <nav aria-label="Setting groups" className="min-w-0 lg:sticky lg:top-6">
            <ul className="flex gap-1 overflow-x-auto pb-1 lg:flex-col lg:overflow-visible lg:pb-0">
              {d.groups.map((g) => {
                const Icon = ICONS[g.icon ?? "business"];
                const on = g.id === group?.id;
                const n = s.changed(g);
                return (
                  <li key={g.id} className="shrink-0">
                    <button
                      type="button"
                      aria-current={on ? "page" : undefined}
                      onClick={() => setGroupId(g.id)}
                      className={cn(
                        "flex h-10 w-full items-center gap-3 rounded-control px-3 text-left text-sm transition-colors focus-visible:outline-2 focus-visible:outline-primary",
                        on ? "bg-primary/10 font-medium text-primary" : "text-ink hover:bg-ink/5",
                      )}
                    >
                      <Icon className="size-4 shrink-0" aria-hidden="true" />
                      <span className="whitespace-nowrap lg:flex-1">{g.title}</span>
                      {n > 0 ? (
                        <span className="size-1.5 shrink-0 rounded-full bg-warn" aria-label={`${n} unsaved`} />
                      ) : (
                        <ChevronRight className={cn("hidden size-4 shrink-0 lg:block", on ? "" : "text-muted")} aria-hidden="true" />
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>
          </nav>
          {group ? (
            <Card key={group.id} className="min-w-0 animate-fade-in lg:col-span-3">
              <CardHeader>
                <CardTitle>{group.title}</CardTitle>
                <CardDescription>{group.line}</CardDescription>
              </CardHeader>
              <CardContent className="divide-y divide-line py-0">
                {group.fields.map((f) => (
                  <FieldRow key={f.id} s={s} f={f} />
                ))}
              </CardContent>
              <CardFooter className="border-t border-line pt-4">
                <SaveBar s={s} g={group} className="w-full" />
              </CardFooter>
            </Card>
          ) : null}
        </div>
      </Container>
    </Section>
  );
}
