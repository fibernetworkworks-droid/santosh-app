// Sign-in screen (portal front door): who is signing in, then Hoola's own sign-in. No password box is drawn here:
// Hoola handles the sign-in (phone code, Google), so the app never sees a password.
import * as React from "react";
import { ArrowLeft, ArrowRight, Briefcase, Check, ShieldCheck, UserRound, Users } from "lucide-react";
import { Section, Container, type Tone } from "./_kit";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "@/components/ui/sonner";

export const variants = ["roles", "split", "centered"] as const;
export type ScreenSigninVariant = (typeof variants)[number];

export interface SigninRole {
  id: string;
  name: string;
  line: string;
  icon?: "person" | "team" | "work";
}

export interface ScreenSigninProps {
  variant?: ScreenSigninVariant;
  tone?: Tone;
  portal?: string;
  purpose?: string;
  roles?: SigninRole[];
  /** what someone can do once inside (split variant) */
  inside?: string[];
  help?: string;
}

export const sample: Required<Omit<ScreenSigninProps, "variant" | "tone">> = {
  portal: "Kaveri Members' Portal",
  purpose: "Your bookings, bills and messages in one place.",
  roles: [
    { id: "member", name: "Member", line: "See your bookings, pay bills and message us", icon: "person" },
    { id: "staff", name: "Staff", line: "Your day's work, customers and notes", icon: "work" },
    { id: "admin", name: "Owner or manager", line: "Reports, approvals, team and settings", icon: "team" },
  ],
  inside: [
    "Book, move or cancel a visit in a few taps",
    "Pay bills by UPI and download GST invoices",
    "Message the team and get replies on WhatsApp",
    "See every past visit and its report",
  ],
  help: "Trouble signing in? Call +91 20 4012 3300, 9 am to 7 pm.",
};

const ICONS = { person: UserRound, team: Users, work: Briefcase };

function startSignin(portal: string, role?: SigninRole) {
  toast("Hoola's sign-in opens next", {
    description: role ? `Signing in to ${portal} as ${role.name.toLowerCase()}.` : `Signing in to ${portal}.`,
  });
}

function HoolaBox({ portal, role, onBack, compact }: { portal: string; role?: SigninRole; onBack?: () => void; compact?: boolean }) {
  return (
    <div className="flex flex-col gap-5">
      <div className={cn("flex items-start gap-3 rounded-control bg-primary/5 p-4", compact ? "p-3" : "")}>
        <ShieldCheck className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden="true" />
        <p className="text-sm">
          Sign-in is handled by <span className="font-medium">Hoola</span>. You get a one-time code on your phone or use your
          Google account. This portal never sees or stores a password.
        </p>
      </div>
      {role ? (
        <p className="flex items-center gap-2 text-sm text-muted">
          <Check className="size-4 text-ok" aria-hidden="true" />
          Signing in as <span className="font-medium text-ink">{role.name}</span>
        </p>
      ) : null}
      <Button size="lg" className="w-full" onClick={() => startSignin(portal, role)}>
        Continue
        <ArrowRight className="size-4" aria-hidden="true" />
      </Button>
      {onBack ? (
        <Button variant="ghost" className="self-center" onClick={onBack}>
          <ArrowLeft className="size-4" aria-hidden="true" />
          Choose a different role
        </Button>
      ) : null}
    </div>
  );
}

function RoleCards({ roles, picked, onPick }: { roles: SigninRole[]; picked?: string; onPick: (r: SigninRole) => void }) {
  return (
    <div role="radiogroup" aria-label="Who are you?" className="grid gap-3 sm:grid-cols-3">
      {roles.map((r) => {
        const Icon = ICONS[r.icon ?? "person"];
        const on = picked === r.id;
        return (
          <button
            key={r.id}
            type="button"
            role="radio"
            aria-checked={on}
            onClick={() => onPick(r)}
            className={cn(
              "flex flex-col items-start gap-3 rounded-card border bg-surface p-5 text-left transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
              on ? "border-primary ring-2 ring-primary/20" : "border-line hover:border-ink/25",
            )}
          >
            <span className="flex w-full items-center justify-between">
              <Icon className="size-5 text-primary" aria-hidden="true" />
              <span
                aria-hidden="true"
                className={cn(
                  "flex size-5 items-center justify-center rounded-full border transition-colors",
                  on ? "border-primary bg-primary text-primary-ink" : "border-line",
                )}
              >
                {on ? <Check className="size-3" /> : null}
              </span>
            </span>
            <span className="font-head text-lg font-semibold">{r.name}</span>
            <span className="text-sm text-muted">{r.line}</span>
          </button>
        );
      })}
    </div>
  );
}

