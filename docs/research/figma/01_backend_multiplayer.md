# Figma backend and collaboration architecture (primary sources)

Researched 11 Nov 2026. Sources are Figma's own engineering blog, help centre and developer docs, plus Evan Wallace's (co-founder, former CTO) GitHub. A claim with no primary source is marked **[secondary]** or **[unconfirmed]**. Each claim cites its source URL. Numbers appear exactly as published. Where a post gives no number, this file gives none either.

Source key (cited by tag below):

- **[MP]** How Figma's multiplayer technology works: https://www.figma.com/blog/how-figmas-multiplayer-technology-works/
- **[SEQ]** Realtime editing of ordered sequences: https://www.figma.com/blog/realtime-editing-of-ordered-sequences/
- **[MPE]** Multiplayer editing in Figma (launch post): https://www.figma.com/blog/multiplayer-editing-in-figma/
- **[RUST]** Rust in production at Figma: https://www.figma.com/blog/rust-in-production-at-figma/
- **[REL]** Making multiplayer more reliable: https://www.figma.com/blog/making-multiplayer-more-reliable/
- **[AUTO]** Behind the feature: autosave: https://www.figma.com/blog/behind-the-feature-autosave/
- **[LG1]** LiveGraph: real-time data fetching at Figma: https://www.figma.com/blog/livegraph-real-time-data-fetching-at-figma/
- **[LG2]** Keeping it 100(x) with real-time data at scale: https://www.figma.com/blog/livegraph-real-time-data-at-scale/
- **[DB]** How Figma's databases team lived to tell the scale: https://www.figma.com/blog/how-figmas-databases-team-lived-to-tell-the-scale/
- **[INFRA]** Under the hood of Figma's infrastructure: https://www.figma.com/blog/under-the-hood-of-figmas-infrastructure/
- **[DPL]** Speeding up file load times, one page at a time: https://www.figma.com/blog/speeding-up-file-load-times-one-page-at-a-time/
- **[PLUG]** How we built the Figma plugin system: https://www.figma.com/blog/how-we-built-the-figma-plugin-system/
- **[KIWI]** evanw/kiwi: https://github.com/evanw/kiwi
- **[MEM]** Figma Help, memory usage: https://help.figma.com/hc/en-us/articles/360040528973
- **[PLUGDL]** Migrating plugins to dynamically load pages: https://developers.figma.com/docs/plugins/migrating-to-dynamic-loading
- **[BR]** Branching in Figma (best practices): https://www.figma.com/best-practices/branching-in-figma/

---

## 1. Multiplayer: the data model and the sync algorithm

### 1.1 Topology
- Clients are web pages. They talk "with a cluster of servers over WebSockets". Figma will "spin up a separate process for each multiplayer document which everyone editing that document connects to" [MP]. Each design file maps to one Multiplayer instance [INFRA].
- Multiplayer syncs **only the document**. Comments, users, teams and projects live in Postgres and sync through a separate system, which became LiveGraph (section 3) [MP].
- **Join:** the client downloads the full file, then receives updates over the socket [MP]. Dynamic page loading changed this later (section 4).
- The server is authoritative for validation, ordering and conflict resolution [REL].

### 1.2 The document is a tree of objects with properties
- "Every Figma document is a tree of objects, similar to the HTML DOM" [MP].
- Logically the document is `Map<ObjectID, Map<Property, Value>>`, which equals a set of `(ObjectID, Property, Value)` rows [MP]. New features usually just mean new properties on existing objects [MP].

### 1.3 Conflict resolution: last-writer-wins, per property, decided by the server
- The server keeps the latest value any client sent for each property of each object [MP]. "Two simultaneous changes are independent unless they affect the same property on the same object" [MPE].
- When two edits hit the same property, "the document will just end up with the last value that was sent to the server" [MP].
- Each property value is atomic. Two concurrent edits to a text value give "AB or BC but never ABC". No character merging takes place [MP].
- **Optimistic local apply:** a client applies its own change at once. To avoid flicker, it **discards incoming server changes that conflict with its own unacknowledged changes**. Once the server acknowledges its change, the server's order is final [MP].
- **Coupled properties** have to be merged with care. Some actions change other objects too (layout is the example), and two users editing unrelated objects could then conflict. Figma fixed this by changing how layout features work [MPE].

