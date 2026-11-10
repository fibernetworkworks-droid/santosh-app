---
name: byox-git
description: Build a Git clone: objects, refs, commit, diff, log, clone
when_to_use: own git, git clone from scratch, version control system
---
GOAL: a working `ugit` or `gitlet` that creates commits, reads history and clones.

PHASES
1. init: create .git/objects, .git/refs/heads, HEAD pointing to main.
2. hash-object: zlib-compress + store blob under .git/objects/ab/cdef….
3. write-tree (tree object from index) + commit-tree (commit object).
4. checkout, diff (Myers LCS), log (walk parent chain via commit.tree.parent).
5. clone over HTTP: smart HTTP pack protocol; fetch pack + index-pack.

CORE CONCEPTS
- Object format: "<type> <size>\0<content>"; SHA-1 of this is the object id.
- Packfile delta: ref-delta and ofs-delta reduce storage by encoding diffs.
- Index file: sorted list of path/SHA/mode/stat entries; binary format.

VERIFY: `ugit commit -m "init"` then `ugit log` shows the commit with correct hash.
