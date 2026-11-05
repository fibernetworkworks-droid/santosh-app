---
name: byox-database
description: Build a database: B-tree, SQL parser, WAL, buffer pool, MVCC
---
GOAL: a database that persists data to disk, parses SQL, and survives a crash.

PHASES
1. In-memory key/value store (hash table); get/put/delete; benchmarks.
2. B-tree paged on disk: insert, search, split; fixed-size 4 KB pages.
3. SQL lexer + recursive-descent parser: CREATE TABLE, INSERT, SELECT WHERE.
4. Write-Ahead Log: append before write; replay on startup; checkpoint.
5. Buffer pool (LRU eviction) + MVCC: snapshot reads, serialisable writes.

CORE CONCEPTS
- B-tree node: page_id, keys[], child_page_ids[]; leaf node stores values.
- WAL: every write appends (LSN, page_id, before, after); replay on restart.
- MVCC: each row has xmin/xmax; a read sees rows where xmin<=txid<xmax.

LANGUAGE: C for page-level work; Rust or Go for safety with similar performance.

VERIFY: insert 10k rows, kill -9 the process, restart — all rows intact.