### 1.4 Why this is neither OT nor a true CRDT
- OT was rejected as "unnecessarily complex for our problem space" [MP]. Under OT "every operation must transform correctly past every other operation", so complexity grows quadratically with the number of operation types [SEQ].
- Figma is "inspired by" CRDTs but does not use true CRDTs. A central server is the authority, so the overhead CRDTs need for decentralised merging can be dropped [MP]. In effect it is several CRDT-like structures (an LWW register per property, an LWW parent+position pair per child) put together, with the server's arrival order as the clock [MP].

### 1.5 Object creation, deletion, IDs
- Creation and removal are explicit operations. Writing to an unassigned ID cannot create an object [MP].
- IDs are a **per-client ID plus a local counter**, so a client can create objects offline without asking the server [MP].
- The server does **not** keep a deleted object's properties. They live in the **undo buffer of the client that deleted it**. Undoing a delete re-creates the object from that buffer [MP].

### 1.6 Child order: fractional indexing
- Every child has a position that is a fraction strictly between 0 and 1. Siblings are sorted by it. An insert between two siblings takes a value between theirs (the average), and a move changes only the moved object's index [MP][SEQ].
- "We use arbitrary-precision fractions instead of 64-bit doubles so that we can't run out of precision after lots of edits" [SEQ]. Indices are **strings**: the leading "0." is dropped, the digits use the printable ASCII range (base 95), and averaging is done by string manipulation [SEQ].
- **Two clients inserting into the same gap:** the server gives the second insert a unique position, so no two siblings ever share an index [SEQ].
- Index strings can grow longer over time. Figma accepts this because reordering is bounded by user activity [SEQ].
- Figma has used fractional indexing "from the beginning" and credits it with simplicity: "it's much more beneficial ... to use simple algorithms that are easy to understand and implement" [SEQ]. (The term "fractional indexing" is widely credited to this post [secondary].)

### 1.7 Reparenting and cycle prevention
- The parent link is **a property of the child** (not a list held by the parent), so a move keeps the object's identity [MP].
- **Parent link and position are stored as one property**, so a reparent and its new order update atomically [MP].
- Two concurrent moves can form a cycle (A under B while B moves under A). "Figma's multiplayer servers reject parent property updates that would cause a cycle" [MP].
- Before the rejection arrives, a client may briefly hold a cycle. Figma handles it by temporarily parenting the objects to each other and **removing them from the visible tree** until the server resolves it. The objects briefly disappear, a trade-off Figma accepts because the case is rare and short-lived [MP].

### 1.8 Undo/redo in multiplayer
- The guiding rule: "if you undo a lot, copy something, and redo back to the present ... the document should not change" [MP][MPE].
- How: **an undo writes redo history at the moment of the undo, and a redo writes undo history at the moment of the redo** [MP]. The client records the values it is overwriting at that moment, so an undo reverts only *your* properties to what you last saw, and other users' later edits to other properties survive. Undo is per-client and local; the server knows nothing about it beyond ordinary property writes [MP].

### 1.9 Presence
- The launch post shows every participant's **mouse cursor and selection**, plus avatars in the top-right [MPE].
- **Presentation (follow) mode:** clicking an avatar follows that person. It is opt-in; a viewer can drift off and rejoin without interrupting the presenter. An earlier design (one presenter per document, mandatory following) and a "baton-passing" single-editor model were both rejected [MPE].
- Turning off multiplayer cursors is one of Figma's suggestions for reducing memory use (help centre, via [MEM]'s linked guide).
- **Not published:** the presence wire protocol and its rate. The [MP] post does not cover presence.

