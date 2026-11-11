"""One Room per open file, and the HUB of all rooms of this process (contract sections 1 and 2).

A Room holds the document in memory and is the only writer of it. Everything that changes room state runs on the
event loop WITHOUT awaiting in the middle (apply -> number -> journal queue -> fan out), so ops have one order
and a joiner can never miss or double-see one. Everything slow runs in a worker thread: database reads and
writes, and turning the whole document into compressed JSON.

Durability: an accepted batch is queued for the journal at once and written within one write cycle; a
checkpoint (every `design_checkpoint_ops` ops, after `design_checkpoint_idle_s` of quiet, and when the last
person leaves) stores the whole document and trims the journal below it. Load = snapshot + the journal after it.

Joining is cheap: the room keeps the JSON of its last checkpoint and the op frames since. A joiner gets that
JSON as its `init` and the frames after it - the document is never serialised per person.

One slow browser never stalls the room: each connection has its own bounded send queue and writer task.
Cursor frames are dropped for a connection that is falling behind; a connection whose queue overflows is closed.

D9b speed (wire.py): a browser that asks (`?lazy=1&pages=<ids>`) gets a file over `design_lazy_nodes` PAGE BY PAGE:
its init is the root, every page node and the pages it wants, cut from the live document at this moment, and
`{"t":"page","id"}` asks for one more page, answered at that place of its stream (frames before it are inside it).
`?enc=c1` = it reads and writes the compact op frames; the JSON frames stay exactly as they were for everyone else.
An accepted "create" of a node the server already had is marked `ex: 1` (fan-out) / `ex: [i]` (ack).
"""
from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from ..config import get_settings
from ..db import now
from . import store, wire
from .doc import APPLIED, ID_MAX, MAX_OP_BYTES, REJECTED, ROOT, Doc, dumps, dumps_nodes, loads

log = logging.getLogger("hoola.design")

QUEUE_MAX = 4096                 # frames waiting for one connection before it is closed as too slow
TAIL_JOIN_MAX = 1024             # more op frames than this since the last checkpoint: checkpoint before a join
FRAME_MAX = 8 * 1024 * 1024      # one incoming frame
PRES_MAX = 16 * 1024             # one presence frame
VIEW_STRIKES = 3                 # a view-only connection that keeps sending ops is closed with 4403
PONG = '{"t":"pong"}'
RELOAD = '{"t":"reload"}'
COLORS = ("#F24E1E", "#0FA958", "#1ABCFE", "#A259FF", "#FF7262", "#FFC700", "#00B5AD", "#E84393",
          "#6C5CE7", "#F2994A", "#27AE60", "#2D9CDB")

# The design rooms' own threads: a busy shared pool (model calls, uploads) must never hold up a journal write.
_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="design")
_TASKS: set[asyncio.Task] = set()


async def bg(fn: Callable, *args: Any) -> Any:
    """Run a blocking function (database, disk, big JSON) off the event loop."""
    return await asyncio.get_running_loop().run_in_executor(_POOL, fn, *args)


def _spawn(coro) -> asyncio.Task:
    task = asyncio.ensure_future(coro)
    _TASKS.add(task)
    task.add_done_callback(_TASKS.discard)
    return task


