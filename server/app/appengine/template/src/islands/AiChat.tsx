"use client"; // v0.999.103 D8 wave 10: her AI assistant on a React website - an island
// Hoola App Engine - Hoola's own kit file. Her own Hoola AI App (built and published in AI Apps) answers her visitors
// here: the same answers, notice, limits and monthly cost ceiling as its chat page, all checked on Hoola's server. The
// visitor agrees to the notice first (their tap); nothing is asked of them before that. Under Hoola's address (the
// sealed Studio preview) it is not called, so no visitor's words spend her credits there.
import * as React from "react";
import { Bot, Send, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { AppError, aiAgree, aiAgreed, aiApp, aiSealed } from "@/lib/member";

type FormField = { key: string; label?: string; type?: string; options?: string[]; required?: boolean };

export interface AiChatProps {
  code: string;
  name?: string;
  opening?: string;
  notice?: string;
  kind?: string;
  suggested?: string[];
}

type Info = { name?: string; kind?: string; opening?: string; suggested?: string[]; notice?: string; form?: FormField[] };
type Turn = { id: string; q: string; a: string };
type State = "loading" | "sealed" | "off" | "notice" | "chat";

const SAID: Record<string, string> = {
  sealed: "Your assistant answers on your website's own address, not in this preview.",
  off: "The assistant is not answering right now. Please contact us another way.",
};

export default function AiChat({ code, name, opening, notice, kind, suggested }: AiChatProps) {
  const [st, setSt] = React.useState<State>("loading");
  const [info, setInfo] = React.useState<Info>({ name, opening, notice, kind, suggested });
  const [turns, setTurns] = React.useState<Turn[]>([]);
  const [text, setText] = React.useState("");
  const [vals, setVals] = React.useState<Record<string, string>>({});
  const [busy, setBusy] = React.useState(false);
  const [err, setErr] = React.useState("");
  const idBase = React.useId();
  const end = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!code) return;
    if (aiSealed()) {
      setSt("sealed");
      return;
    }
    aiApp<Info>(code)
      .then((i) => {
        setInfo((o) => ({ ...o, ...i }));
        if (!aiAgreed(code)) {
          setSt("notice");
          return;
        }
        setSt("chat");
        aiApp<{ messages?: { id: string; q: string; a: string }[] }>(code, "history")
          .then((h) => setTurns((h.messages || []).map((m) => ({ id: m.id, q: m.q, a: m.a }))))
          .catch((e) => {
            if (e instanceof AppError && e.status === 401) setSt("notice");
          });
      })
      .catch(() => setSt("off"));
  }, [code]);

  React.useEffect(() => {                          // a block body: scrollIntoView may return a Promise, never a cleanup
    end.current?.scrollIntoView({ block: "end" });
  }, [turns.length]);

  async function agree() {
    setBusy(true);
    setErr("");
    try {
      await aiAgree(code);
      setSt("chat");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "That did not work. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  const isForm = info.kind === "form" && (info.form || []).length > 0;

  async function send(q: string) {
    const ask = q.trim();
    if (busy || (!ask && !isForm)) return;
    setBusy(true);
    setErr("");
    try {
      const out = await aiApp<{ reply?: string; message_id?: string }>(code, "chat", "POST",
        isForm ? { text: ask, inputs: vals } : { text: ask });
      setTurns((t) => [...t, { id: out.message_id || String(t.length), q: ask, a: out.reply || "" }]);
      setText("");
    } catch (e) {
      if (e instanceof AppError && e.status === 401) setSt("notice");
      setErr(e instanceof Error ? e.message : "That did not work. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  const title = info.name || "Ask our assistant";
  return (
    <section className="px-4 py-16" data-hoola-ai={st}>
      <Card className="mx-auto w-full max-w-2xl">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Bot className="size-5 text-primary" aria-hidden="true" />
            <CardTitle id={`${idBase}-h`}>{title}</CardTitle>
            <Badge variant="secondary" className="ml-auto">AI assistant</Badge>
          </div>
          {info.opening ? <CardDescription>{info.opening}</CardDescription> : null}
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {st === "sealed" || st === "off" ? <p className="text-sm text-muted">{SAID[st]}</p> : null}
          {st === "loading" ? <p className="text-sm text-muted">Loading the assistant...</p> : null}
          {st === "notice" ? (
            <div className="flex flex-col gap-3">
              <p className="text-sm text-muted">{info.notice}</p>
              <Button onClick={agree} disabled={busy} className="self-start">
                I agree
              </Button>
            </div>
          ) : null}
          {st === "chat" ? (
            <>
              <div className="flex max-h-96 min-h-24 flex-col gap-3 overflow-y-auto pr-1" role="log" aria-live="polite"
                aria-labelledby={`${idBase}-h`}>
                {turns.map((t) => (
                  <div key={t.id} className="flex flex-col gap-2">
                    {t.q ? (
                      <p className="max-w-prose self-end rounded-card bg-primary px-3 py-2 text-sm text-on-primary">{t.q}</p>
                    ) : null}
                    <p className="max-w-prose self-start whitespace-pre-line rounded-card bg-surface px-3 py-2 text-sm text-ink">{t.a}</p>
                  </div>
                ))}
                <div ref={end} />
              </div>
              {turns.length === 0 && (info.suggested || []).length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {(info.suggested || []).slice(0, 4).map((s) => (
                    <Button key={s} variant="outline" size="sm" onClick={() => send(s)} disabled={busy}>
                      <Sparkles className="size-4" aria-hidden="true" />
                      {s}
                    </Button>
                  ))}
                </div>
              ) : null}
              {isForm ? (
                <div className="grid gap-3 sm:grid-cols-2">
                  {(info.form || []).map((f) => (
                    <div key={f.key} className={cn("flex flex-col gap-1", f.type === "long_text" && "sm:col-span-2")}>
                      <Label htmlFor={`${idBase}-${f.key}`}>{f.label || f.key}{f.required ? " *" : ""}</Label>
                      {f.type === "long_text" ? (
                        <Textarea id={`${idBase}-${f.key}`} value={vals[f.key] || ""}
                          onChange={(e) => setVals((v) => ({ ...v, [f.key]: e.target.value }))} />
                      ) : (
                        <Input id={`${idBase}-${f.key}`} value={vals[f.key] || ""}
                          type={f.type === "number" ? "number" : f.type === "email" ? "email" : f.type === "phone" ? "tel" : f.type === "date" ? "date" : "text"}
                          list={f.options && f.options.length ? `${idBase}-${f.key}-o` : undefined}
                          onChange={(e) => setVals((v) => ({ ...v, [f.key]: e.target.value }))} />
                      )}
                      {f.options && f.options.length ? (
                        <datalist id={`${idBase}-${f.key}-o`}>
                          {f.options.map((o) => <option key={o} value={o} />)}
                        </datalist>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : null}
              <form
                className="flex items-end gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  void send(text);
                }}
              >
                <Textarea aria-label="Your question" value={text} rows={2} maxLength={2000}
                  placeholder={isForm ? "Anything else to add (optional)" : "Type your question"}
                  onChange={(e) => setText(e.target.value)} className="flex-1" />
                <Button type="submit" disabled={busy || (!text.trim() && !isForm)} aria-label="Send">
                  <Send className="size-4" aria-hidden="true" />
                </Button>
              </form>
              <p className="text-xs text-muted">Answers are written by AI and may be wrong. Never share an OTP, PIN, password or card number.</p>
            </>
          ) : null}
          {err ? <p className="text-sm text-danger" role="alert">{err}</p> : null}
        </CardContent>
      </Card>
    </section>
  );
}
