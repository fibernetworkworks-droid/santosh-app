"use client"; // v0.999.124: her members' board - an island
// Hoola App Engine - Hoola's own kit file. Her Discussions section, with her members talking to each other once SHE
// switched the board on (Studio > Settings > Members' board): anyone reads the shown posts (or only members, her
// choice), a signed-in member of her website posts and replies, a post waits for her approval by default, any member
// reports a post. Everything is checked on Hoola's server (numbers and emails masked, caps, her approval). With the
// board off this is her Discussions section as it was: topics + a question that reaches her.
import * as React from "react";
import { Flag, MessageSquare, Reply } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import Discussions, { type DiscussionsProps } from "@/components/blocks/discussions";
import { Container, Section, SectionHead } from "@/components/blocks/_kit";
import { AppError, siteApp, useMember } from "@/lib/member";

type Post = { id: string; topic: string; parent: string; name: string; text: string; at: string; mine?: boolean; status?: string };
type Board = { on: boolean; signin?: boolean; approve?: boolean; posts?: Post[]; signed_in?: boolean };

export interface MemberBoardProps extends DiscussionsProps {
  site: string;
  signin?: string;
}

const when = (iso: string) => {
  try {
    return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short" });
  } catch {
    return "";
  }
};

export default function MemberBoard({ site, signin, ...disc }: MemberBoardProps) {
  const [board, setBoard] = React.useState<Board | null>(null);
  const [topic, setTopic] = React.useState("");
  const [text, setText] = React.useState("");
  const [reply, setReply] = React.useState<{ to: string; text: string } | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [said, setSaid] = React.useState("");
  const { me } = useMember(site);
  const id = React.useId();
  const topics = (disc.topics || []).map((t) => t.title).filter(Boolean);

  const load = React.useCallback(() => {
    siteApp<Board>(site, "board")
      .then(setBoard)
      .catch(() => setBoard({ on: false }));
  }, [site]);
  React.useEffect(load, [load, me]);

  if (!board || !board.on) return <Discussions {...disc} />;

  async function send(body: Record<string, string>, done: () => void) {
    setBusy(true);
    setSaid("");
    try {
      const out = await siteApp<{ say?: string }>(site, "board", "POST", body);
      setSaid(out.say || "");
      done();
      load();
    } catch (e) {
      setSaid(e instanceof AppError || e instanceof Error ? e.message : "That did not work. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  async function report(pid: string) {
    try {
      const out = await siteApp<{ say?: string }>(site, "board/report", "POST", { id: pid });
      setSaid(out.say || "");
      load();
    } catch (e) {
      setSaid(e instanceof Error ? e.message : "That did not work.");
    }
  }

  const posts = (board.posts || []).filter((p) => !topic || p.topic === topic);
  const tops = posts.filter((p) => !p.parent);
  const kids = (pid: string) => posts.filter((p) => p.parent === pid).reverse();
  const line = (p: Post) => (
    <div className="flex flex-col gap-1">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="font-semibold">{p.name}</span>
        <span className="text-muted">{when(p.at)}</span>
        {p.topic && !p.parent ? <Badge variant="secondary">{p.topic}</Badge> : null}
        {p.mine && p.status === "waiting" ? <Badge variant="secondary">Waiting for approval</Badge> : null}
      </div>
      <p className="whitespace-pre-line text-base">{p.text}</p>
    </div>
  );

  return (
    <Section block="discussions" variant="topics" tone={disc.tone ?? "plain"} data-hoola-board="on">
      <Container>
        <SectionHead title={disc.title || "Members' board"} intro={disc.intro} />
        {topics.length ? (
          <div className="mb-6 flex flex-wrap gap-2" role="group" aria-label="Topics">
            <Button variant={topic ? "outline" : "default"} size="sm" onClick={() => setTopic("")} aria-pressed={!topic}>All</Button>
            {topics.map((t) => (
              <Button key={t} variant={topic === t ? "default" : "outline"} size="sm" onClick={() => setTopic(t)} aria-pressed={topic === t}>{t}</Button>
            ))}
          </div>
        ) : null}
        {board.signin ? (
          <p className="text-muted">The board is for members. {signin ? <a className="text-primary underline" href={signin}>Sign in</a> : "Sign in"} to read and post.</p>
        ) : (
          <div className="grid gap-8 lg:grid-cols-12">
            <ul className="flex flex-col gap-4 lg:col-span-7" aria-label="Posts">
              {tops.length === 0 ? <li className="text-muted">No posts yet. Start the conversation.</li> : null}
              {tops.map((p) => (
                <li key={p.id} className="flex flex-col gap-3 rounded-card border border-line bg-surface p-5">
                  {line(p)}
                  {kids(p.id).map((k) => (
                    <div key={k.id} className="ml-4 border-l border-line pl-4">{line(k)}</div>
                  ))}
                  {me ? (
                    <div className="flex flex-wrap gap-2">
                      <Button variant="ghost" size="sm" onClick={() => setReply({ to: p.id, text: "" })}>
                        <Reply className="size-4" aria-hidden="true" /> Reply
                      </Button>
                      {!p.mine ? (
                        <Button variant="ghost" size="sm" onClick={() => report(p.id)}>
                          <Flag className="size-4" aria-hidden="true" /> Report
                        </Button>
                      ) : null}
                    </div>
                  ) : null}
                  {reply && reply.to === p.id ? (
                    <form className="flex flex-col gap-2" onSubmit={(e) => { e.preventDefault(); void send({ parent: p.id, text: reply.text }, () => setReply(null)); }}>
                      <Label htmlFor={`${id}-r-${p.id}`}>Your reply</Label>
                      <Textarea id={`${id}-r-${p.id}`} value={reply.text} maxLength={2000} onChange={(e) => setReply({ to: p.id, text: e.target.value })} />
                      <div className="flex gap-2">
                        <Button type="submit" size="sm" disabled={busy || reply.text.trim().length < 2}>Send reply</Button>
                        <Button type="button" size="sm" variant="ghost" onClick={() => setReply(null)}>Cancel</Button>
                      </div>
                    </form>
                  ) : null}
                </li>
              ))}
            </ul>
            <div className="flex flex-col gap-3 lg:col-span-5">
              <div className="flex items-center gap-2">
                <MessageSquare className="size-5 text-primary" aria-hidden="true" />
                <h3 className="text-lg font-semibold">Write to the members</h3>
              </div>
              {me ? (
                <form className="flex flex-col gap-2" onSubmit={(e) => { e.preventDefault(); void send({ topic, text }, () => setText("")); }}>
                  <Label htmlFor={`${id}-new`}>{topic ? `Your post about ${topic}` : "Your post"}</Label>
                  <Textarea id={`${id}-new`} value={text} maxLength={2000} rows={4} onChange={(e) => setText(e.target.value)} />
                  <Button type="submit" disabled={busy || text.trim().length < 2} className="self-start">Post</Button>
                  <p className="text-sm text-muted">
                    {board.approve ? "Posts show after the organisers approve them. " : ""}Phone numbers and email addresses are hidden.
                  </p>
                </form>
              ) : (
                <p className="text-muted">{signin ? <a className="text-primary underline" href={signin}>Sign in</a> : "Sign in"} to post and reply.</p>
              )}
              {said ? <p className="text-sm" role="status">{said}</p> : null}
            </div>
          </div>
        )}
      </Container>
    </Section>
  );
}