class Conn:
    """One browser in a room. Only its own writer task ever writes to the socket."""

    __slots__ = ("room", "ws", "cid", "name", "color", "role", "queue", "pres", "dead", "strikes", "_code", "_pump",
                 "enc", "pages")

    def __init__(self, room: "Room", ws: Any, cid: int, name: str, color: str, role: str):
        self.room, self.ws, self.cid, self.name, self.color, self.role = room, ws, cid, name, color, role
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=QUEUE_MAX)
        self.pres = ""                       # the last presence frame, replayed to people who join later
        self.dead = False
        self.strikes = 0
        self._code = 1000
        self.enc = "json"                    # D9b: 'c1' = this browser reads and writes the compact op frames
        self.pages: set | None = None        # D9b: the top-level ids this browser was sent whole (None = all of them)
        self._pump = _spawn(self._write())

    def user(self) -> dict:
        return {"cid": self.cid, "name": self.name, "color": self.color}

    def send(self, frame: Any, lossy: bool = False) -> None:
        """Queue a frame; never waits. `lossy` frames (cursors) are skipped while the connection is behind.
        D9b: a frame may also be a Future of one (a page cut being serialised in a worker thread): it keeps its
        place in the stream and the writer waits for it."""
        if self.dead:
            return
        queue = self.queue
        if lossy and queue.qsize() * 2 > QUEUE_MAX:
            return
        try:
            queue.put_nowait(frame)
        except asyncio.QueueFull:
            self.dead = True                 # not removed here: the caller may be in the middle of a fan-out
            asyncio.get_running_loop().call_soon(self.room.drop, self, 1013)

    def close(self, code: int) -> None:
        self.dead = True
        self._code = code
        self._pump.cancel()

    async def _write(self) -> None:
        ws, queue = self.ws, self.queue
        try:
            while True:
                frame = await queue.get()
                if not isinstance(frame, str):
                    frame = await frame          # D9b: a page / init cut, serialised off the loop, in its place
                await ws.send_text(frame)
        except asyncio.CancelledError:
            pass                             # close() asked for it: say goodbye below
        except Exception:                    # noqa: BLE001 - the browser is gone; the reader ends the visit
            self.dead = True
            return
        try:
            await ws.close(self._code)
        except Exception:                    # noqa: BLE001 - already closed from the other side
            pass


def _load(file_id: str, tenant: str | None, max_nodes: int, allow_trashed: bool = False) -> dict | None:
    """Worker thread: read snapshot + journal and rebuild the document. None = no such file for this tenant."""
    raw = store.load_raw(file_id, tenant, allow_trashed)
    if raw is None:
        return None
    doc = Doc.from_json(raw["doc"], max_nodes)
    seq, tail, replayed = raw["seq"], [], 0
    for seq, by, ops_json in raw["journal"]:
        for op in loads(ops_json):
            doc.apply(op)
            replayed += 1
        tail.append((seq, f'{{"t":"ops","seq":{seq},"by":{by},"ops":{ops_json}}}'))
    big = len(doc) > int(getattr(get_settings(), "design_lazy_nodes", 20000))
    return {"tenant": raw["tenant"], "name": raw["name"], "doc": doc, "seq": seq, "base_json": raw["doc"],
            "base_seq": raw["seq"], "tail": tail, "replayed": replayed,
            "pcounts": wire.page_counts(doc.nodes) if big else None}


def _snapshot(file_id: str, nodes: dict, seq: int, version_every_s: float, keep: int, by: str = "") -> str:
    """Worker thread: document -> JSON -> zlib -> the file row (and the journal trimmed below `seq`)."""
    doc_json = dumps_nodes(nodes)
    store.save_snapshot(file_id, store.pack(doc_json), seq, len(nodes), version_every_s, keep, by)
    return doc_json


def _store_json(file_id: str, doc_json: str, seq: int, node_count: int, keep: int) -> None:
    """Worker thread: a document that is already JSON (a restored version) becomes the file's snapshot."""
    store.save_snapshot(file_id, store.pack(doc_json), seq, node_count, 0, keep)


