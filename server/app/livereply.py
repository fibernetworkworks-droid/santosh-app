"""v0.161 Smooth replies: the reply streams to the open console while the model writes it (CONSOLE_STREAM).

One `Live` per assistant reply (one `turn` id). A reply can have several text blocks (`seg`): text -> tool steps ->
text, as it happened. Events (all STREAM_KINDS: live-only, never stored, only to streams that asked with ?live=1):
  reply_start {turn}                      the reply began
  delta       {turn, seg, seq, text}      new words of block `seg` (seq counts up across the whole reply)
  delta_reset {turn, seg}                 that block's words are void (the brain failed mid-stream; another answers)
  reply_end   {turn, stopped?}            the reply is over
  think       {turn, seg, seq, text}      v0.171 the model's reasoning while it thinks (Claude thinking / GLM
                                          reasoning); `clear` instead of `text` when the brain failed mid-thought
The final `message` of each block is published and saved exactly as before, plus `turn` / `seg`: it replaces the
live words, so an old client (or a reload) shows the same reply. Thinking is never stored and never re-sent: the
card lives only while the reply is on the screen (a reload mid-thought gets what was thought so far in /live).

Cleaning (before any word leaves the server): `scrub.text` (this server's keys + well-known key shapes), an OTP box
waiting for her (its digits never echo), and Aadhaar numbers masked. The last TAIL characters, and any word still
being written (no space after it yet: a key is one long word), are held back until more text arrives, so a secret is
never split across two deltas. If cleaning would change words already sent, the block stops streaming and its final
message replaces it.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from sqlalchemy import select

from .config import get_settings
from .db import ChatFeedback, Message, now, session
from .events import bus

log = logging.getLogger("santosh.livereply")

TAIL = 24            # characters held back at the end of the text written so far
FLUSH_S = 0.05       # deltas are batched about every 50 ms
_LIVE: dict[str, "Live"] = {}
STATS = {"replies": 0, "deltas": 0, "resets": 0, "held": 0, "retries": 0, "thinks": 0}


def enabled() -> bool:
    return bool(get_settings().console_v2 or get_settings().console_stream)   # v0.170 CONSOLE_V2 turns the chat phases on in one go


def _mask_ids(tenant: str, text: str) -> str:
    try:
        from . import idvault
        return idvault.AADHAAR.sub(
            lambda m: idvault.mask("aadhaar", "".join(m.groups())) if idvault.verhoeff_ok("".join(m.groups())) else m.group(),
            text)
    except Exception:
        log.exception("id mask failed")
        return text


def _mask_otp(tenant: str, text: str) -> str:
    try:
        from .operator import service as ops
        from .operator.otpwords import find_otp, mask
        a = ops.pending_otp(tenant)
        if a is None:
            return text
        v = find_otp(text, getattr(a, "digits", 0) or 0)
        return mask(text, v) if v else text
    except Exception:
        return text


def clean(tenant: str, text: str) -> str:
    """The words as they may leave the server while streaming."""
    from .scrub import text as scrub_text
    return _mask_ids(tenant, _mask_otp(tenant, scrub_text(text)))


def _safe_end(raw: str) -> int:
    """How much of `raw` may be cleaned and sent now (the rest waits for more text)."""
    end = len(raw) - TAIL
    j = len(raw)
    while j > 0 and not raw[j - 1].isspace():
        j -= 1                         # the word being written: maybe the start of a key
    end = min(end, j)
    pem = raw.rfind("-----BEGIN")
    if pem >= 0 and "-----END" not in raw[pem:]:
        end = min(end, pem)
    return max(0, end)


DRAFT_S = 0.4          # parity Phase 6: a page being written reaches the panel about this often
DRAFT_MAX = 300_000


def draft_on() -> bool:
    try:
        return bool(get_settings().chat_artifact_direct)
    except Exception:
        return False


_ESC = {'"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t"}


def _json_str_prefix(src: str, start: int) -> tuple[str, bool]:
    """The decoded JSON string that starts at src[start] (just after its opening quote), as far as it is written.
    Returns (text, complete)."""
    out: list[str] = []
    i, n = start, len(src)
    while i < n:
        ch = src[i]
        if ch == '"':
            return "".join(out), True
        if ch != "\\":
            out.append(ch)
            i += 1
            continue
        if i + 1 >= n:
            break                      # an escape cut in half: wait for the rest
        e = src[i + 1]
        if e == "u":
            hx = src[i + 2:i + 6]
            if len(hx) < 4:
                break
            try:
                out.append(chr(int(hx, 16)))
            except ValueError:
                pass
            i += 6
            continue
        out.append(_ESC.get(e, e))
        i += 2
    return "".join(out), False


def draft_fields(args: str) -> dict[str, str]:
    """The fields of a half-written `artifact` call (partial JSON): content as far as it is written, the short ones
    only when complete."""
    import re as _re
    out: dict[str, str] = {}
    for key in ("action", "title", "type", "artifact_id", "content"):
        m = _re.search(r'"%s"\s*:\s*"' % key, args or "")
        if not m:
            continue
        val, done = _json_str_prefix(args, m.end())
        if done or key == "content":
            out[key] = val
    return out


class Live:
    def __init__(self, conversation_id: str, tenant: str):
        self.conv, self.tenant = conversation_id, tenant
        self.turn = "t_" + uuid.uuid4().hex[:12]
        self.seg = -1
        self.seq = 0
        self.raw = ""                  # this block's model text so far
        self.sent = ""                 # this block's cleaned words already sent
        self.streaming = False         # this block streams (off: shown only by its final message)
        self.tagged = False            # a message of this block was published
        self.last = 0.0
        self.stopped = False
        self.traw = ""                 # v0.171 this block's thinking so far
        self.tsent = ""                # thinking already sent (cleaned)
        self.tseq = 0
        self.tlast = 0.0
        self.sayq: list[str] = []      # v0.187 the little true lines between steps ("12 mails aaye")

    # ---- one reply
    def start(self) -> None:
        _LIVE[self.conv] = self
        STATS["replies"] += 1
        bus.publish_live(self.conv, "reply_start", {"turn": self.turn})

    def end(self) -> None:
        if _LIVE.get(self.conv) is self:
            _LIVE.pop(self.conv, None)
        p: dict[str, Any] = {"turn": self.turn}
        if self.stopped:
            p["stopped"] = True
        bus.publish_live(self.conv, "reply_end", p)

    # ---- one text block (one model call)
    def block(self, stream: bool = True) -> None:
        """A model call starts: a new block if the last one had words (streamed, or shown by a message)."""
        if self.seg < 0 or self.raw or self.sent or self.tagged:
            self.seg += 1
        self.raw, self.sent, self.streaming, self.last, self.tagged = "", "", stream, 0.0, False
        self.traw, self.tsent, self.tseq, self.tlast = "", "", 0, 0.0     # a new call thinks into its own card

    def tag(self, new_block: bool = False) -> dict:
        """`turn` / `seg` for a message of this reply (a new block for a closing line after the streamed text)."""
        if new_block:
            self.block(stream=False)
        self.tagged = True
        return {"turn": self.turn, "seg": max(0, self.seg)}

    def feed(self, piece: str) -> None:
        if not self.raw:
            piece = piece.lstrip()     # the final text is stripped too
        if not piece:
            return
        self.raw += piece
        if self.streaming and time.monotonic() - self.last >= FLUSH_S:
            self.flush()

    def new_text_block(self) -> None:
        """The model began another text block in the same answer: it is joined with a blank line (as the final text)."""
        if self.raw.strip():
            self.feed("\n\n")

    def flush(self, final: bool = False) -> None:
        if not self.streaming:
            return
        self.last = time.monotonic()
        end = len(self.raw) if final else _safe_end(self.raw)
        if end <= 0:
            return
        words = clean(self.tenant, self.raw[:end])
        if len(words) <= len(self.sent):
            return
        if not words.startswith(self.sent):
            STATS["held"] += 1         # cleaning changed words already sent: the final message replaces this block
            self.streaming = False
            return
        new, self.sent = words[len(self.sent):], words
        self.seq += 1
        STATS["deltas"] += 1
        bus.publish_live(self.conv, "delta", {"turn": self.turn, "seg": self.seg, "seq": self.seq, "text": new})

    def reset(self) -> None:
        """The brain failed after some words: they are void, the next brain writes this block again."""
        if self.sent or self.raw:
            STATS["resets"] += 1
            bus.publish_live(self.conv, "delta_reset", {"turn": self.turn, "seg": self.seg})
        self.raw, self.sent, self.last = "", "", 0.0
        self.think_reset()

    def retract(self) -> None:
        """parity Phase 5b: a check caught this block's answer before it was final - the words she saw stream are
        void (`delta_reset`), and the corrected answer is written into the SAME block (one reply, replaced in place).
        Unlike reset() the Soch card keeps what was thought."""
        if self.sent or self.raw:
            STATS["retracted"] = STATS.get("retracted", 0) + 1
            bus.publish_live(self.conv, "delta_reset", {"turn": self.turn, "seg": max(0, self.seg)})
        self.raw, self.sent, self.last, self.tagged = "", "", 0.0, False

    # ---- thinking (v0.171): the same discipline as the words — held back at word edges, cleaned, never stored
    def feed_think(self, piece: str) -> None:
        if not piece:
            return
        self.traw += piece
        if time.monotonic() - self.tlast >= FLUSH_S:
            self.think_flush()

    def think_flush(self, final: bool = False) -> None:
        if not self.traw:
            return
        self.tlast = time.monotonic()
        end = len(self.traw) if final else _safe_end(self.traw)
        if end <= 0:
            return
        words = clean(self.tenant, self.traw[:end])
        if len(words) <= len(self.tsent):
            return
        if not words.startswith(self.tsent):
            self.traw = self.tsent        # cleaning changed words already sent: the card keeps what it has
            return
        new, self.tsent = words[len(self.tsent):], words
        self.tseq += 1
        STATS["thinks"] += 1
        bus.publish_live(self.conv, "think", {"turn": self.turn, "seg": max(0, self.seg), "seq": self.tseq, "text": new})

    def think_reset(self) -> None:
        """The brain failed while thinking out loud: the card empties, the next brain starts clean."""
        if self.tsent:
            bus.publish_live(self.conv, "think", {"turn": self.turn, "seg": max(0, self.seg), "clear": True})
        self.traw, self.tsent, self.tseq, self.tlast = "", "", 0, 0.0

    def partial(self) -> str:
        """What she saw of the block being written (cleaned), e.g. when she stopped it."""
        return clean(self.tenant, self.raw).strip() if self.raw else ""

    def feed_tool(self, index: int, name: str, args: str) -> None:
        """parity Phase 6: the `artifact` tool's arguments while the model writes them - the page's content so far
        goes to the console's panel (`artifact_draft`, live-only, never stored), cleaned like the words. About every
        0.4 s; the stored version (the `artifact` card) replaces it the moment the call completes."""
        if name != "artifact" or not draft_on():
            return
        tnow = time.monotonic()
        last = getattr(self, "_dlast", {})
        if tnow - last.get(index, 0.0) < DRAFT_S:
            return
        d = draft_fields(args)
        if d.get("action") == "update" or not d.get("content"):
            return                     # an exact edit is tiny: the ready card shows it
        last[index] = tnow
        self._dlast = last
        STATS["drafts"] = STATS.get("drafts", 0) + 1
        bus.publish_live(self.conv, "artifact_draft", {
            "turn": self.turn, "idx": int(index), "title": d.get("title", "")[:120], "type": d.get("type") or "html",
            "action": d.get("action") or "create", "artifact_id": d.get("artifact_id", "")[:40],
            "text": clean(self.tenant, d["content"][:DRAFT_MAX]), "chars": len(d["content"])})

    def feed_say(self, line: str) -> None:
        """v0.187 one short true line about what a tool just really returned, shown while the next model call
        thinks (rule-based from the result, no model call, never a guess). Replaces the previous say line -
        it is one growing whisper above the stream bubble, gone the moment the reply arrives."""
        line = " ".join(str(line or "").split())
        if not line:
            return
        if line in self.sayq:
            return                     # already shown: no re-send
        self.sayq.append(line)
        del self.sayq[:-3]             # keep the last three
        bus.publish_live(self.conv, "say", {"turn": self.turn, "text": "  ·  ".join(self.sayq)})


def begin(conversation_id: str, tenant: str) -> Live | None:
    if not enabled():
        return None
    lv = Live(conversation_id, tenant)
    lv.start()
    return lv


def current(conversation_id: str) -> Live | None:
    return _LIVE.get(conversation_id)


def snapshot(conversation_id: str) -> dict | None:
    """GET /live: the reply being written now (the block's words so far), or None."""
    lv = _LIVE.get(conversation_id)
    if lv is None:
        return None
    out = {"turn": lv.turn, "seg": max(0, lv.seg), "seq": lv.seq, "text": lv.sent}
    if lv.tsent:
        out["think"] = lv.tsent        # v0.171 a reload mid-thought reopens the Soch card with what was thought
    return out


# ---------------------------------------------------------------- retry + thumbs
class RetryError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status = status


RETRY_NOTE = ("[System: she tapped Retry for a fresh answer to the message above. Anything the earlier try already "
              "sent, paid, booked, shared or deleted HAS happened: do not do it again unless she asks, and every such "
              "step still needs its own card / tap.]")


def prepare_retry(conversation_id: str) -> tuple[str, str]:
    """Take the last reply out of the model's history (kept in the database as a branch) and give back her last
    message (text shown, extra context) to run again."""
    from .agent.santosh import _locks
    if _locks[conversation_id].locked():
        raise RetryError(409, "Hoola is working right now. Stop it first, then ask again.")
    with session() as s:
        users = s.scalars(select(Message).where(Message.conversation_id == conversation_id, Message.role == "user",
                                                Message.in_history.is_(True), Message.display.is_not(None))
                          .order_by(Message.id.desc()).limit(20)).all()
        last = next((m for m in users if isinstance(m.content, str)), None)
        if last is None:
            raise RetryError(404, "No question was found to ask again.")
        text, content = last.display or "", last.content
        for m in s.scalars(select(Message).where(Message.conversation_id == conversation_id, Message.id >= last.id,
                                                 Message.in_history.is_(True))).all():
            m.in_history = False
            m.delivered_to_agent = True        # never handed to the model as a worker note either (notes stay as they are)
        at = last.created_at
    i = content.find(text) if text else -1
    context = content[i + len(text):].strip() if i >= 0 else ""
    _hide_old_reply(conversation_id, at)
    STATS["retries"] += 1
    return text, (context + "\n\n" + RETRY_NOTE).strip()


def _hide_old_reply(conversation_id: str, since) -> None:
    from .db import Event
    with session() as s:
        rows = s.scalars(select(Event).where(Event.conversation_id == conversation_id, Event.kind == "message",
                                             Event.created_at >= since).order_by(Event.id)).all()
        for e in rows:
            p = e.payload if isinstance(e.payload, dict) else {}
            if p.get("role") == "assistant" and not p.get("replaced_by"):
                e.payload = {**p, "replaced_by": "retry"}


VALUES = {"up", "down", "none"}


def feedback(tenant: str, conversation_id: str, turn: str, value: str, note: str = "") -> dict:
    if value not in VALUES:
        raise RetryError(400, "value: up | down | none")
    with session() as s:
        row = s.scalars(select(ChatFeedback).where(ChatFeedback.conversation_id == conversation_id,
                                                   ChatFeedback.turn == turn)).first()
        if row is None:
            row = ChatFeedback(tenant_id=tenant, conversation_id=conversation_id, turn=turn)
            s.add(row)
        row.value, row.note, row.updated_at = value, (note or "")[:500], now()
    return {"turn": turn, "value": value}


def feedback_counts(tenant: str, since=None) -> dict:
    with session() as s:
        q = select(ChatFeedback.value).where(ChatFeedback.tenant_id == tenant)
        if since is not None:
            q = q.where(ChatFeedback.updated_at >= since)
        vals = s.scalars(q).all()
    return {"up": sum(v == "up" for v in vals), "down": sum(v == "down" for v in vals)}
