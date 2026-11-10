---
name: db-gui-ops
description: DB GUIs via ax tree - browse, query, export, approved
when_to_use: pgadmin, dbeaver, tableplus, database GUI, run a query, export table, browse database, sql client, database tool
---
GOAL: DB GUI tools (pgAdmin, DBeaver, TablePlus shapes; Beekeeper, Adminer,
DataGrip jaise aur bhi) semantically controllable hain - unhe pixel se
nahi, unke structure se chalana hai. mgramin/awesome-db-tools = the ops
kit syllabus: kaunsa GUI/CLI kab kaam aayega, kis database ke liye kya
tool hai - catalog me har entry ek search term hai, install command nahi.
Hoola in GUIs ko apne operator doors se chalati hai.

THE DOORS (sab operator ke asli tools, pixel lane aakhri me):
1. ax_find pehle: connection tree, query tab, results grid - sab role/name
   se milte hain (role=tree name=Servers, role=tab name=Query, results
   grid role=table). Screenshot sirf tab jab ax jawab na de.
2. page_fill_form: connection dialog (host, port, user, password, dbname)
   form-fill se bharo, click-by-click nahi. Creds tenant ke, bahar nahi.
3. postgres / data_read / data_fetch: jab GUI browse slow ho, seedha data
   lane ke bhi doors hain - GUI tab visual proof ke liye, sach data doors
   se aata hai.
4. sheet_create / sheet_read / sheet_export / sheet_query: exports aur
   result dumps isi lane se. GUI ka "Export CSV" button nahi - output
   tenant ke andar sheet me jaata hai, in-tenant hi rehta hai.
5. data_note: schema notes (table, index, FK, column types) - har browse
   ke baad note likho; yaad sirf printed note hai, mann ki nahi.
6. ask_approval: destructive SQL aur migrations ke liye akela darwaza.

THE LAWS: semantic doors pehle, pixel click sabse aakhri me. Query run
se pehle read-only default - SELECT hi likho; EXPLAIN bina mutation ke
plan dikhata hai, pehle wahi. DELETE/DROP/TRUNCATE, ya UPDATE bina WHERE
- ask_approval pehle, phir run. Jo table browse kar rahe ho usi ke
results me kaam; bade grids pe LIMIT lagao. Har query ke baad row-count
printed lo - "kaafi rows the" andaaz nahi, grid ka number sach hai.
Connection dialog me unknown update/prompt aaye to blind OK nahi - padho,
samjho, phir ask_approval.

THE KIT (awesome-db-tools se chuno): quick peeks ke liye lightweight GUI
(Beekeeper/Adminer shape), deep admin ke liye pgAdmin/DBeaver shape,
bulk/automation ke liye psql aur data doors. Search karo, compare karo,
phir jo khula hai usi me kaam - har step pe toolkit badalna nahi.

NEVER: destructive SQL (DROP/DELETE/TRUNCATE/UPDATE bina where) bina
ask_approval; exports tenant ke bahar bhejna - sheet lane bhi in-tenant;
GUI ke update/dialog prompts ke through blind OK; bina row-count printed
"data mil gaya" bolna; migrations bina approval; creds chat me paste karna.
