// v0.999.51 D1 the kit: WhatsApp / call float - a round WhatsApp button in the bottom-right corner, a call +
// WhatsApp pair, or a bar fixed to the bottom of a phone screen. The wrapper section has no padding and the button
// is fixed, so the block never takes space on the page. Links go to her own number (wa.me / tel:).
import * as React from "react";
import { MessageCircle, Phone } from "lucide-react";
import { Section, type Tone } from "./_kit";
import { cn } from "@/lib/utils";

export const variants = ["round", "pair", "bar"] as const;
export type WhatsAppFloatVariant = (typeof variants)[number];

export interface WhatsAppFloatProps {
  variant?: WhatsAppFloatVariant;
  tone?: Tone;
  /** her WhatsApp number with the country code, e.g. +91 98220 41736 */
  whatsapp?: string;
  /** her phone number for calls (often the same) */
  phone?: string;
  /** the message the chat opens with */
  message?: string;
  label?: string;
  callLabel?: string;
  /** when she replies, one short line */
  hours?: string;
}

export const sample: Required<Omit<WhatsAppFloatProps, "variant" | "tone">> = {
  whatsapp: "+91 98220 41736",
  phone: "+91 98220 41736",
  message: "Hello, I saw your website and would like to know more.",
  label: "Chat on WhatsApp",
  callLabel: "Call us",
  hours: "Replies 9 am - 8 pm, Monday to Saturday",
};

function given<T extends object>(rest: T): Partial<T> {
  return Object.fromEntries(Object.entries(rest).filter(([, v]) => v !== undefined)) as Partial<T>;
}

function digits(n: string) {
  const d = n.replace(/\D/g, "");
  return d.length === 10 ? `91${d}` : d;
}

const RING = "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary";

export default function WhatsAppFloat({ variant = "round", tone, ...rest }: WhatsAppFloatProps) {
  const p = { ...sample, ...given(rest) };
  const wa = `https://wa.me/${digits(p.whatsapp)}?text=${encodeURIComponent(p.message)}`;
  const tel = `tel:+${digits(p.phone || p.whatsapp)}`;

  const round = (extra?: string) => (
    <div className={cn("group fixed bottom-5 right-5 z-40 flex items-center gap-3", extra)}>
      <span
        aria-hidden="true"
        className="pointer-events-none hidden max-w-56 rounded-card border border-line bg-surface px-3 py-2 text-ink opacity-0 shadow-card transition-opacity duration-200 group-focus-within:opacity-100 group-hover:opacity-100 sm:block"
      >
        <span className="block text-sm font-medium">{p.label}</span>
        {p.hours ? <span className="block text-xs text-muted">{p.hours}</span> : null}
      </span>
      <a
        href={wa}
        target="_blank"
        rel="noopener noreferrer"
        aria-label={p.label}
        className={cn(
          "flex size-14 shrink-0 items-center justify-center rounded-full bg-primary text-primary-ink shadow-card transition-transform duration-200 hover:-translate-y-0.5 active:translate-y-0",
          RING,
        )}
      >
        <MessageCircle className="size-6" aria-hidden="true" />
      </a>
    </div>
  );

  if (variant === "pair") {
    return (
      <Section block="whatsapp_float" variant={variant} tone={tone ?? "plain"} tight className="p-0 sm:p-0">
        <div className="fixed bottom-5 right-5 z-40 flex flex-col items-end gap-3">
          <a
            href={tel}
            aria-label={p.callLabel}
            className={cn(
              "flex h-12 items-center gap-2 rounded-full border border-line bg-surface px-3 text-ink shadow-card transition-transform duration-200 hover:-translate-y-0.5 sm:px-4",
              RING,
            )}
          >
            <Phone className="size-5" aria-hidden="true" />
            <span className="hidden text-sm font-medium sm:inline">{p.callLabel}</span>
          </a>
          <a
            href={wa}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={p.label}
            className={cn(
              "flex h-14 items-center gap-2 rounded-full bg-primary px-4 text-primary-ink shadow-card transition-transform duration-200 hover:-translate-y-0.5 sm:px-5",
              RING,
            )}
          >
            <MessageCircle className="size-6" aria-hidden="true" />
            <span className="hidden flex-col text-left leading-tight sm:flex">
              <span className="text-sm font-semibold">{p.label}</span>
              {p.hours ? <span className="text-xs opacity-80">{p.hours}</span> : null}
            </span>
          </a>
        </div>
      </Section>
    );
  }

  if (variant === "bar") {
    return (
      <Section block="whatsapp_float" variant={variant} tone={tone ?? "plain"} tight className="p-0 sm:p-0">
        <div className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-surface/95 px-4 pb-3 pt-2 text-ink shadow-card sm:hidden">
          {p.hours ? <p className="mb-2 text-center text-xs text-muted">{p.hours}</p> : null}
          <div className="grid grid-cols-2 gap-3">
            <a
              href={tel}
              className={cn(
                "flex h-12 items-center justify-center gap-2 rounded-control border border-line bg-bg text-sm font-medium text-ink transition-colors hover:bg-ink/5",
                RING,
              )}
            >
              <Phone className="size-4" aria-hidden="true" />
              {p.callLabel}
            </a>
            <a
              href={wa}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                "flex h-12 items-center justify-center gap-2 rounded-control bg-primary text-sm font-medium text-primary-ink transition-colors hover:bg-primary/90",
                RING,
              )}
            >
              <MessageCircle className="size-4" aria-hidden="true" />
              WhatsApp
            </a>
          </div>
        </div>
        {round("hidden sm:flex")}
      </Section>
    );
  }

  return (
    <Section block="whatsapp_float" variant={variant} tone={tone ?? "plain"} tight className="p-0 sm:p-0">
      {round()}
    </Section>
  );
}
