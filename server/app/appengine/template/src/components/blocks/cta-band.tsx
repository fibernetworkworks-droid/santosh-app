// v0.999.51 D1 block: Call to action band. Three layouts - a full-width colour band with one button, a split with call
// and WhatsApp buttons beside the line, and an inline name + phone form that asks for a call back.
import * as React from "react";
import { ArrowRight, MessageCircle, Phone } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { DotPattern } from "@/components/effects";
import { Section, Container, type Tone } from "./_kit";

export const variants = ["band", "split", "inline"] as const;
export type CtaBandVariant = (typeof variants)[number];

export interface CtaBandProps {
  variant?: CtaBandVariant;
  tone?: Tone;
  title?: string;
  text?: string;
  action?: { label: string; href: string };
  phone?: string;
  whatsapp?: string;
  note?: string;
}

export const sample: Required<Omit<CtaBandProps, "variant" | "tone">> = {
  title: "Tell us what you need. We reply the same day.",
  text: "A short message is enough. We will call back with a plan and a price, and nothing starts until you say yes.",
  action: { label: "Book a visit", href: "#booking" },
  phone: "+91 98220 45117",
  whatsapp: "919822045117",
  note: "Mon to Sat, 10 am to 8 pm",
};

/** Text colours that read on each tone (the band is usually a colour field, so plain text-muted would vanish). */
const INK: Record<Tone, { head: string; soft: string; line: string }> = {
  plain: { head: "text-ink", soft: "text-muted", line: "border-line" },
  surface: { head: "text-ink", soft: "text-muted", line: "border-line" },
  primary: { head: "text-primary-ink", soft: "text-primary-ink/80", line: "border-primary-ink/25" },
  ink: { head: "text-bg", soft: "text-bg/70", line: "border-bg/20" },
};

function tel(phone: string) {
  return "tel:" + phone.replace(/[^\d+]/g, "");
}

export default function CtaBand({ variant = "band", tone, ...rest }: CtaBandProps) {
  const d = { ...sample, ...rest };
  const t: Tone = tone ?? (variant === "band" ? "primary" : variant === "split" ? "ink" : "surface");
  const c = INK[t];
  const onColour = t === "primary" || t === "ink";
  const [name, setName] = React.useState("");
  const [phone, setPhone] = React.useState("");
  const [tried, setTried] = React.useState(false);
  const uid = React.useId();
  const phoneOk = phone.replace(/\D/g, "").length >= 10;

  if (variant === "split") {
    return (
      <Section block="cta_band" variant={variant} tone={t} tight>
        <Container>
          <div className="grid items-center gap-8 lg:grid-cols-12">
            <div className="min-w-0 lg:col-span-7">
              <h2 className={cn("font-head text-3xl font-semibold tracking-tight sm:text-4xl", c.head)}>{d.title}</h2>
              <p className={cn("mt-4 max-w-xl text-lg leading-relaxed", c.soft)}>{d.text}</p>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row lg:col-span-5 lg:justify-end">
              <Button asChild size="lg" variant={onColour ? "accent" : "primary"}>
                <a href={tel(d.phone)} className="no-underline">
                  <Phone className="size-5" aria-hidden="true" />
                  Call {d.phone}
                </a>
              </Button>
              <Button asChild size="lg" variant="outline" className={cn(onColour && cn("bg-transparent hover:bg-bg/10", c.head, c.line))}>
                <a href={`https://wa.me/${d.whatsapp}`} target="_blank" rel="noreferrer" className="no-underline">
                  <MessageCircle className="size-5" aria-hidden="true" />
                  WhatsApp
                </a>
              </Button>
            </div>
          </div>
          {d.note ? <p className={cn("mt-8 border-t pt-6 text-sm", c.soft, c.line)}>{d.note}</p> : null}
        </Container>
      </Section>
    );
  }

  if (variant === "inline") {
    const submit = (e: React.FormEvent) => {
      e.preventDefault();
      setTried(true);
      if (!name.trim() || !phoneOk) return;
      toast.success("Request noted", { description: `We will call ${name.trim()} on ${phone.trim()} soon.` });
      setName("");
      setPhone("");
      setTried(false);
    };
    return (
      <Section block="cta_band" variant={variant} tone={t} tight>
        <Container>
          <div className="grid gap-8 lg:grid-cols-12 lg:items-end">
            <div className="min-w-0 lg:col-span-5">
              <h2 className={cn("font-head text-3xl font-semibold tracking-tight", c.head)}>{d.title}</h2>
              <p className={cn("mt-3 leading-relaxed", c.soft)}>{d.text}</p>
            </div>
            <form onSubmit={submit} noValidate className="grid min-w-0 gap-4 sm:grid-cols-12 sm:items-end lg:col-span-7">
              <div className="flex flex-col gap-2 sm:col-span-5">
                <Label htmlFor={`${uid}-name`} className={c.head}>
                  Your name
                </Label>
                <Input
                  id={`${uid}-name`}
                  autoComplete="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  aria-invalid={tried && !name.trim()}
                  className="h-12"
                />
              </div>
              <div className="flex flex-col gap-2 sm:col-span-4">
                <Label htmlFor={`${uid}-phone`} className={c.head}>
                  Phone
                </Label>
                <Input
                  id={`${uid}-phone`}
                  type="tel"
                  inputMode="tel"
                  autoComplete="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  aria-invalid={tried && !phoneOk}
                  aria-describedby={`${uid}-help`}
                  className="h-12"
                />
              </div>
              <Button type="submit" size="lg" variant={onColour ? "accent" : "primary"} className="sm:col-span-3">
                Call me back
              </Button>
              <p id={`${uid}-help`} className={cn("text-sm sm:col-span-12", tried && !phoneOk ? "text-bad" : c.soft)}>
                {tried && !name.trim() ? "Please add your name. " : ""}
                {tried && !phoneOk ? "A 10-digit mobile number, please." : "We only use your number to call you about this."}
              </p>
            </form>
          </div>
        </Container>
      </Section>
    );
  }

  return (
    <Section block="cta_band" variant={variant} tone={t} className="overflow-hidden">
      <DotPattern className={cn("opacity-40", onColour ? "text-primary-ink/30" : "text-line")} gap={22} />
      <Container className="relative max-w-4xl text-center">
        <h2 className={cn("font-head text-4xl font-semibold tracking-tight sm:text-5xl", c.head)}>{d.title}</h2>
        <p className={cn("mx-auto mt-5 max-w-2xl text-lg leading-relaxed", c.soft)}>{d.text}</p>
        <div className="mt-10 flex flex-col items-center gap-4">
          <Button asChild size="xl" variant={onColour ? "secondary" : "primary"}>
            <a href={d.action.href} className="no-underline">
              {d.action.label}
              <ArrowRight className="size-5" aria-hidden="true" />
            </a>
          </Button>
          <p className={cn("text-sm", c.soft)}>
            Or call{" "}
            <a href={tel(d.phone)} className={cn("font-semibold underline underline-offset-4", c.head)}>
              {d.phone}
            </a>
            {d.note ? ` · ${d.note}` : ""}
          </p>
        </div>
      </Container>
    </Section>
  );
}
