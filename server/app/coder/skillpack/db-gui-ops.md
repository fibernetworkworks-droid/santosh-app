---
name: db-gui-ops
description: DB GUIs via ax tree - browse, query, export, approved
when_to_use: pgadmin, dbeaver, tableplus, database GUI, run a query, export table, browse database, sql client, database tool
---
GOAL: DB GUI tools (the pgAdmin, DBeaver, TablePlus shapes; also others
like Beekeeper, Adminer, DataGrip) can be controlled semantically - drive
them by their structure, not by pixels. mgramin/awesome-db-tools = the ops
kit syllabus: which GUI / CLI is useful when, which tool fits which
database - every entry in the catalog is a search term, not an install
command. Hoola drives these GUIs through its operator doors.

THE DOORS (all real operator tools, the pixel lane last):
1. ax_find first: the connection tree, the query tab, the results grid -
   all are found by role / name (role=tree name=Servers, role=tab
   name=Query, results grid role=table). A screenshot only when ax gives
   no answer.
2. page_fill_form: fill the connection dialog (host, port, user, password,
   dbname) with form-fill, not click by click. Credentials are the
   tenant's and do not leave it.
3. postgres / data_read / data_fetch: when browsing in the GUI is slow
   there are direct data lane doors too - the GUI is then for visual
   proof, the true data comes from the data doors.
4. sheet_create / sheet_read / sheet_export / sheet_query: exports and
   result dumps go through this lane. Not the GUI's "Export CSV" button -
   output goes into a sheet inside the tenant and stays in-tenant.
5. data_note: schema notes (table, index, FK, column types) - write a
   note after every browse; the only memory is the printed note, not
   what you think you remember.
6. ask_approval: the only door for destructive SQL and migrations.

THE LAWS: semantic doors first, a pixel click last of all. Read-only by
default before running a query - write SELECT only; EXPLAIN shows the
plan without a mutation, so that first. DELETE / DROP / TRUNCATE, or an
UPDATE without WHERE - ask_approval first, then run. Work in the results
of the table you are browsing; put a LIMIT on big grids. Take a printed
row count after every query - "there were plenty of rows" is a guess,
the grid's number is the truth. If an unknown update / prompt appears in
the connection dialog, no blind OK - read it, understand it, then
ask_approval.

THE KIT (choose from awesome-db-tools): a lightweight GUI for quick peeks
(the Beekeeper / Adminer shape), the pgAdmin / DBeaver shape for deep
admin, psql and the data doors for bulk / automation. Search, compare,
then work in whatever is open - do not change the toolkit at every step.

NEVER: destructive SQL (DROP / DELETE / TRUNCATE / UPDATE without where)
without ask_approval; send exports outside the tenant - the sheet lane is
in-tenant too; a blind OK through the GUI's update / dialog prompts; say
"got the data" without a printed row count; migrations without approval;
paste credentials into chat.

ALSO ASKED AS (Hinglish asks this skill answers): database mein query
chalao, table export kar do, pgadmin mein data dekhna hai