### 1.10 Offline and reconnect (the rebase)
- "Figma lets you go offline for an arbitrary amount of time and continue editing" [MP]. On reconnect the client **downloads a fresh copy and reapplies its offline edits on top of that latest state** [MP]. With per-property LWW this "rebase" is simply re-sending the pending property sets, and the server applies them as new last writes.
- **Autosave [AUTO]:** pending changes go to **IndexedDB** "as a set of property changes on a per-file, per-(node/layer) basis", written at intervals as deltas ("we only need to write changes between commits"). They are not written as a whole-file blob: files reach "tens of megabytes" compressed and "hundreds of megabytes" in memory, and serialising the largest "can actually take a few seconds"; even 100 ms would be a regular stutter on a single-threaded JS/WASM main thread.
- Invariant: "the node changes stored on disk are exactly equal to the pending node changes stored in memory". The document counts as unsaved "until the changes are acknowledged by the server", and closing the tab is blocked during that window [AUTO].
- Restore = "apply this diff on top of the latest version of the document". Autosaved work is treated like a **branch split off at disconnect**; several tabs belonging to the same user are applied one after another. Figma automatically creates a **version-history checkpoint before and after** applying the diff, so a messy merge can be reverted [AUTO]. Offline work may wait "days" [AUTO].
- Offline you can open only files you already opened online, and pages not yet loaded stay unavailable [MEM].

---

## 2. The multiplayer server

### 2.1 TypeScript to Rust [RUST]
- **The original** was TypeScript on Node.js, single-threaded: "a single slow operation would lock up the entire worker". Encoding large documents caused latency spikes. Many documents shared one worker, so one heavy file slowed every file on it. The stopgap was moving heavy documents by hand to a separate pool of "heavy" workers.
- **Not** one Node process per document: V8's memory overhead per process was too high.
- **Final shape:** Node.js still handles the network (WebSockets, periodic HTTP). For **each document** it spawns a **Rust child process**, and they talk over **stdin/stdout** with a message protocol; stderr carries logs. The Rust side runs a single event loop. A full rewrite was planned and then dropped.
- Rust's low memory use (no GC, layout control) made "it was actually practical to just start a separate Rust process for every document."
- Results: serialisation "now over 10x faster", and server-side editing performance improved "by an order of magnitude". GC pauses were part of the old problem.
- Lessons: two Servo-used Rust compression libraries had correctness bugs that could lose data, so Figma used a C library. Async Rust was too immature at the time, which is why the networking stayed in Node.

### 2.2 In-memory document, checkpoints, journal [REL]
- "multiplayer holds the state of the file in-memory and updates it as changes come in."
- **Checkpoint (before the journal):** every **30 to 60 seconds** the whole file is binary-encoded, compressed and uploaded to **S3**. A crash could lose up to ~60 s of server-side work. A redeploy closed every in-memory file at once and caused checkpoint write storms.
- **Journal = write-ahead log:** "Each change is assigned a sequence number, which is an incrementing integer associated with the file." Each checkpoint stores the sequence number it reached. **Recovery** loads the latest checkpoint and replays journal entries with higher sequence numbers.
- Clients send updates every **33 ms (30 FPS)**. Journal entries are batched and stored with start/end sequence numbers (e.g. `[5, 9]`), written about every **0.5 s**. The data-loss goal is **under 1 s**.
- **Store:** **DynamoDB**, picked over Postgres, which would have needed horizontal scaling for this write rate. A separate lock table holds `(lock UUID, file key)` so that **only one multiplayer instance** can write a file's journal. Journal writes are **conditional on the lock UUID**, and reads after taking the lock are strongly consistent (single-writer fencing).
- **Deploys:** multiplayer closes connections and waits for pending changes to persist; p99 is under 1 s.
- **Cross-region:** the target is replication within 30 minutes. DynamoDB global tables were rejected at ~6x cost. Instead the journal is checkpointed within 30 min, and the S3 checkpoints are already replicated across regions. Async checkpoint jobs use jittered delays.
- **Proof before rollout:** checkpoint A plus its journal entries must reproduce checkpoint B **byte for byte**; ~**400K** consecutive successful validations.
- **Scale:** "the journal handles >2.2B received changes per day"; "95% of edits to a Figma file get saved within 600ms". For the worst 5% of files a checkpoint can take ~4 s or more.