export default function ScreenSignin({ variant = "roles", tone, ...rest }: ScreenSigninProps) {
  const d = { ...sample, ...rest };
  const sampleShown = rest.portal === undefined;
  const [role, setRole] = React.useState<SigninRole | undefined>(undefined);
  const [step, setStep] = React.useState<"pick" | "signin">("pick");

  if (variant === "split") {
    return (
      <Section block="screen_signin" variant={variant} tone={tone ?? "plain"} tight>
        <Container>
          <div className="grid overflow-hidden rounded-card border border-line bg-surface shadow-card lg:grid-cols-2">
            <div className="flex flex-col gap-8 bg-primary p-8 text-primary-ink sm:p-12">
              <div>
                <div className="flex flex-wrap items-center gap-3">
                  <h2 className="font-head text-3xl font-semibold tracking-tight text-primary-ink sm:text-4xl">{d.portal}</h2>
                  {sampleShown ? <Badge className="border border-primary-ink/30 bg-transparent text-primary-ink">Sample</Badge> : null}
                </div>
                <p className="mt-3 text-primary-ink/80">{d.purpose}</p>
              </div>
              <ul className="flex flex-col gap-4">
                {d.inside.map((line) => (
                  <li key={line} className="flex items-start gap-3">
                    <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-primary-ink/15">
                      <Check className="size-3" aria-hidden="true" />
                    </span>
                    <span>{line}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="flex flex-col justify-center gap-6 p-8 sm:p-12">
              <div>
                <h3 className="font-head text-2xl font-semibold">Sign in</h3>
                <p className="mt-1 text-sm text-muted">Pick who you are, then continue.</p>
              </div>
              <div role="radiogroup" aria-label="Who are you?" className="flex flex-col gap-2">
                {d.roles.map((r) => {
                  const on = role?.id === r.id;
                  return (
                    <button
                      key={r.id}
                      type="button"
                      role="radio"
                      aria-checked={on}
                      onClick={() => setRole(r)}
                      className={cn(
                        "flex items-center gap-3 rounded-control border px-4 py-3 text-left transition-colors focus-visible:outline-2 focus-visible:outline-primary",
                        on ? "border-primary bg-primary/5" : "border-line hover:bg-ink/5",
                      )}
                    >
                      <span
                        aria-hidden="true"
                        className={cn("flex size-4 shrink-0 items-center justify-center rounded-full border", on ? "border-primary" : "border-line")}
                      >
                        {on ? <span className="size-2 rounded-full bg-primary" /> : null}
                      </span>
                      <span className="min-w-0">
                        <span className="block text-sm font-medium">{r.name}</span>
                        <span className="block text-xs text-muted">{r.line}</span>
                      </span>
                    </button>
                  );
                })}
              </div>
              <HoolaBox portal={d.portal} role={role} compact />
              <p className="text-center text-xs text-muted">{d.help}</p>
            </div>
          </div>
        </Container>
      </Section>
    );
  }

  if (variant === "centered") {
    return (
      <Section block="screen_signin" variant={variant} tone={tone ?? "surface"}>
        <Container>
          <Card className="mx-auto max-w-md animate-fade-up">
            <CardHeader className="items-center gap-3 pt-8 text-center">
              <span className="flex size-12 items-center justify-center rounded-card bg-primary font-head text-lg font-semibold text-primary-ink" aria-hidden="true">
                {d.portal.trim().charAt(0).toUpperCase()}
              </span>
              <div className="flex flex-wrap items-center justify-center gap-2">
                <h2 className="font-head text-2xl font-semibold tracking-tight">{d.portal}</h2>
                {sampleShown ? <Badge tone="outline">Sample</Badge> : null}
              </div>
              <CardDescription>{d.purpose}</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-5 pb-8">
              <HoolaBox portal={d.portal} />
              <p className="text-center text-xs text-muted">{d.help}</p>
            </CardContent>
          </Card>
        </Container>
      </Section>
    );
  }

  return (
    <Section block="screen_signin" variant={variant} tone={tone ?? "plain"}>
      <Container>
        <div className="mx-auto max-w-3xl">
          <div className="mb-8 text-center">
            <div className="flex flex-wrap items-center justify-center gap-3">
              <h2 className="font-head text-3xl font-semibold tracking-tight sm:text-4xl">
                {step === "pick" ? "Who is signing in?" : `Welcome to ${d.portal}`}
              </h2>
              {sampleShown ? <Badge tone="outline">Sample</Badge> : null}
            </div>
            <p className="mt-2 text-muted">{step === "pick" ? d.purpose : "One more step and you are in."}</p>
          </div>
          {step === "pick" ? (
            <div className="flex flex-col gap-6">
              <RoleCards roles={d.roles} picked={role?.id} onPick={setRole} />
              <div className="flex flex-col items-center gap-3">
                <Button size="lg" disabled={!role} onClick={() => setStep("signin")} className="w-full sm:w-auto">
                  Next
                  <ArrowRight className="size-4" aria-hidden="true" />
                </Button>
                <p className="text-xs text-muted">{d.help}</p>
              </div>
            </div>
          ) : (
            <Card className="mx-auto max-w-md animate-fade-in">
              <CardHeader>
                <CardTitle>Sign in with Hoola</CardTitle>
                <CardDescription>{role?.line}</CardDescription>
              </CardHeader>
              <CardContent>
                <HoolaBox portal={d.portal} role={role} onBack={() => setStep("pick")} />
              </CardContent>
            </Card>
          )}
        </div>
      </Container>
    </Section>
  );
}
