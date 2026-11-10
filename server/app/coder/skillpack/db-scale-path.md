---
name: db-scale-path
description: SQLite to Postgres - dbmove path, printed row proof
when_to_use: postgres, move from sqlite, database slow, scale database, migrate database, too many users, database growing
---
GOAL: mem-store filhaal SQLite hai (app/db.py) - ek user, ek file, kaam chalta
hai. Jab multi-user ya traffic aaye, Postgres (app/pgdb + postgres tool)
hi jawab hai - aur ye safar app/dbmove.py lane se chalta hai, haath se
table-by-table nahi. Production-SQLite/Postgres migration guides (generic)
syllabus hain: path wahi purana hai - backup, schema map, batched copy,
dono side row counts, phir cutover. Order toot-ta nahi.

THE PATH (dbmove lane, step by step):
1. BACKUP PEHLE: purani SQLite file ki copy banao, naam printed likho
   (app.db.bak-<date>). Backup ke bina step 2 tak nahi.
2. SCHEMA MAP PRINTED: har table, har column, har index, har FK - app/db.py
   se padho, poora map output me daalo. Jo map print nahi hua, wo migrate
   nahi hua - andaaz se table banana mana hai.
3. COPY IN BATCHES: data batch-by-batch (LIMIT/OFFSET ya id ranges); har
   batch pura hone par count printed. Ek batch fail to ruk jao - aadha
   migrate chhodo nahi, phir se usi batch se shuru karo.
4. ROW COUNTS DONO SIDE: source aur target dono ke counts printed, table
   by table; diff zero hi pass hai. Count gap bacha to cutover ka naam
   nahi, sirf jaldi.
5. CUTOVER EK BAAR: app/pgdb pe switch, config ek hi jagah badlo. Purana
   SQLite file tab tak sacred hai jab tak approval-window na ho - use
   delete/rename nahi, sirf padha ja sakta hai.

THE LAWS: destructive steps (purana file hatana, tables drop, schema
migration) sab ask_approval ke baad - pehle poochho, phir chalao. Printed
output hi evidence hai - "migrate ho gaya" bolne se pehle dono side ke
counts paste karo. Migration ke dauran naya feature freeze - aadhe-
migrate codebase me naya kaam bugon ki khad hai. Private rows kabhi test
data ke naam pe bahar nahi - sample data bhi tenant ke andar banao
(sheet_create in-tenant). Rollback plan pehle likho: backup restore ek
command, yahi safety hai. Sample rows ka content bhi do-teen jagah
compare karo - count match, content mismatch chhup jaata hai.

RIGHT TIME (signals): do-do users ek hi file pe takra rahe hain, writes
slow ho gaye, backup window badi - tabhi path shuru karo; chhota single-
user app SQLite me hi khush hai, migration sirf dikhawa nahi. Poore
safar me data_note me har step ka status likho (backup naam, batch range,
counts) - agla turn wahi printed note se shuru hoga, yaad se nahi. High
traffic aane par pehle postgres ke read doors (data_read/data_fetch) se
load test karo, phir cutover ka din chuno.

NEVER: bina backup migrate karna; row-count proof (dono side printed,
diff zero) ke bina cutover; purani DB khushi se delete karna - approval
window tab tak nahi aayi; migration ke beech naya feature; private rows
ko test data ke naam pe bahar bhejna; bina sample-content check "sab
theek" bolna.