### 2.3 Geography [INFRA]
- More than 80% of weekly active users are outside the US, and latency was bound by the round trip to the main Oregon datacenter. The plan was global proxies first, then multiplayer instances placed near each document's users.

---

## 3. Non-document data: LiveGraph and Postgres

### 3.1 LiveGraph v1 [LG1]
- "a data fetching layer on top of Postgres". It is a query engine, not storage. Clients send "GraphQL-like queries" and get a JSON tree back, through a React `useSubscription` hook with generated TypeScript bindings.
- **Change capture:** it does not poll. It "tail[s] the database replication log" (the Postgres WAL / replication stream).
- Each view breaks down into a tree of **join-free subqueries** (`SELECT columns FROM table WHERE condition`), one object type each. Active subqueries are indexed by type, so each replication row touches only the matching cached results. Identical subqueries are shared across viewers, which works as a cache.
- Updates arrive in order and exactly once. On disconnect the client re-fetches the view. Access-control rules are applied per object and relation. **Optimistic updates** are removed automatically once the real write shows up in the subscription.
- Built in Node.js plus **Go** for multithreaded hot paths. Each instance processed the whole replication stream, about **10,000 writes/second**. Persistent sockets caused a "thundering herd" of re-subscribes after each deploy.

### 3.2 LiveGraph 100x [LG2]
- Sessions tripled since 2021, and view requests grew ~5x in a year. The old design was one in-memory, **mutation-based** cache per server, each server tailing the stream. After vertical partitioning the shard streams were merged into one to keep global order.
- Problems named: fan-out (every mutation to every server), fan-in, read scaling coupled to update scaling, fragmented caches, wide blast radius, and deploys emptying the cache.
- **Key insight:** most traffic is *initial reads*, not live updates, so an **invalidation-based** cache is enough. Most queries can be invalidated straight from a row mutation by filling the row's values into known query shapes, so invalidators need not track subscriptions.
- **Three tiers, in Go:** *Edge* (expands views to queries, subscribes, re-fetches on invalidation) / *Cache* (read-through, sharded by query hash, topology-agnostic, forwards invalidations to edges through a **cuckoo filter**, hot standbys) / *Invalidator* (sharded like the physical DB shards, each tailing one replication stream; the only tier that knows the topology).
- **Hard queries** (e.g. range filters on `created_at`) are **11 of ~700**. Every query is normalised to `(easy-expr) AND (hard-expr)`; hard results sit under a key holding a nonce, and an easy-key invalidation drops them (deliberate over-invalidation).
- A "read-invalidation rendezvous" stops a stale read from being cached across a concurrent invalidation. Validation used chaos tests, online sampling against the primary, and a convergence checker comparing old and new engines. In production ~1.5 years.

### 3.3 Postgres scaling [INFRA][DB]
- Earlier: a **single Postgres instance** on a very large AWS machine, nearing its limits [INFRA].
- "Figma's database stack has grown almost 100x since 2020". In 2020 it ran on AWS's largest physical instance. By end-2022 it had caching, read replicas and ~a dozen **vertically partitioned** databases (table groups such as "Figma files" and "Organizations" moved to their own DBs). That lever was "relatively easy and very impactful", but the smallest unit it can move is one table [DB].
- What forced **horizontal sharding**: multi-terabyte, billion-row tables, vacuum reliability, and write-heavy tables nearing the RDS max IOPS. CockroachDB, TiDB, Spanner and Vitess were rejected as risky migrations; NoSQL would have meant rewriting the backend [DB].
- **Design:** sharding on top of RDS Postgres; **no atomic cross-shard transactions**. **Colos** are table groups sharing a shard key, where joins and full transactions work within a single key. Shard keys are **UserID, FileID, OrgID**, **hashed** to avoid hotspots (cost: weaker range scans). **Logical shards** (Postgres views on the old instance, percentage rollout, instant rollback) come before **physical** moves, e.g. "Four logical shards on two physical shards" [DB].
- **DBProxy** (Go, between the app and PGBouncer): SQL parser → logical planner → physical planner; scatter-gather for queries without a key; load-shedding; observability. Shadow planning showed the supported subset covers the most common 90% of queries; the views cost under 10% overhead. The first sharded table shipped in Sept 2023 after ~9 months; its failover meant 10 s of partial primary availability [DB].

