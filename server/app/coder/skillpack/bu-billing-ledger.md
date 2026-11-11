---
name: bu-billing-ledger
description: Billing ledger - ai_kharcha, tally, sheets, printed
when_to_use: billing, invoices, subscriptions, AI spend, how much did I spend, kharcha, tally export, expense sheet, usage cost report
---
GOAL: the awesome-billing catalog of billing tools is the syllabus -
patterns for invoicing, subscriptions, tax and reconciliation. But
the lane runs through Hoola's own doors. In a BYOK world the real
work is usage accounting: per-tenant metering (the usage module)
keeps a separate account for every tenant, ai_kharcha shows the AI
spend inside it, and from that comes the month-end ledger - and from
the ledger, the invoice.

THE DOORS (all real operator tools):
1. ai_kharcha: the AI spend account - which tenant, which model, how
   much. Read metered usage here; this is the number that goes into
   the ledger, never an estimate. Small reads through the month add
   up to the big month-end account.
2. paisa: the money view lane - revenue, dues and adjustments at a
   glance. Look here before closing the month; what shows here is
   what goes into the sheet.
3. sheet_create / sheet_write_range: the month-end ledger is built
   in sheets - each row an account, each column a category / day;
   printed, shareable, and in plain sight.
4. sheet_milaan: reconcile - match the statement / paisa view
   against the sheet; what matches is ticked, what does not goes on
   a DIFF list and is never hidden.
5. tally_entry: an invoice / entry in Tally - Tally is ALREADY
   semantic, so an entry is made through its own fields, not as
   free-text mess.
6. tally_report: the report of posted entries - balance,
   outstanding and GSTR-ready numbers come from here.
7. gst: for tax calculation - rates, slabs and filing columns come
   through this door.
8. memory_search / remember: a reason card for every adjustment -
   who, when, why. The ledger does not remember reasons; the card
   does.

THE LAWS: money = ask_approval ALWAYS - whether sending an invoice,
giving a credit or correcting a number; printed output is the only
evidence - every invoice has printed line-item proof (what, how
much, at what rate, how much tax); every adjustment in the ledger
carries a written reason, a blank adjustment is not an adjustment;
only the source is the source of truth - ai_kharcha, tally_report,
paisa - an old number written on a sheet never becomes a source;
private data never leaves the tenant, and reconciliation also
happens inside the tenant.

NEVER: round a number silently - even a fraction of a paisa is
written down or asked about; issue an invoice without printed line
items; move money without approval; fix the ledger from the ledger -
go back to the source, not the sheet; send client data outside -
reconciliation, reports, everything stays inside the tenant; leave a
bill's entry and its printed proof in different places - both go on
the same card.

ALSO ASKED AS (Hinglish asks this skill answers): is mahine ka kharcha kitna
hua, AI ka bill dikhao, invoice banao, hisaab milao, tally mein entry daalo
