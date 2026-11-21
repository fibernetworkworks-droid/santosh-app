"use client"; // v0.999.64 D3: needs JavaScript in the browser - on a pre-rendered site page it is an island
// v0.999.51 D1 block: Contact. Three layouts - phone / WhatsApp / email cards with the address, details beside a form
// that asks which service, and one big phone number with the three ways to reach. v0.999.77 D8: with `endpoint` (her
// website's own enquiry address, written by Hoola) the form really sends - it becomes her lead, with a hidden spam trap;
// without it the form only says it is received (a preview of the kit).
import * as React from "react";
import { cn } from "@/lib/utils";
import { ArrowUpRight, Clock, Mail, MapPin, MessageCircle, Phone } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Section, Container, SectionHead, type Tone } from "./_kit";

export const variants = ["form", "cards", "phone"] as const;
export type ContactBlockVariant = (typeof variants)[number];

export interface ContactBlockProps {
  variant?: ContactBlockVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  phone?: string;
  whatsapp?: string;
  email?: string;
  address?: string;
  landmark?: string;
  hours?: string;
  services?: string[];
  /** v0.999.77 D8: her website's enquiry address (written by Hoola); empty = the form only shows a note */
  endpoint?: string;
}

export const sample: Required<Omit<ContactBlockProps, "variant" | "tone">> = {
  title: "Get in touch",
  intro: "Call, message or drop by. A person answers, usually within the hour.",
  phone: "+91 98220 45117",
  whatsapp: "919822045117",
  email: "hello@example.in",
  address: "12, Shanti Complex, Ramdaspeth, Nagpur 440010",
  landmark: "Opposite the Ramdaspeth post office, first floor",
  hours: "Mon to Sat, 10 am to 8 pm · Sun, 10 am to 2 pm",
  services: ["First consultation", "Regular visit", "Home visit", "Something else"],
  endpoint: "",
};

function tel(phone: string) {
  return "tel:" + phone.replace(/[^\d+]/g, "");
}