class Room:
    def __init__(self, file_id: str, built: dict):
        st = get_settings()
        self.file_id = file_id
        self.tenant: str = built["tenant"]
        self.name: str = built["name"]
        self.doc: Doc = built["doc"]
        self.seq: int = built["seq"]
        self.conns: dict[int, Conn] = {}
        self.pins = 0                        # connections + other holders; the HUB unloads the room at 0
        self.closed = False                  # the file went to the trash: nobody new is let in
        self._base_json: str = built["base_json"]
        self._base_seq: int = built["base_seq"]
        self._tail: list[tuple[int, str]] = built["tail"]
        self._saved_seq: int = built["base_seq"]
        self._since: int = built["replayed"]            # ops accepted since the last checkpoint
        self._last_op = time.monotonic()
        self._last_by = ""                               # who made the newest accepted edit (named on an automatic version)
        self._journal: list[tuple] = []
        self._writer: asyncio.Task | None = None        # the journal write in flight
        self._saver: asyncio.Task | None = None         # the every-N-ops checkpoint in flight
        self._cp = asyncio.Lock()
        self._cp_ops = max(1, int(st.design_checkpoint_ops))
        self._idle_s = max(0.05, float(st.design_checkpoint_idle_s))
        self._version_s = max(0, int(st.design_autoversion_min)) * 60.0
        self._keep = int(st.design_autoversion_keep)
        self._quiet_s = max(5.0, float(st.design_socket_idle_s))
        self._lazy_nodes = max(0, int(getattr(st, "design_lazy_nodes", 20000)))   # D9b: page by page above this
        self._pcounts: dict | None = built.get("pcounts")                           # D9b: nodes per page, about
        self._last_ex: list[int] = []
        self._ticker = _spawn(self._tick())

    @classmethod
    async def load(cls, file_id: str, tenant: str) -> "Room":
        built = await bg(_load, file_id, tenant, int(get_settings().design_max_nodes))
        if built is None:
            raise LookupError(file_id)
        return cls(file_id, built)

    # ------------------------------------------------------------------ people
    def _color(self) -> str:
        used = {c.color for c in self.conns.values()}
        return next((c for c in COLORS if c not in used), COLORS[len(self.conns) % len(COLORS)])

    async def admit(self, ws: Any, role: str, name: str, lazy: list[str] | None = None, enc: str = "json") -> Conn:
        """Give the socket its client number and its `init`; from the next line on it is in the room.
        D9b: `lazy` (the pages the browser wants first, [] = the first page) = it can take the file page by page:
        a document over `design_lazy_nodes` then comes as the root, every page node and those pages only, cut
        from the LIVE document (init seq = now, no op tail); `enc='c1'` = it speaks the compact op frames."""
        cid = await bg(store.next_cid, self.file_id)
        if len(self._tail) > TAIL_JOIN_MAX:
            await self.checkpoint()
        if self.closed:                                  # the file went to the trash while this one was at the door
            raise LookupError(self.file_id)
        # No await below: the joiner's init, the frames after it and its place in the fan-out are one step.
        if len(self._tail) > TAIL_JOIN_MAX:             # the checkpoint could not be written: rebase in memory
            self._base_json, self._base_seq, self._tail = dumps_nodes(self.doc.nodes), self.seq, []
        conn = Conn(self, ws, cid, name, self._color(), role)
        conn.enc = "c1" if enc == "c1" else "json"
        info = {"t": "init", "cid": cid, "seq": self._base_seq,
                "file": {"id": self.file_id, "name": self.name, "role": role},
                "users": [c.user() for c in self.conns.values()], "you": conn.user()}
        if enc or lazy is not None:                      # D9b: only a browser that asked hears of the new ways
            info["enc"], info["use"] = list(wire.ENCODINGS), conn.enc
        if lazy is not None and len(self.doc) > self._lazy_nodes:
            nodes, sent, rest = wire.cut(self.doc, lazy)
            counts = self._pcounts or {}
            info["seq"] = self.seq
            info["lazy"] = rest
            info["pages"] = [{"id": p, "name": self.doc.nodes[p].get("name", ""), "count": counts.get(p)}
                             for p in self.doc.children(ROOT)]       # counts: as of the last checkpoint (about)
            conn.pages = set(sent)
            conn.send(asyncio.get_running_loop().run_in_executor(_POOL, wire.init_text, dumps(info), nodes))
        else:
            head = dumps(info)
            conn.send(f'{head[:-1]},"doc":{self._base_json}}}')
            for _, frame in self._tail:
                conn.send(frame)
        for other in self.conns.values():
            if other.pres:
                conn.send(other.pres)
        self._fan(dumps({"t": "join", "user": conn.user()}))
        self.conns[cid] = conn
        return conn

    def remove(self, conn: Conn) -> None:
        """Take a connection out of the room (safe to call twice) and tell the others."""
        if self.conns.get(conn.cid) is conn:
            del self.conns[conn.cid]
            self._fan(f'{{"t":"leave","cid":{conn.cid}}}')
        if not conn.dead:
            conn.close(1000)

    def drop(self, conn: Conn, code: int) -> None:
        """Close a connection from this side (too slow, silent, bad frames, file gone)."""
        conn.close(code)
        self.remove(conn)

    def kick(self, code: int) -> None:
        for conn in list(self.conns.values()):
            self.drop(conn, code)

    def kick_guests(self, code: int) -> None:
        """The share link was switched off: every view-only guest is shown out, the editors stay."""
        for conn in list(self.conns.values()):
            if conn.role != "edit":
                self.drop(conn, code)

    def _fan(self, frame: str, skip: Conn | None = None, lossy: bool = False) -> None:
        for conn in self.conns.values():
            if conn is not skip:
                conn.send(frame, lossy)

    def tell(self, frame: str) -> None:
        """A frame for everyone in the room (file renamed, a comment changed)."""
        self._fan(frame)

    # ------------------------------------------------------------------ the socket
    async def serve(self, conn: Conn) -> None:
        """Read one connection until it ends. A frame this server can not read ends the visit (1003)."""
        ws = conn.ws
        while not conn.dead:
            try:
                msg = await asyncio.wait_for(ws.receive(), self._quiet_s)
            except asyncio.TimeoutError:                 # the browser pings every 15 s; this one went silent
                return self.drop(conn, 1001)
            except Exception:                            # noqa: BLE001 - receive after the socket ended
                return
            if msg.get("type") != "websocket.receive":
                return
            text = msg.get("text")
            if text is None:
                return self.drop(conn, 1003)
            if len(text) > FRAME_MAX:
                return self.drop(conn, 1009)
            try:
                frame = loads(text)
                if type(frame) is list:                  # D9b: a compact (c1) frame
                    frame = wire.from_c1(frame)
                kind = frame["t"]
            except Exception:                            # noqa: BLE001 - not JSON, not an object, no "t"
                return self.drop(conn, 1003)
            if kind == "pres":
                self._on_pres(conn, frame)
            elif kind == "ops":
                if not self._on_ops(conn, frame, len(text)):
                    return self.drop(conn, 1003)
            elif kind == "ping":
                conn.send(PONG)
            elif kind == "page":
                self._on_page(conn, frame)

    def _on_pres(self, conn: Conn, frame: dict) -> None:
        frame["t"], frame["cid"] = "pres", conn.cid
        out = dumps(frame)
        if len(out) <= PRES_MAX:
            conn.pres = out
            self._fan(out, skip=conn, lossy=True)

    def _on_ops(self, conn: Conn, frame: dict, size: int) -> bool:
        ops, n = frame.get("ops"), frame.get("n")
        if not isinstance(ops, list) or type(n) is not int:
            return False
        if conn.role != "edit":
            if conn.enc == "c1":
                conn.send(wire.ack_frame(n, self.seq, list(range(len(ops))), []))
            else:
                conn.send(f'{{"t":"ack","n":{n},"seq":{self.seq},"rejected":{dumps(list(range(len(ops))))}}}')
            conn.strikes += 1
            if conn.strikes >= VIEW_STRIKES:
                self.drop(conn, 4403)
            return True
        before = self.seq
        rejected = self._commit(ops, conn.cid, size > MAX_OP_BYTES, conn)
        if self.seq != before:
            self._last_by = conn.name
        ex = self._last_ex
        if conn.enc == "c1":
            conn.send(wire.ack_frame(n, self.seq, rejected, ex))
        elif ex:                                         # D9b: which of hers the server merged into a node it had
            conn.send(f'{{"t":"ack","n":{n},"seq":{self.seq},"rejected":{dumps(rejected)},"ex":{dumps(ex)}}}')
        else:
            conn.send(f'{{"t":"ack","n":{n},"seq":{self.seq},"rejected":{dumps(rejected)}}}')
        return True

    def _on_page(self, conn: Conn, frame: dict) -> None:
        """D9b: one page (a top-level node) of the live document, cut NOW so it sits exactly at this place of the
        connection's stream (every frame before it is inside it), plus the pages its instances' components are on
        that this connection was not sent yet. Serialised in a worker thread; the writer keeps the order."""
        pid = frame.get("id")
        if not isinstance(pid, str) or not 0 < len(pid) <= ID_MAX:
            return
        loop = asyncio.get_running_loop()
        node = self.doc.nodes.get(pid)
        if node is None or node.get("parent") != ROOT:
            conn.send(wire.page_text(pid, None))
            return
        have = conn.pages if conn.pages is not None else set(self.doc.children(ROOT))
        order, cuts = wire.closure(self.doc, [pid], have - {pid})
        for p in order:
            conn.send(loop.run_in_executor(_POOL, wire.page_text, p, cuts[p]))
            if conn.pages is not None:
                conn.pages.add(p)

    # ------------------------------------------------------------------ ops
    def _commit(self, ops: list, by: int, measure: bool, skip: Conn | None) -> list[int]:
        """Apply a batch in order; number, journal and fan out the accepted ops as ONE frame, serialised once.
        Returns the indexes of the refused ops. `measure` = the frame was big enough for one op to be over the limit."""
        doc, accepted, rejected, ex, nodes = self.doc, [], [], [], self.doc.nodes
        for i, op in enumerate(ops):
            # D9b: a "create" of a node the server already has merges into it - marked `ex` for browsers that hold
            # only some pages (they can not know that node's other props). Rare: an undo of a delete racing another.
            had = type(op) is dict and type(op.get("p")) is dict and op["p"].get("type") is not None and op.get("id") in nodes
            result = REJECTED if measure and len(dumps(op)) > MAX_OP_BYTES else doc.apply(op)
            if result == APPLIED:
                if had:
                    op = dict(op, ex=1)
                    ex.append(i)
                accepted.append(op)
            elif result == REJECTED:
                rejected.append(i)
        self._last_ex = ex
        if accepted:
            self.seq += 1
            body = dumps(accepted)
            frame = f'{{"t":"ops","seq":{self.seq},"by":{by},"ops":{body}}}'
            self._tail.append((self.seq, frame))
            self._journal.append((self.seq, by, body, now()))
            if self._writer is None or self._writer.done():
                self._writer = _spawn(self._write_journal())
            self._since += len(accepted)
            self._last_op = time.monotonic()
            c1 = None
            for conn in self.conns.values():             # the JSON frame, or the compact one built once (D9b)
                if conn is not skip:
                    if conn.enc == "c1":
                        if c1 is None:
                            c1 = wire.ops_frame(self.seq, by, accepted)
                        conn.send(c1)
                    else:
                        conn.send(frame)
            if self._since >= self._cp_ops and (self._saver is None or self._saver.done()):
                self._saver = _spawn(self.checkpoint())
        return rejected

    def apply_external(self, ops: list) -> dict:
        """Ops made by the server itself (AI, the agent tool): same rules, same journal, everyone sees them."""
        rejected = self._commit(loads(dumps(ops)), 0, True, None)
        return {"seq": self.seq, "rejected": rejected}

    # ------------------------------------------------------------------ durability
    async def _write_journal(self) -> None:
        while self._journal:
            rows, self._journal = self._journal, []
            try:
                await bg(store.append_ops, self.file_id, rows)
            except Exception:                            # noqa: BLE001
                # The rows are lost to the journal, but the document in memory has them: checkpoint now.
                log.exception("design journal write failed for %s (%d batches); checkpointing instead",
                              self.file_id, len(rows))
                self._since = max(self._since, self._cp_ops)
                self._last_op = 0.0

    async def _flush_journal(self) -> None:
        while self._writer is not None and not self._writer.done():
            await asyncio.shield(self._writer)

    async def checkpoint(self) -> bool:
        """Store the whole document and trim the journal below it. False = it could not be written (it is retried)."""
        async with self._cp:
            await self._flush_journal()                  # every row up to `seq` is in the journal before it is trimmed
            if self.seq == self._saved_seq:
                return True
            seq, nodes, counted = self.seq, self.doc.copy_nodes(), self._since
            try:
                doc_json = await bg(_snapshot, self.file_id, nodes, seq, self._version_s, self._keep, self._last_by)
            except Exception:                            # noqa: BLE001
                log.exception("design checkpoint failed for %s at seq %d", self.file_id, seq)
                return False
            self._saved_seq = seq
            self._since = max(0, self._since - counted)
            if len(nodes) > self._lazy_nodes:          # D9b: the page list's layer counts, off the loop
                try:
                    self._pcounts = await bg(wire.page_counts, nodes)
                except Exception:                        # noqa: BLE001 - only a hint for the page list
                    pass
            if seq > self._base_seq:
                self._base_json, self._base_seq = doc_json, seq
                self._tail = [entry for entry in self._tail if entry[0] > seq]
            return True

    async def _tick(self) -> None:
        """The idle checkpoint (and the retry of one that failed)."""
        pause = min(5.0, self._idle_s / 2)
        while True:
            await asyncio.sleep(pause)
            if self.seq != self._saved_seq and time.monotonic() - self._last_op >= self._idle_s:
                await asyncio.shield(_spawn(self.checkpoint()))      # close() may cancel this loop, never a save

    async def current(self) -> tuple[int, str]:
        """(seq, document JSON) of a consistent moment, without serialising on the event loop."""
        if self._tail and not await self.checkpoint():   # the database is refusing writes: answer from memory
            seq, nodes = self.seq, self.doc.copy_nodes()
            return seq, await bg(dumps_nodes, nodes)
        return self._base_seq, self._base_json

    async def replace(self, doc_json: str) -> int:
        """Swap in another document (a version was restored), store it, and tell every editor to fetch again."""
        doc = await bg(Doc.from_json, doc_json, self.doc.max_nodes)
        async with self._cp:
            await self._flush_journal()
            self.doc = doc
            self.seq += 1
            self._base_json, self._base_seq, self._tail, self._since = doc_json, self.seq, [], 0
            self._fan(RELOAD)                            # before any op that lands on the new document
            seq = self.seq
            await bg(_store_json, self.file_id, doc_json, seq, len(doc), self._keep)
            self._saved_seq = max(self._saved_seq, seq)
        return seq

    async def close(self) -> None:
        """The last person left: write what is not yet written."""
        self._ticker.cancel()
        await self.checkpoint()