---

## 4. File format and loading large files

### 4.1 Kiwi and the .fig format
- **Kiwi** (Evan Wallace, MIT) is "a schema-based binary format for encoding trees of data". It has `enum`, `struct` (fixed, required fields, cannot grow) and `message` (optional fields, can grow) types; varints (≤5 bytes for 32-bit, ≤9 for 64-bit); a zero float takes 1 byte; strings are null-terminated UTF-8; reading and writing take one linear pass. It is backward compatible, and forward compatible if the schema travels with the data. Kiwi presents itself as simpler than protobuf, with real field-presence detection, and leaves compression to a later step [KIWI].
- **Figma itself** says only that it "overhauled the file format" because the old one was not efficient enough for small multiplayer messages [MPE], and that the server checkpoints the file "binary-encoded, compressed" [REL].
- **[unconfirmed by Figma]** That `.fig` files and multiplayer messages are Kiwi-encoded with an embedded schema is well established by third-party reverse engineering (e.g. https://grida.co/docs/wg/feat-fig/glossary/fig.kiwi). Figma publishes **no** official .fig spec; its public interfaces are the REST API and the Plugin API.

### 4.2 Size and memory
- Files reach "tens of megabytes" compressed and "hundreds of megabytes" in memory [AUTO]. People build documents "to the point of hitting memory limits". Serialising one large design-system file for a plugin took **14 s**, which is why plugins run against the live document instead of a serialised copy [PLUG].
- **Limit:** ~**2 GB per tab** (it can vary by device). Alerts appear at **60% / 75% / 100%**, and at 100% the file is locked until memory is reduced [MEM]. The desktop app has the same limit (same browser-based runtime, per the forum [secondary]).
- Loading every shared component at file open strained the backend as libraries approached ~10,000 elements, so clients moved to requesting library data on demand [INFRA].

### 4.3 Dynamic page loading [DPL][PLUGDL]
- The client now loads **the opened page plus its dependencies**; other pages load on demand. It first shipped for viewing and then for editors, since editable files are 70% of daily loads [DPL].
- **QueryGraph** is an in-memory, bidirectional dependency graph held by the Multiplayer server. **Read dependencies** are foreign keys such as an instance → its main component, styles and variables, which may live on other pages. **Write dependencies** are the inverse (editing a component needs its instances), plus implicit edges such as auto layout resizing cross-page siblings. They matter because clients cache derived data (e.g. text layout); a missed write dependency leaves that data stale [DPL].
- Multiplayer sends a client only the subgraph it has subscribed to; edits to nodes the client has not reached are not sent [DPL].
- **Rejected alternatives:** view-only until a full backfill finishes (no memory win), and a pull-based reactive data model (too big a change) [DPL].
- **Validation:** shadow mode for an extended period flagged any edit outside the predicted write set, which found a missed recursive cross-page dependency involving frame constraints and instances [DPL].
- **Results:** the slowest 5% of loads are **33% faster**, even as files grew 18% year over year; **70% fewer nodes in memory**; **33% fewer users hitting out-of-memory**. Preloading on a backend hint before the WebSocket opens saves **300-500 ms at p75**. Persisting raw chunk offsets lets decoding run across CPU cores, cutting decode time by **>40%** (serial decode could exceed 5 s on the largest files). Instance sublayers on other pages are materialised lazily. Rollout took six months of A/B tests [DPL].
- For plugins: the manifest key `documentAccess: "dynamic-page"` and async APIs (e.g. loading a page before reading it) [PLUGDL].

---

## 5. Branching and version history
- **Version history** works like commits: autosave describes a checkpoint as "a feature in Figma similar to a Git commit", made automatically before and after an offline diff is applied [AUTO]. The help centre says a new checkpoint is recorded **every 30 minutes** of activity (Figma help, via search; the exact page was not fetched, so treat this as [secondary]).
- On the server, the checkpoint/journal pair (S3 snapshot + sequence-numbered log) is the natural basis for versions [REL]. Figma has **not published** an engineering post on how version history or branching is stored or merged; I found none.
- **Branching** (from Figma's product docs): a branch is file-scoped. Checkpoints are made when a branch is created and when it is merged, with an extra checkpoint on main before the merge. A merged branch is archived with its comments and cannot be restored; to undo a merge you restore an earlier version of main [BR]. The whole branch merges at once; partial merges are a common user request (forum [secondary]). The conflict UI picks one side per conflicting layer **[secondary, not confirmed by Figma docs]**.

---

## 6. What Hoola can realistically replicate on one Python VPS (FastAPI + SQLite/Postgres), and what it cannot

Hoola today: one FastAPI process under pm2, SQLite by default (Postgres optional), an SSE/WebSocket event bus (`app/events.py`), a worker loop, and a few to a few hundred concurrent editors per tenant at most. Figma's scale numbers (2.2B changes a day, ~100x DB growth) do not apply. Most of its *algorithms* are deliberately simple and transfer directly.

### 6.1 Can replicate, essentially as published
1. **The document model**: one table, `doc_props(doc_id, object_id, prop, value_json, seq)`, or an in-memory `dict[obj_id][prop]` per open doc. This is literally Figma's `(ObjectID, Property, Value)` [MP].
2. **Server-authoritative per-property LWW**: the server's arrival order is the truth. No OT, no CRDT library. ~200 lines of Python.
3. **Client-made IDs**: `"{session_id}:{counter}"` [MP]. Offline creation works with no round trip.
4. **Fractional indexing**: base-95 (or base-62) string keys strictly between 0 and 1, with the server de-duplicating collisions [SEQ]. Pure Python; a known public algorithm (the `fractional-indexing` package family implements it).
5. **Parent+position as one property, plus a server-side cycle check**: walk the ancestors on every parent write and reject a write that would create a cycle [MP]. O(depth), trivial at Hoola's sizes.
6. **Optimistic client + "ignore server echoes for my unacked props"** [MP], and **client-local undo** that records overwritten values at undo time [MP]. Both are front-end work in the console JS / Flutter.
7. **Presence**: cursors and selections as ephemeral messages on the existing bus, never persisted, throttled to ~10-30 Hz, follow mode as a client toggle [MPE].
8. **One authoritative in-memory doc per open file, inside the single FastAPI process**, guarded by an `asyncio.Lock` per doc. Figma needed a process per document because one Node thread stalled on huge files [RUST]. At Hoola's file sizes, one asyncio process with small per-doc state works, **provided** encode/serialise runs via `asyncio.to_thread` (the same event-loop lesson as v0.640-v0.645).
9. **Journal + checkpoint durability**: append batched changes with `(doc_id, seq_start, seq_end, blob)` to SQLite in WAL mode (or Postgres) every ~0.5 s; snapshot the whole doc (msgpack or JSON + zstd) to disk or object storage every ~60 s and on idle; recover = snapshot + replay seq > snapshot.seq [REL]. Add the **byte-for-byte replay check** in a test [REL]. A single-row "owner lock" with a fencing token matters only once there is more than one worker; with one pm2 process it is free.
10. **Offline rebase**: the client keeps pending property sets per node in IndexedDB (web) / sqflite (phone), re-sends them on reconnect, and the server applies them as new LWW writes; checkpoint before and after the rebase [AUTO]. Version history = named snapshot rows.
11. **LiveGraph-lite for non-document data**: Hoola already pushes events on `bus.publish`. An *invalidation* model (a write to table X → `invalidate(query_key)` → the client re-fetches) is the LiveGraph-100x insight [LG2], and it fits a single process with no WAL tailing. On Postgres, `LISTEN/NOTIFY` from triggers is the cheap version of tailing the replication stream [LG1]. Logical-replication tailing is possible later but not needed.
12. **Dynamic page loading, simplified**: send the opened page's subtree plus its explicit read dependencies (component/style ids) first, then the rest lazily; subscribe each client only to the pages it has loaded [DPL]. Hoola's documents are small, so the write-dependency graph can start as "explicit foreign keys only".
13. **Schema-based binary encoding**: optional. Kiwi has JS/C++/Rust ports but no maintained Python port, so msgpack (or CBOR) with a versioned field map gives most of the benefit [KIWI]. JSON is fine until messages are measured as too large.

### 6.2 Can replicate only partially
- **Branching**: a branch = a copied snapshot plus its own journal from a base seq. Merge = a three-way diff of `(object, prop)` maps (base vs branch vs main), with conflicts resolved as pick-a-side per property or layer. This is doable in Python because the property map makes diffs mechanical. Figma's own merge internals are unpublished, so this design is ours, not a copy [BR].
- **Geo-distribution**: one VPS means one region. A CDN can serve static assets, but every edit round-trips to the box.
- **The rich-text story**: Figma's text property is atomic LWW ("AB or BC, never ABC") [MP]. Copying it gives the same limitation. Character-level co-editing of the same text box would need a real sequence CRDT (e.g. Yjs/`pycrdt`) for that one property type.

### 6.3 Cannot replicate (and should not try)
- **Process-per-document Rust servers and a fleet of them** [RUST]: no need at this scale, and one VPS cannot isolate a pathological file from the others the way separate processes do. Mitigation: per-doc size caps and off-loop serialisation.
- **DynamoDB-grade journal throughput and the cross-region replication SLA** (<30 min to another region) [REL]: a single box has one disk. The realistic substitute is the existing off-server backup (v0.237) of snapshots plus journal.
- **Horizontal Postgres sharding, DBProxy, colos** [DB]: irrelevant until one Postgres is saturated. The transferable lesson is to *pick shard-able keys now* (tenant_id / file_id on every row) and to put new table groups in their own DB file or schema (the cheap vertical-partitioning lever).
- **LiveGraph 100x's three sharded Go tiers and cuckoo-filter fan-out** [LG2]: designed for millions of sessions; a single-process invalidation map does the same job for Hoola.
- **A 2 GB, WASM/C++ client renderer that handles hundreds-of-MB documents** [MEM][AUTO]: that is Figma's client engine, not backend; out of scope for a FastAPI server and the current Flutter/vanilla-JS clients.
- **Figma's .fig compatibility**: there is no official spec, and the format is reverse-engineered [4.1]. Use the official REST/Plugin APIs (and the Figma MCP) for any import/export; never ship a .fig parser that would break silently.

### 6.4 Suggested minimal build order (if Hoola ever adds co-editing)
1. Property-map model + server LWW + seq journal in SQLite (WAL) + 60 s snapshots + replay test.
2. WebSocket per open doc with optimistic clients, the unacked-echo rule, and presence on the bus.
3. Fractional indexing, parent+position as one property, cycle rejection.
4. Offline queue + rebase with before/after snapshots; named versions.
5. Invalidation-based live queries for side data; page-scoped subscriptions.
6. Branch = snapshot fork + three-way property merge.

Each step is independently testable on one box. None of steps 1-5 needs a new pip dependency beyond what a FastAPI app already has (optionally `msgpack`/`zstandard`).