function ContactForm({ services, endpoint = "" }: { services: string[]; endpoint?: string }) {
  const idBase = React.useId();
  const [form, setForm] = React.useState({ name: "", phone: "", service: "", message: "" });
  const [tried, setTried] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [said, setSaid] = React.useState("");
  const trap = React.useRef<HTMLInputElement>(null);
  const set = (k: keyof typeof form) => (v: string) => setForm((f) => ({ ...f, [k]: v }));
  const phoneOk = form.phone.replace(/\D/g, "").length >= 10;
  const missing = { name: !form.name.trim(), phone: !phoneOk, service: services.length > 0 && !form.service };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setTried(true);
    if (missing.name || missing.phone || missing.service) return;
    if (endpoint) {
      setBusy(true);
      setSaid("");
      try {
        const res = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: form.name.trim(),
            phone: form.phone.replace(/\D/g, "").slice(-10),
            message: [form.service, form.message.trim()].filter(Boolean).join(" - "),
            website: trap.current?.value || "",
            page: typeof location === "undefined" ? "" : location.pathname,
          }),
        });
        const out = await res.json().catch(() => ({}));
        if (!res.ok || out.ok === false) {
          setSaid(out.error || "It did not send. Please try again, or call us.");
          setBusy(false);
          return;
        }
      } catch {
        setSaid("It did not send - check your connection and try again.");
        setBusy(false);
        return;
      }
      setBusy(false);
    }
    toast.success(endpoint ? "Sent" : "Message noted", {
      description: `Thank you, ${form.name.trim()}. We will call you${form.service ? ` about "${form.service}"` : ""}.`,
    });
    setForm({ name: "", phone: "", service: "", message: "" });
    setTried(false);
  };

  const id = (k: string) => `${idBase}-${k}`;
  return (
    <form onSubmit={submit} noValidate className="grid gap-5 sm:grid-cols-2">
      <div className="flex flex-col gap-2">
        <Label htmlFor={id("name")}>Your name</Label>
        <Input id={id("name")} autoComplete="name" value={form.name} onChange={(e) => set("name")(e.target.value)} aria-invalid={tried && missing.name} />
        {tried && missing.name ? <p className="text-sm text-bad">Please add your name.</p> : null}
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor={id("phone")}>Mobile number</Label>
        <Input
          id={id("phone")}
          type="tel"
          inputMode="tel"
          autoComplete="tel"
          placeholder="10 digits"
          value={form.phone}
          onChange={(e) => set("phone")(e.target.value)}
          aria-invalid={tried && missing.phone}
        />
        {tried && missing.phone ? <p className="text-sm text-bad">A 10-digit mobile number, please.</p> : null}
      </div>
      {services.length > 0 ? (
      <div className="flex flex-col gap-2 sm:col-span-2">
        <Label htmlFor={id("service")}>What is it about?</Label>
        <Select value={form.service} onValueChange={set("service")}>
          <SelectTrigger id={id("service")} aria-invalid={tried && missing.service}>
            <SelectValue placeholder="Choose one" />
          </SelectTrigger>
          <SelectContent>
            {services.map((s) => (
              <SelectItem key={s} value={s}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {tried && missing.service ? <p className="text-sm text-bad">Pick the closest one; you can explain below.</p> : null}
      </div>
      ) : null}
      <div className="flex flex-col gap-2 sm:col-span-2">
        <Label htmlFor={id("message")}>
          Anything we should know <span className="font-normal text-muted">(optional)</span>
        </Label>
        <Textarea id={id("message")} rows={4} value={form.message} onChange={(e) => set("message")(e.target.value)} />
      </div>
      <input ref={trap} type="text" name="website" tabIndex={-1} autoComplete="off" aria-hidden="true" className="hidden" />
      <div className="flex flex-col gap-3 sm:col-span-2 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-muted" role="status">{said || "Your number is used only to reply to you."}</p>
        <Button type="submit" size="lg" disabled={busy}>
          {busy ? "Sending…" : "Send message"}
        </Button>
      </div>
    </form>
  );
}

export default function ContactBlock({ variant = "form", tone, ...rest }: ContactBlockProps) {
  const d = { ...sample, ...rest };
  const ways = [
    { icon: Phone, name: "Call", value: d.phone, href: tel(d.phone), hint: "Fastest during working hours" },
    { icon: MessageCircle, name: "WhatsApp", value: "Send a message", href: `https://wa.me/${d.whatsapp}`, hint: "Photos and voice notes welcome" },
    { icon: Mail, name: "Email", value: d.email, href: `mailto:${d.email}`, hint: "For bills and longer questions" },
    // v0.999.65 D4: a way she has not given is left out (an empty string from the writer), never a sample number
  ].filter((w) => (w.name === "WhatsApp" ? !!d.whatsapp : !!w.value));

  if (variant === "cards") {
    return (
      <Section block="contact_block" variant={variant} tone={tone ?? "plain"}>
        <Container>
          <SectionHead title={d.title} intro={d.intro} />
          <ul className={cn("grid gap-4", ways.length >= 3 ? "sm:grid-cols-3" : "sm:grid-cols-2")}>
            {ways.map((w) => (
              <li key={w.name} className="min-w-0">
                <a
                  href={w.href}
                  target={w.href.startsWith("http") ? "_blank" : undefined}
                  rel={w.href.startsWith("http") ? "noreferrer" : undefined}
                  className="group flex h-full flex-col rounded-card border border-line bg-surface p-6 text-ink no-underline transition-colors hover:border-primary/50"
                >
                  <span className="flex items-center justify-between">
                    <span className="inline-flex items-center gap-2 font-semibold">
                      <w.icon className="size-5 text-primary" aria-hidden="true" />
                      {w.name}
                    </span>
                    <ArrowUpRight className="size-4 text-muted transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" aria-hidden="true" />
                  </span>
                  <span className="mt-6 break-words font-head text-xl font-semibold tracking-tight">{w.value}</span>
                  <span className="mt-1 text-sm text-muted">{w.hint}</span>
                </a>
              </li>
            ))}
          </ul>
          <div className="mt-10 grid gap-6 border-t border-line pt-8 sm:grid-cols-2">
            <p className="flex items-start gap-3 text-ink">
              <MapPin className="mt-0.5 size-5 shrink-0 text-muted" aria-hidden="true" />
              <span>
                {d.address}
                <span className="block text-sm text-muted">{d.landmark}</span>
              </span>
            </p>
            <p className="flex items-start gap-3 text-ink">
              <Clock className="mt-0.5 size-5 shrink-0 text-muted" aria-hidden="true" />
              <span>{d.hours}</span>
            </p>
          </div>
        </Container>
      </Section>
    );
  }

  if (variant === "phone") {
    const steps = [
      { n: "1", title: "Call or message", text: "Tell us what you need in a line or two." },
      { n: "2", title: "We call back", text: "With a time that suits you and a clear price." },
      { n: "3", title: "Visit or we come", text: d.landmark },
    ];
    return (
      <Section block="contact_block" variant={variant} tone={tone ?? "surface"}>
        <Container className="max-w-4xl">
          <div className="text-center">
            <h2 className="font-head text-2xl font-semibold tracking-tight sm:text-3xl">{d.title}</h2>
            {d.phone ? <a
              href={tel(d.phone)}
              className="mt-6 inline-block break-words font-head text-4xl font-semibold tabular-nums tracking-tight text-ink no-underline transition-colors hover:text-primary sm:text-6xl"
            >
              {d.phone}
            </a> : null}
            {d.hours ? <p className="mt-4 text-muted">{d.hours}</p> : null}
            <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
              {d.phone ? <Button asChild size="lg">
                <a href={tel(d.phone)} className="no-underline">
                  <Phone className="size-5" aria-hidden="true" />
                  Call now
                </a>
              </Button> : null}
              {d.whatsapp ? <Button asChild size="lg" variant="secondary">
                <a href={`https://wa.me/${d.whatsapp}`} target="_blank" rel="noreferrer" className="no-underline">
                  <MessageCircle className="size-5" aria-hidden="true" />
                  WhatsApp us
                </a>
              </Button> : null}
            </div>
          </div>
          <ol className="mt-16 grid gap-8 border-t border-line pt-10 sm:grid-cols-3">
            {steps.map((s) => (
              <li key={s.n} className="flex gap-4">
                <span className="font-head text-3xl font-semibold leading-none text-primary">{s.n}</span>
                <div className="min-w-0">
                  <h3 className="font-semibold text-ink">{s.title}</h3>
                  <p className="mt-1 text-sm leading-relaxed text-muted">{s.text}</p>
                </div>
              </li>
            ))}
          </ol>
          <p className="mt-10 flex items-start justify-center gap-2 text-center text-sm text-muted">
            <MapPin className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            {d.address}
          </p>
        </Container>
      </Section>
    );
  }

  return (
    <Section block="contact_block" variant={variant} tone={tone ?? "plain"}>
      <Container>
        <div className="grid gap-12 lg:grid-cols-12 lg:gap-16">
          <div className="min-w-0 lg:col-span-5">
            <SectionHead title={d.title} intro={d.intro} className="mb-8 sm:mb-10" />
            <dl className="flex flex-col divide-y divide-line border-y border-line">
              {ways.map((w) => (
                <div key={w.name} className="flex items-center gap-4 py-4">
                  <w.icon className="size-5 shrink-0 text-primary" aria-hidden="true" />
                  <dt className="w-24 shrink-0 text-sm text-muted">{w.name}</dt>
                  <dd className="min-w-0">
                    <a
                      href={w.href}
                      target={w.href.startsWith("http") ? "_blank" : undefined}
                      rel={w.href.startsWith("http") ? "noreferrer" : undefined}
                      className="inline-flex min-h-10 items-center break-words font-medium text-ink underline-offset-4 hover:text-primary hover:underline"
                    >
                      {w.value}
                    </a>
                  </dd>
                </div>
              ))}
              <div className="flex items-start gap-4 py-4">
                <MapPin className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden="true" />
                <dt className="w-24 shrink-0 text-sm text-muted">Visit</dt>
                <dd className="min-w-0 text-ink">
                  {d.address}
                  <span className="mt-1 block text-sm text-muted">{d.hours}</span>
                </dd>
              </div>
            </dl>
          </div>
          <div className="min-w-0 rounded-card border border-line bg-surface p-6 shadow-card sm:p-8 lg:col-span-7">
            <h3 className="font-head text-xl font-semibold text-ink">Send us a message</h3>
            <p className="mb-6 mt-1 text-sm text-muted">We reply on the number you give, the same working day.</p>
            <ContactForm services={d.services} endpoint={d.endpoint} />
          </div>
        </div>
      </Container>
    </Section>
  );
}
