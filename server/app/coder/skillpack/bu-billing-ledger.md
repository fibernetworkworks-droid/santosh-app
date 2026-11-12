---
name: bu-billing-ledger
description: Billing ledger - ai_kharcha, tally, sheets, printed
when_to_use: billing, invoices, subscriptions, AI spend, how much did I spend, kharcha, tally export, expense sheet, usage cost report
---
GOAL: the awesome-billing catalog is the syllabus for billing tools -
invoicing, subscriptions, tax and reconciliation patterns. But the lane
runs on Hoola's own doors. In a BYOK world the real work is usage
accounting: per-tenant metering (the usage module) keeps each tenant's
own ledger, ai_kharcha shows the AI spend from it, the month-end ledger
is built from that - and the invoice from the ledger.

THE DOORS (all real operator tools):
1. ai_kharcha: the AI spend ledger - which tenant, which model, how
   much. Read metered usage here; this is the number that goes into the
   ledger, never an estimate. Many small reads through the month make
   the big month-end picture.
2. paisa: the money view lane - revenue, dues and adjustments at a
   glance. Look here before closing the month; what shows here is what
   goes into the sheet.
3. sheet_create / sheet_write_range: the month-end ledger is built in
   sheets - each row one account, each column one category/day;
   printed, shareable, in plain sight.
4. sheet_milaan: reconcile - match the statement/paisa view against the
   sheet; what matches gets a tick, what does not goes on a DIFF list,
   nothing is hidden.
5. tally_entry: an invoice/entry in Tally - Tally is ALREADY semantic,
   the entry goes in through its own fields, no free-text mess.
6. tally_report: the report of posted entries - balance, outstanding and
   GSTR-ready numbers come from here.
7. gst: for tax calculation - rates, slabs and filing columns come from
   this door.
8. memory_search / remember: a reason card for every adjustment - who,
   when, why. The ledger does not remember the reason by itself; the
   card does.

THE LAWS: money = ask_approval ALWAYS - whether sending an invoice,
giving credit or correcting any number; printed output is the evidence -
every invoice has printed line-items as proof (what, how many, what
rate, how much tax); every ledger adjustment is written with its reason,
a blank adjustment is not an adjustment; the source of truth is only the
source - ai_kharcha, tally_report, paisa - an old number written on a
sheet never becomes the source; private data never leaves the tenant,
reconciliation also happens inside the tenant.

NEVER: silently round a number - even the fraction of a paisa is written
down or asked about; issue an invoice without printed line-items; move
money without approval; fix a ledger from the ledger - go to the source,
not the sheet; send client data outside - reconcile, report, all of it
stays inside the tenant; leave a bill's entry and its printed proof in
different places - both go in one card.