class Hub:
    """All open rooms of this process. A file's room is loaded and unloaded behind a per-file gate, so a join that
    arrives while the last person's room is still saving waits and then loads what was saved."""

    def __init__(self) -> None:
        self.rooms: dict[str, Room] = {}
        self._gates: dict[str, asyncio.Event] = {}

    async def open(self, file_id: str, tenant: str) -> Room:
        """The file's room, pinned for the caller (pair with `release`). LookupError = no such file for this tenant."""
        while file_id in self._gates:
            await self._gates[file_id].wait()
        room = self.rooms.get(file_id)
        if room is None:
            gate = self._gates[file_id] = asyncio.Event()
            try:
                room = self.rooms[file_id] = await Room.load(file_id, tenant)
            finally:
                del self._gates[file_id]
                gate.set()
        elif room.tenant != tenant or room.closed:
            raise LookupError(file_id)
        room.pins += 1
        return room

    async def release(self, room: Room) -> None:
        room.pins -= 1
        if room.pins <= 0:
            await asyncio.shield(_spawn(self._retire(room)))     # a cancelled caller must not cut the save short

    async def _retire(self, room: Room) -> None:
        file_id = room.file_id
        if room.pins > 0 or self.rooms.get(file_id) is not room or file_id in self._gates:
            return
        gate = self._gates[file_id] = asyncio.Event()
        try:
            await room.close()
        except Exception:                                # noqa: BLE001
            log.exception("design room %s did not close cleanly", file_id)
        finally:
            self.rooms.pop(file_id, None)
            del self._gates[file_id]
            gate.set()

    def live(self, file_id: str) -> Room | None:
        return self.rooms.get(file_id)

    def tell(self, file_id: str, frame: str) -> None:
        room = self.rooms.get(file_id)
        if room is not None:
            room.tell(frame)

    def renamed(self, file_id: str, name: str) -> None:
        room = self.rooms.get(file_id)
        if room is not None:
            room.name = name
            room.tell(dumps({"t": "file", "name": name}))

    def evict(self, file_id: str, code: int) -> None:
        """The file went to the trash: everyone in it is shown out, and nobody new is let in."""
        room = self.rooms.get(file_id)
        if room is not None:
            room.closed = True
            room.kick(code)

    def unshared(self, file_id: str) -> None:
        """The share link of a file was switched off: its guests leave (4404, the same as a link that never was)."""
        room = self.rooms.get(file_id)
        if room is not None:
            room.kick_guests(4404)

    def restored(self, file_id: str) -> None:
        """The file came back from the trash while its room was still unloading: it may be joined again."""
        room = self.rooms.get(file_id)
        if room is not None:
            room.closed = False

    async def read(self, file_id: str, tenant: str | None, allow_trashed: bool = False) -> tuple[int, str] | None:
        """(seq, document JSON) as of now: from the open room, else from the database. None = no such file."""
        room = self.rooms.get(file_id)
        if room is not None and tenant in (None, room.tenant):
            return await room.current()
        return await bg(_read, file_id, tenant, allow_trashed)

    async def replace(self, file_id: str, tenant: str, doc_json: str) -> int:
        room = await self.open(file_id, tenant)
        try:
            return await room.replace(doc_json)
        finally:
            await self.release(room)

    async def apply_ops(self, file_id: str, tenant: str, ops: list) -> dict:
        """HOOK for the AI route and the agent tool (phase D5): apply server-made ops THROUGH the room, so they are
        checked, journaled and seen by every open editor. Mint their node ids under `await new_cid(file_id)`."""
        room = await self.open(file_id, tenant)
        try:
            return room.apply_external(ops)
        finally:
            await self.release(room)

    async def new_cid(self, file_id: str) -> int:
        """A client number for server-made nodes (see apply_ops)."""
        return await bg(store.next_cid, file_id)

    async def shutdown(self) -> None:
        """Server stop: show everyone out and write every open room."""
        for room in list(self.rooms.values()):
            room.kick(1012)
            try:
                await room.close()
            except Exception:                            # noqa: BLE001
                log.exception("design room %s did not close cleanly at shutdown", room.file_id)
        self.rooms.clear()


def _read(file_id: str, tenant: str | None, allow_trashed: bool) -> tuple[int, str] | None:
    built = _load(file_id, tenant, int(get_settings().design_max_nodes), allow_trashed)
    if built is None:
        return None
    if not built["tail"]:
        return built["base_seq"], built["base_json"]
    return built["seq"], dumps_nodes(built["doc"].nodes)


HUB = Hub()
