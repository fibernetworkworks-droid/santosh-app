---
name: bu-billing-ledger
description: Billing ledger - ai_kharcha, tally, sheets, printed
when_to_use: billing, invoices, subscriptions, AI spend, how much did I spend, kharcha, tally export, expense sheet, usage cost report
---
GOAL: billing-tools ka awesome-billing catalog syllabus hai - invoicing,
subscriptions, tax, reconciliation ke patterns. Par lane Hoola ke
apne doors se chalti hai. BYOK duniya me usage-accounting ki
evolution hi asli kaam hai: per-tenant metering (usage module) har
tenant ka apna khata rakhta hai, ai_kharcha usi me AI spend
dikhata hai, aur isi se month-end ledger banti hai - aur ledger se
invoice.

THE DOORS (sab operator ke asli tools):
1. ai_kharcha: AI spend ka khata - kis tenant, kis model, kitna.
   Metered usage yahan se padho; ledger me yahi number jaata hai,
   andaaz wala number nahi. Mahine bhar ke chhote reads hi
   month-end ka bada hisaab banate hain.
2. paisa: money view ki lane - revenue, dues, adjustments ka ek
   nazar. Month band karne se pehle yahan jhaanko; jo yahan
   dikhta hai wahi sheet me jaata hai.
3. sheet_create / sheet_write_range: month-end ledger sheets me
   banti hai - har row ek khata, har column ek category/din;
   printed, shareable, aur aankhon ke saamne.
4. sheet_milaan: reconcile - statement/paisa view ko sheet ke
   against milao; jo mila wo tick, jo na mile wo DIFF list,
   chhupaya nahi jaata.
5. tally_entry: invoice/entry Tally me - Tally PEHLE SE semantic
   hai, entry apne fields se hoti hai, free-text keechad nahi.
6. tally_report: posted entries ka report - balance, outstanding,
   GSTR-ready numbers yahin se aate hain.
7. gst: tax ke hisaab ke liye - rate, slabs, filing columns isi
   door se.
8. memory_search / remember: har adjustment ka reason-card - kaun,
   kab, kyun. Ledger khud reason yaad nahi rakhta, card rakhta hai.

THE LAWS: paisa = ask_approval ALWAYS - invoice bhejni ho, credit
dena ho, ya koi number theek karna ho; printed output hi evidence -
har invoice ka printed line-items proof hoga (kya, kitna, kis rate,
kitna tax); ledger me har adjustment ke saath reason likha jaata
hai, blank adjustment = adjustment nahi; source of truth sirf
source hai - ai_kharcha, tally_report, paisa - sheet pe likha hua
purana number kabhi source nahi banta; private data tenant se
bahar kabhi nahi jaata, reconcile bhi tenant ke andar hota hai.

NEVER: number silently round karna - paise ka fraction bhi likha
jaata hai ya poochha jaata hai; bina printed line-items invoice
jaari karna; money move bina approval; ledger ko ledger se fix
karna - source se aao, sheet se nahi; client data bahar bhejna -
reconcile, report, sab tenant ke andar; bill ki entry aur uska
printed proof alag jagah chhodna - dono ek hi card me.
