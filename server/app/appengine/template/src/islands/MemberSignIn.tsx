"use client"; // v0.999.82 D8 wave 7: the sign-in of her portal on a React website - an island
// Hoola App Engine - Hoola's own kit file. The same members as her HTML website on Hoola: sign in with email + password,
// create an account (with the privacy tick she must give), a phone code when her website has SMS set up, and the
// authenticator step for staff who turned it on. The server checks everything; this island never sees a rule.
import * as React from "react";
import { LogOut, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { signedIn, signOut, siteApp, useMember, useSchema } from "@/lib/member";

export interface MemberSignInProps {
  site: string;
  portal: string;
  purpose?: string;
  /** where a signed-in visitor goes next, e.g. ./dashboard */
  next?: string;
  help?: string;
  privacy?: string;
}

type Mode = "in" | "up" | "phone" | "code" | "twofa";
type Answer = { token?: string; need_2fa?: boolean; ticket?: string; sent?: boolean };

export default function MemberSignIn({ site, portal, purpose, next, help, privacy }: MemberSignInProps) {
  const { me, ready } = useMember(site);
  const schema = useSchema(site);
  const [mode, setMode] = React.useState<Mode>("in");
  const [f, setF] = React.useState({ name: "", email: "", password: "", phone: "", code: "", ticket: "" });
  const [consent, setConsent] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [err, setErr] = React.useState("");
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });

  const done = (a: Answer) => {
    if (a.need_2fa && a.ticket) {
      setF((x) => ({ ...x, ticket: a.ticket || "", code: "" }));
      setMode("twofa");
      return;
    }
    if (signedIn(site, a) && next) window.location.assign(next);
  };

  const go = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr("");
    if (mode === "up" && !consent) {
      setErr("To create an account, tick the privacy notice first.");
      return;
    }
    setBusy(true);
    try {
      if (mode === "in") done(await siteApp<Answer>(site, "login", "POST", { email: f.email, password: f.password }));
      else if (mode === "up")
        done(await siteApp<Answer>(site, "signup", "POST", { name: f.name, email: f.email, password: f.password, consent: true }));
      else if (mode === "phone") {
        await siteApp<Answer>(site, "otp/start", "POST", { phone: f.phone });
        setMode("code");
      } else if (mode === "code")
        done(await siteApp<Answer>(site, "otp/verify", "POST", { phone: f.phone, code: f.code, name: f.name, consent }));
      else done(await siteApp<Answer>(site, "2fa/login", "POST", { ticket: f.ticket, code: f.code }));
    } catch (x) {
      setErr((x as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (!site) return null;
  if (ready && me) {
    return (
      <Card className="mx-auto w-full max-w-md">
        <CardHeader>
          <CardTitle>Signed in</CardTitle>
          <CardDescription>{me.name || me.email || "You"} · {portal}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          {next ? <Button asChild><a href={next}>Open {portal}</a></Button> : null}
          <Button variant="outline" onClick={() => signOut(site)}>
            <LogOut className="size-4" aria-hidden="true" />
            Sign out
          </Button>
        </CardContent>
      </Card>
    );
  }
  const canSignUp = schema ? schema.signup !== false : true;
  const phone = !!schema?.security?.otp;
  const title = { in: "Sign in", up: "Create your account", phone: "Sign in with your phone", code: "Enter the code", twofa: "One more step" }[mode];
  return (
    <Card className="mx-auto w-full max-w-md">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{mode === "twofa" ? "Type the 6-digit code from your authenticator app." : purpose || portal}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={go} className="flex flex-col gap-4" noValidate>
          {mode === "up" || mode === "code" ? (
            <div className="flex flex-col gap-2">
              <Label htmlFor="ms-name">Your name</Label>
              <Input id="ms-name" value={f.name} onChange={set("name")} autoComplete="name" />
            </div>
          ) : null}
          {mode === "in" || mode === "up" ? (
            <>
              <div className="flex flex-col gap-2">
                <Label htmlFor="ms-email">Email</Label>
                <Input id="ms-email" type="email" value={f.email} onChange={set("email")} autoComplete="email" required />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="ms-pass">Password</Label>
                <Input id="ms-pass" type="password" value={f.password} onChange={set("password")}
                  autoComplete={mode === "up" ? "new-password" : "current-password"} required />
              </div>
            </>
          ) : null}
          {mode === "phone" || mode === "code" ? (
            <div className="flex flex-col gap-2">
              <Label htmlFor="ms-phone">Mobile number</Label>
              <Input id="ms-phone" type="tel" inputMode="tel" value={f.phone} onChange={set("phone")} autoComplete="tel"
                disabled={mode === "code"} />
            </div>
          ) : null}
          {mode === "code" || mode === "twofa" ? (
            <div className="flex flex-col gap-2">
              <Label htmlFor="ms-code">Code</Label>
              <Input id="ms-code" inputMode="numeric" autoComplete="one-time-code" value={f.code} onChange={set("code")} />
            </div>
          ) : null}
          {mode === "up" || mode === "code" ? (
            <label className="flex items-start gap-3 text-sm">
              <Checkbox checked={consent} onCheckedChange={(v) => setConsent(v === true)} aria-label="I agree to the privacy notice" />
              <span>
                I agree that {portal} keeps my details to run my account
                {privacy ? <> (<a href={privacy} className="underline">privacy notice</a>)</> : null}.
              </span>
            </label>
          ) : null}
          {err ? <p role="alert" className="text-sm text-bad">{err}</p> : null}
          <Button type="submit" disabled={busy}>
            {busy ? "Please wait" : mode === "up" ? "Create account" : mode === "phone" ? "Send the code" : mode === "in" ? "Sign in" : "Continue"}
          </Button>
        </form>
        <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2 text-sm">
          {mode !== "in" ? <button type="button" className="underline" onClick={() => setMode("in")}>Sign in with email</button> : null}
          {mode === "in" && canSignUp ? <button type="button" className="underline" onClick={() => setMode("up")}>New here? Create an account</button> : null}
          {phone && mode !== "phone" && mode !== "code" ? (
            <button type="button" className="underline" onClick={() => setMode("phone")}>Use a phone code</button>
          ) : null}
        </div>
        {help ? (
          <p className="mt-4 flex items-start gap-2 text-sm text-muted">
            <ShieldCheck className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            {help}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
