---
name: db-scale-path
description: SQLite to Postgres - dbmove path, printed row proof
when_to_use: postgres, move from sqlite, database slow, scale database, migrate database, too many users, database growing
---
GOAL: the mem-store is SQLite today (app/db.py) - one user, one file, it
works. When multi-user use or traffic arrives, Postgres (app/pgdb + the
postgres tool) is the answer - and that journey runs through the
app/dbmove.py lane, not by hand table by table. Production SQLite /
Postgres migration guides (generic) are the syllabus: the path is the
well-known one - backup, schema map, batched copy, row counts on both
sides, then cutover. The order never breaks.

THE PATH (dbmove lane, step by step):
1. BACKUP FIRST: copy the old SQLite file and print its name
   (app.db.bak-<date>). No step 2 without a backup.
2. SCHEMA MAP PRINTED: every table, every column, every index, every FK -
   read them from app/db.py and put the whole map in the output. What is
   not in the printed map was not migrated - creating a table from a
   guess is not allowed.
3. COPY IN BATCHES: data batch by batch (LIMIT / OFFSET or id ranges);
   print the count when each batch finishes. If one batch fails, stop -
   do not leave it half migrated, start again from that same batch.
4. ROW COUNTS ON BOTH SIDES: print the row count of source and target,
   table by table; only a diff of zero passes. With a count gap left it
   is not a cutover, only haste.
5. CUTOVER ONCE: switch to app/pgdb, change the config in one place
   only. The old SQLite file stays sacred until the approval window - do
   not delete / rename it, it may only be read.

THE LAWS: every destructive step (removing the old file, dropping
tables, schema migration) only after ask_approval - ask first, then run.
Printed output is the only evidence - paste the counts of both sides
before saying "migration is done". Freeze new features during the
migration - new work on a half-migrated codebase breeds bugs. Private
rows never go outside as "test data" - build sample data inside the
tenant too (sheet_create in-tenant). Write the rollback plan first:
restoring the backup is one command, and that is the safety. Compare the
content of sample rows in two or three places too - counts can match
while a content mismatch stays hidden.

RIGHT TIME (signals): two users colliding on the same file, writes
getting slow, a long backup window - only then start the path; a small
single-user app is happy on SQLite, and a migration is not for show.
Through the whole journey write each step's status in data_note (backup
name, batch range, counts) - the next turn starts from that printed
note, not from memory. When high traffic arrives, first load-test
through the postgres read doors (data_read / data_fetch), then pick the
cutover day.

NEVER: migrate without a backup; cut over without row-count proof (both
sides printed, diff zero); delete the old DB freely - the approval
window has not come until it has; add a new feature mid-migration; send
private rows outside as test data; say "all good" without a
sample-content check.

ALSO ASKED AS (Hinglish asks this skill answers): database bahut slow chal
raha hai, users badh gaye, sqlite se postgres pe le jao
