"""Wave 1 tables of the Construction & Real Estate department (v0.512.0). Every table tenant-scoped,
nullable-safe on old rows (new tables only, so no migration risk), ids prefixed per domain:

- `cstore_*`  Material Planner & Store Manager (register #61): lots, GRN, issues, min-max.
- `clabour_*` Labour Compliance Desk + Wage & Payment Auditor (register #85, #87): muster, licences,
  statutory calendar rows, wage rates.
- `cbooks_*`  Builder's Accounting & Reconciliation (register #91): project-wise entries.
- `ccust_*`   Customer Payment & Demand-letter Manager + Handover / DLP (register #92, #98).
- `cqual_*`   Quality records (register #72 pour/cube drafts stay in sitesup; #75 ITP/NCR, #76 test lots).
- `cmeet_*`   Meeting Secretary (register #67): meetings, minutes lines, action items.

Pour / cube / snag / safety / progress tables stay in sitesup (they already live); this module never
duplicates them. Money never moves here: payouts and sends stay with the owner's tap (approval cards)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


# ---------------------------------------------------------------- #61 Material Planner & Store Manager
class CStoreLot(Base):
    __tablename__ = "cstore_lots"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("csl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    item: Mapped[str] = mapped_column(String(120), index=True)          # cement OPC 53 / steel Fe500D / aggregate ...
    unit: Mapped[str] = mapped_column(String(12), default="")
    min_qty: Mapped[float] = mapped_column(Float, default=0.0)          # reorder level (consumption norm)
    max_qty: Mapped[float] = mapped_column(Float, default=0.0)          # storage cap
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CStoreGrn(Base):
    """Goods received note: what arrived, from whom, against which PO / challan."""
    __tablename__ = "cstore_grn"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("csg"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    item: Mapped[str] = mapped_column(String(120), index=True)
    unit: Mapped[str] = mapped_column(String(12), default="")
    qty: Mapped[float] = mapped_column(Float, default=0.0)
    rate: Mapped[float] = mapped_column(Float, default=0.0)
    vendor: Mapped[str] = mapped_column(String(160), default="")
    invoice_no: Mapped[str] = mapped_column(String(60), default="")
    vehicle: Mapped[str] = mapped_column(String(40), default="")
    site: Mapped[str] = mapped_column(String(160), default="")
    day: Mapped[str] = mapped_column(String(10), index=True, default="")
    ok: Mapped[bool] = mapped_column(Boolean, default=True)             # quantity / quality accepted on check
    note: Mapped[str] = mapped_column(String(300), default="")
    by: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CStoreIssue(Base):
    """Issue to a gang / activity; `waste` marks a written-off issue (reconciliation counts it separately)."""
    __tablename__ = "cstore_issues"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("csi"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    item: Mapped[str] = mapped_column(String(120), index=True)
    unit: Mapped[str] = mapped_column(String(12), default="")
    qty: Mapped[float] = mapped_column(Float, default=0.0)
    site: Mapped[str] = mapped_column(String(160), default="")
    gang: Mapped[str] = mapped_column(String(120), default="")
    purpose: Mapped[str] = mapped_column(String(200), default="")
    day: Mapped[str] = mapped_column(String(10), index=True, default="")
    waste: Mapped[bool] = mapped_column(Boolean, default=False)
    by: Mapped[str] = mapped_column(String(80), default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# ---------------------------------------------------------------- #85 / #87 Labour Compliance Desk + Wage Auditor
class CLabourMuster(Base):
    """Daily muster roll row (from the sitesup attendance rows or spoken directly here)."""
    __tablename__ = "clabour_muster"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("clm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site: Mapped[str] = mapped_column(String(160), default="")
    day: Mapped[str] = mapped_column(String(10), index=True, default="")
    contractor: Mapped[str] = mapped_column(String(160), default="")    # the labour contractor (licence holder)
    trade: Mapped[str] = mapped_column(String(40), default="")
    present: Mapped[int] = mapped_column(Integer, default=0)
    absent: Mapped[int] = mapped_column(Integer, default=0)
    ot_hours: Mapped[float] = mapped_column(Float, default=0.0)
    wage_paid: Mapped[float] = mapped_column(Float, default=0.0)        # recorded by the auditor AFTER her payment
    wage_basis: Mapped[str] = mapped_column(String(20), default="")     # day | hour | piece (uom)
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CLabourLicence(Base):
    """Contract-labour licence, BOCW registration, EPF/ESIC - anything with a renewal date on the calendar."""
    __tablename__ = "clabour_licences"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cll"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(40), default="")           # contract_labour | bocw | epf | esic | other
    number: Mapped[str] = mapped_column(String(80), default="")
    authority: Mapped[str] = mapped_column(String(160), default="")
    holder: Mapped[str] = mapped_column(String(160), default="")        # the labour contractor / firm it names
    site: Mapped[str] = mapped_column(String(160), default="")
    valid_from: Mapped[str] = mapped_column(String(10), default="")
    valid_to: Mapped[str] = mapped_column(String(10), index=True, default="")
    status: Mapped[str] = mapped_column(String(12), default="valid")    # applied | valid | expired
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CLabourWage(Base):
    """Her wage rate per trade / gang with its basis and source (her word, agreement, or a notified rate she typed)."""
    __tablename__ = "clabour_wages"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("clw"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    trade: Mapped[str] = mapped_column(String(60), index=True, default="")
    site: Mapped[str] = mapped_column(String(160), default="")
    rate: Mapped[float] = mapped_column(Float, default=0.0)
    basis: Mapped[str] = mapped_column(String(20), default="day")       # day | hour | piece
    wef: Mapped[str] = mapped_column(String(10), default="")            # effective from
    source: Mapped[str] = mapped_column(String(200), default="")        # where the number came from (never invented)
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# ---------------------------------------------------------------- #91 Builder's books
class CBookEntry(Base):
    """One project-wise book line. side=in (receipt) | out (payment / due). head keeps the books sane
    (labour | material | hire | subcontract | approval | misc | receipt). Money itself still moves on her tap."""
    __tablename__ = "cbooks_entries"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cbe"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    day: Mapped[str] = mapped_column(String(10), index=True, default="")
    party: Mapped[str] = mapped_column(String(160), index=True, default="")
    side: Mapped[str] = mapped_column(String(6), default="out")         # in | out
    head: Mapped[str] = mapped_column(String(40), default="misc")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    settled: Mapped[bool] = mapped_column(Boolean, default=True)        # False = due (vendor ageing)
    due_day: Mapped[str] = mapped_column(String(10), default="")
    ref: Mapped[str] = mapped_column(String(120), default="")           # bill / voucher no
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# ---------------------------------------------------------------- #92 / #98 Customer money + handover
class CCustDemand(Base):
    """Milestone-linked demand letter for a booked unit. The letter is drafted; `sent` only on her haan."""
    __tablename__ = "ccust_demands"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ccd"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    unit: Mapped[str] = mapped_column(String(60), default="")
    customer: Mapped[str] = mapped_column(String(160), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    milestone: Mapped[str] = mapped_column(String(200), default="")     # plinth / slab 4 / registration ...
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    due: Mapped[str] = mapped_column(String(10), default="")
    interest_pct: Mapped[float] = mapped_column(Float, default=0.0)     # her agreement's clause, printed on the letter
    status: Mapped[str] = mapped_column(String(10), default="draft")    # draft | sent | paid | part
    sent_on: Mapped[str] = mapped_column(String(10), default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CCustReceipt(Base):
    __tablename__ = "ccust_receipts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ccr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    demand_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    project: Mapped[str] = mapped_column(String(160), default="")
    unit: Mapped[str] = mapped_column(String(60), default="")
    customer: Mapped[str] = mapped_column(String(160), default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    mode: Mapped[str] = mapped_column(String(20), default="")           # neft | rtgs | cheque | upi | loan
    day: Mapped[str] = mapped_column(String(10), default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CHandover(Base):
    """Possession checklist per unit; snag closure reads sitesup snags; keys and utilities recorded after the fact."""
    __tablename__ = "ccust_handover"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cch"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    unit: Mapped[str] = mapped_column(String(60), default="")
    customer: Mapped[str] = mapped_column(String(160), default="")
    items: Mapped[str] = mapped_column(Text, default="[]")              # [{item, done(bool), day, note}]
    snags_open: Mapped[int] = mapped_column(Integer, default=0)
    keys_on: Mapped[str] = mapped_column(String(10), default="")
    utilities: Mapped[str] = mapped_column(String(300), default="")     # meter / water / society transfers
    status: Mapped[str] = mapped_column(String(12), default="open")     # open | ready | handed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CDlpTicket(Base):
    """Defect-liability-period ticket after possession; the DLP clock is arithmetic from the agreement months."""
    __tablename__ = "ccust_dlp"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cct"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    unit: Mapped[str] = mapped_column(String(60), default="")
    customer: Mapped[str] = mapped_column(String(160), default="")
    issue: Mapped[str] = mapped_column(Text, default="")
    trade: Mapped[str] = mapped_column(String(40), default="")
    vendor: Mapped[str] = mapped_column(String(160), default="")
    opened_on: Mapped[str] = mapped_column(String(10), default="")
    dlp_until: Mapped[str] = mapped_column(String(10), index=True, default="")
    vendor_sent_on: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(12), default="open")     # open | vendor_sent | fixed | closed
    closed_on: Mapped[str] = mapped_column(String(10), default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# ---------------------------------------------------------------- #75 / #76 Quality records
class CItp(Base):
    """Inspection & test plan for one activity: steps with their spec and the HOLD points (the QA manager's plan)."""
    __tablename__ = "cqual_itps"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cip"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site: Mapped[str] = mapped_column(String(160), index=True, default="")
    activity: Mapped[str] = mapped_column(String(200), default="")
    steps: Mapped[str] = mapped_column(Text, default="[]")              # [{step, spec, hold}]
    status: Mapped[str] = mapped_column(String(12), default="draft")    # draft | approved (by the QA manager's word)
    approved_by: Mapped[str] = mapped_column(String(120), default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CNcr(Base):
    """Non-conformance report: what failed which spec, severity, and its close-out (closing is the QA/QC manager's word)."""
    __tablename__ = "cqual_ncrs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cnc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site: Mapped[str] = mapped_column(String(160), index=True, default="")
    activity: Mapped[str] = mapped_column(String(200), default="")
    defect: Mapped[str] = mapped_column(Text, default="")
    spec: Mapped[str] = mapped_column(String(300), default="")          # the clause / spec it failed
    severity: Mapped[str] = mapped_column(String(12), default="minor")  # minor | major | critical
    action: Mapped[str] = mapped_column(String(300), default="")        # rework / reject / review
    status: Mapped[str] = mapped_column(String(12), default="open")     # open | actioned | closed
    raised_on: Mapped[str] = mapped_column(String(10), default="")
    closed_on: Mapped[str] = mapped_column(String(10), default="")
    itp_id: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CTestLot(Base):
    """Material test register: NABL lab results against cement / steel / aggregate lots, with retest dates."""
    __tablename__ = "cqual_test_lots"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ctl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(60), default="")           # cement OPC 53 lot / steel Fe500D heat / aggregate
    vendor: Mapped[str] = mapped_column(String(160), default="")
    lot_no: Mapped[str] = mapped_column(String(80), default="")
    test: Mapped[str] = mapped_column(String(160), default="")          # 7/28-day cube, tensile, sieve ...
    lab: Mapped[str] = mapped_column(String(160), default="")
    result: Mapped[str] = mapped_column(String(300), default="")        # as reported by the lab, never interpreted
    verdict: Mapped[str] = mapped_column(String(20), default="pending") # pending | pass | fail (her / QC engineer's word)
    tested_on: Mapped[str] = mapped_column(String(10), default="")
    retest_due: Mapped[str] = mapped_column(String(10), index=True, default="")
    report_ref: Mapped[str] = mapped_column(String(120), default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# ---------------------------------------------------------------- #67 Meeting Secretary
class CMeet(Base):
    __tablename__ = "cmeets"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cmt"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    kind: Mapped[str] = mapped_column(String(20), default="site")       # oac | site | coord | client | weekly
    day: Mapped[str] = mapped_column(String(10), index=True, default="")
    site: Mapped[str] = mapped_column(String(160), default="")
    project: Mapped[str] = mapped_column(String(160), default="")
    attendees: Mapped[str] = mapped_column(String(400), default="")
    minutes: Mapped[str] = mapped_column(Text, default="[]")            # [{text, by}]
    status: Mapped[str] = mapped_column(String(10), default="open")     # open | minuted
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CActionItem(Base):
    """One action from a meeting, chased till closed (closed only on the owner's / PM's word)."""
    __tablename__ = "cmeet_actions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cma"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    meet_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    what: Mapped[str] = mapped_column(Text, default="")
    who: Mapped[str] = mapped_column(String(160), default="")
    due: Mapped[str] = mapped_column(String(10), index=True, default="")
    status: Mapped[str] = mapped_column(String(10), default="open")     # open | done
    done_on: Mapped[str] = mapped_column(String(10), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# ============================================================ WAVE 2 (v0.531.0) - file-builders & checkers
# ---------------------------------------------------------------- #28-32,34,36 Approvals office (C7)
class CApprovFile(Base):
    """One approval file with one authority: building permission, fire NOC, CTE/CTO, OC/CC,
    utility liaison. Submission is the owner's / named licensee's act (tier C) - Hoola assembles."""
    __tablename__ = "capprov_files"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("caf"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    authority: Mapped[str] = mapped_column(String(160), default="")     # MCGM / Fire / MPCB / MSEDCL / water board
    purpose: Mapped[str] = mapped_column(String(200), default="")       # building permission / fire NOC / OC ...
    kind: Mapped[str] = mapped_column(String(30), default="permission") # permission | noc | consent | certificate
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    # draft | ready | submitted | queried | approved | rejected
    licensee: Mapped[str] = mapped_column(String(120), default="")      # the named professional who files/certifies
    fee: Mapped[float] = mapped_column(Float, default=0.0)
    checklist: Mapped[str] = mapped_column(Text, default="[]")          # [{item, done, note}]
    ref_no: Mapped[str] = mapped_column(String(80), default="")         # authority's file / approval number
    submitted_on: Mapped[str] = mapped_column(String(10), default="")
    approved_on: Mapped[str] = mapped_column(String(10), default="")
    valid_till: Mapped[str] = mapped_column(String(10), default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CApprovDoc(Base):
    """One paper in a file: form, drawing set, ownership proof, NOC, undertaking - ready or needed."""
    __tablename__ = "capprov_docs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cad"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    file_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    kind: Mapped[str] = mapped_column(String(30), default="form")       # form | drawing | ownership | noc | undertaking | fee
    name: Mapped[str] = mapped_column(String(200), default="")
    ref: Mapped[str] = mapped_column(String(120), default="")           # docstudio / sheet / file reference
    status: Mapped[str] = mapped_column(String(20), default="needed")   # needed | ready
    note: Mapped[str] = mapped_column(String(200), default="")


class CApprovCal(Base):
    """Statutory calendar (#34): NOC renewals, consent validity, licence due dates - the dates SHE
    records; Hoola counts the days and shouts early, never decides the renewal."""
    __tablename__ = "capprov_calendar"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cac"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    authority: Mapped[str] = mapped_column(String(160), default="")
    item: Mapped[str] = mapped_column(String(200), default="")          # fire NOC renewal / CTO validity ...
    due_on: Mapped[str] = mapped_column(String(10), index=True, default="")
    last_done: Mapped[str] = mapped_column(String(10), default="")
    file_id: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(20), default="open")     # open | done
    note: Mapped[str] = mapped_column(String(200), default="")


# ---------------------------------------------------- #37-39,41,49 QS desk (C8): takeoff / rates / BOQ / budget
class CqsTakeoff(Base):
    """One measured line: the quantity WITH its formula trail (IS 1200) - qty, formula, inputs stored
    together; a recompute must reproduce the number bit-for-bit. Never a certificate of measurement."""
    __tablename__ = "cqs_takeoff"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cqo"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    item: Mapped[str] = mapped_column(String(200), default="")
    is_ref: Mapped[str] = mapped_column(String(80), default="")         # IS 1200 (Part 3) brickwork ...
    kind: Mapped[str] = mapped_column(String(30), default="")           # earthwork | concrete | brickwork | plaster ...
    unit: Mapped[str] = mapped_column(String(12), default="")
    qty: Mapped[float] = mapped_column(Float, default=0.0)
    formula: Mapped[str] = mapped_column(String(200), default="")
    inputs: Mapped[str] = mapped_column(Text, default="{}")             # exactly what was fed to the formula
    dwg_ref: Mapped[str] = mapped_column(String(80), default="")        # drawing no / sheet
    by: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CqsRate(Base):
    """Rate build-up (#38): component rows summed, overhead + profit applied, the SOURCE named
    (SOR item / quote). A rate without its source refuses to save."""
    __tablename__ = "cqs_rates"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cqr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    item: Mapped[str] = mapped_column(String(200), default="")
    unit: Mapped[str] = mapped_column(String(12), default="")
    analysis: Mapped[str] = mapped_column(Text, default="[]")           # [{head, qty, unit, rate, amount, source}]
    overhead_pct: Mapped[float] = mapped_column(Float, default=0.0)
    profit_pct: Mapped[float] = mapped_column(Float, default=0.0)
    rate: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(200), default="")        # SOR item no / quote ref
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CqsBoq(Base):
    """BOQ line (#39): takeoff qty x built-up rate = amount; the abstract totals by head."""
    __tablename__ = "cqs_boq"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cqb"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    item: Mapped[str] = mapped_column(String(200), default="")
    unit: Mapped[str] = mapped_column(String(12), default="")
    qty: Mapped[float] = mapped_column(Float, default=0.0)
    rate: Mapped[float] = mapped_column(Float, default=0.0)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    head: Mapped[str] = mapped_column(String(80), default="")           # abstract grouping
    takeoff_id: Mapped[str] = mapped_column(String(40), default="")
    rate_id: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CqsBudget(Base):
    """Cost controller (#41): budget vs committed vs actual per head - variance is arithmetic."""
    __tablename__ = "cqs_budget"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cqg"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    head: Mapped[str] = mapped_column(String(120), default="")
    budget: Mapped[float] = mapped_column(Float, default=0.0)
    committed: Mapped[float] = mapped_column(Float, default=0.0)
    actual: Mapped[float] = mapped_column(Float, default=0.0)
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# --------------------------------------------------------- #35,93 RERA & escrow (C9)
class CreraProject(Base):
    """The RERA project data pack: registration number, dates, escrow account - her facts, cited."""
    __tablename__ = "crera_projects"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("crp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(160), index=True, default="")
    maha_rera: Mapped[str] = mapped_column(String(60), default="")      # registration number (P51...)
    promoter: Mapped[str] = mapped_column(String(160), default="")
    start_on: Mapped[str] = mapped_column(String(10), default="")
    complete_on: Mapped[str] = mapped_column(String(10), default="")
    sanctioned_on: Mapped[str] = mapped_column(String(10), default="")
    escrow_acct: Mapped[str] = mapped_column(String(80), default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CreraUpdate(Base):
    """Quarterly update DRAFT: the percentages are the PROMOTER's own numbers - Hoola never computes
    a completion % (tier C). The filing is the promoter's act."""
    __tablename__ = "crera_updates"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cru"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    quarter: Mapped[str] = mapped_column(String(20), default="")        # 2026-Q4
    pct_complete: Mapped[float] = mapped_column(Float, default=0.0)     # AS THE PROMOTER SAYS
    units_booked: Mapped[int] = mapped_column(Integer, default=0)
    units_delivered: Mapped[int] = mapped_column(Integer, default=0)
    complaints: Mapped[int] = mapped_column(Integer, default=0)
    prepared_on: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(20), default="draft")    # draft | filed
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CreraForm(Base):
    """Form data pack (Form 3/4/5 or any numbered form): the DATA assembled with sources; the
    declaration is the named professional's - prepared_for is required, the sign line stays empty."""
    __tablename__ = "crera_forms"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("crf"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    form_no: Mapped[str] = mapped_column(String(30), default="")        # as the portal / rules name it
    purpose: Mapped[str] = mapped_column(String(200), default="")
    period: Mapped[str] = mapped_column(String(40), default="")
    data: Mapped[str] = mapped_column(Text, default="[]")               # [{item, value, source}]
    prepared_for: Mapped[str] = mapped_column(String(120), default="")  # the named CA / architect / engineer
    status: Mapped[str] = mapped_column(String(20), default="draft")    # draft | ready
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CreraEscrow(Base):
    """Escrow ledger (#93): receipts in; withdrawals out ONLY with the certificate reference of the
    engineer / architect / CA - a withdrawal without a certificate refuses to save."""
    __tablename__ = "crera_escrow"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cre"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    kind: Mapped[str] = mapped_column(String(20), default="receipt")    # receipt | withdrawal
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    day: Mapped[str] = mapped_column(String(10), index=True, default="")
    certificate_ref: Mapped[str] = mapped_column(String(120), default="")
    ref: Mapped[str] = mapped_column(String(120), default="")           # bank / invoice ref
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# --------------------------------------------------------- #44-46,51 Contracts desk (C10)
class CContract(Base):
    """Contract register: the paper's facts, the notice window from HER contract."""
    __tablename__ = "ccontr_contracts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cct"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    party: Mapped[str] = mapped_column(String(160), default="")
    role: Mapped[str] = mapped_column(String(30), default="contractor")  # employer | contractor | sub-contractor
    value: Mapped[float] = mapped_column(Float, default=0.0)
    signed_on: Mapped[str] = mapped_column(String(10), default="")
    start_on: Mapped[str] = mapped_column(String(10), default="")
    end_on: Mapped[str] = mapped_column(String(10), default="")
    notice_days: Mapped[int] = mapped_column(Integer, default=0)         # notice window as the contract says
    ref: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(20), default="open")      # open | closed | terminated
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CContrOblig(Base):
    """One obligation of one side, chased with the due date - notice-period alerts ride this."""
    __tablename__ = "ccontr_obligs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cco"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    contract_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    obligation: Mapped[str] = mapped_column(String(400), default="")
    due_on: Mapped[str] = mapped_column(String(10), index=True, default="")
    owner_side: Mapped[bool] = mapped_column(Boolean, default=True)      # whose obligation
    status: Mapped[str] = mapped_column(String(20), default="open")      # open | done
    done_on: Mapped[str] = mapped_column(String(10), default="")
    note: Mapped[str] = mapped_column(String(200), default="")


class CContrVariation(Base):
    """Variation paper DRAFT (#45): what changed, on what rate basis, the money - the approval is
    the client's (tier C); approved_by records THEIR name when she reports it."""
    __tablename__ = "ccontr_variations"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ccv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    contract_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    desc: Mapped[str] = mapped_column(String(500), default="")
    basis: Mapped[str] = mapped_column(String(200), default="")          # SOR item / quoted rate / daywork
    qty: Mapped[float] = mapped_column(Float, default=0.0)
    rate: Mapped[float] = mapped_column(Float, default=0.0)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    raised_on: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(20), default="draft")     # draft | submitted | approved | rejected
    approved_by: Mapped[str] = mapped_column(String(120), default="")    # the client's name, as she records it
    ref: Mapped[str] = mapped_column(String(120), default="")
    note: Mapped[str] = mapped_column(String(200), default="")


class CContrClaim(Base):
    """Claims working paper (#46): the entitlement matrix as she feeds it (event -> clause -> effect
    -> evidence) + the notice-compliance ARITHMETIC. Entitlement is counsel's conclusion, never
    Hoola's (tier C) - the paper ends where the advocate begins."""
    __tablename__ = "ccontr_claims"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ccl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    contract_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    cause: Mapped[str] = mapped_column(String(400), default="")
    event_on: Mapped[str] = mapped_column(String(10), default="")
    noticed_on: Mapped[str] = mapped_column(String(10), default="")
    notice_days: Mapped[int] = mapped_column(Integer, default=0)         # contract's notice window
    matrix: Mapped[str] = mapped_column(Text, default="[]")              # [{event, clause, effect, evidence}]
    status: Mapped[str] = mapped_column(String(20), default="draft")     # draft | submitted
    ref: Mapped[str] = mapped_column(String(120), default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# --------------------------------------------------------- #52-56,58 Tendering desk (C10)
class CTender(Base):
    """Tender watch: due date, EMD, scope, and the bid / no-bid sheet (her call, her reasons)."""
    __tablename__ = "ctend_tenders"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ctn"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    authority: Mapped[str] = mapped_column(String(160), default="")
    due_on: Mapped[str] = mapped_column(String(10), index=True, default="")
    emd: Mapped[float] = mapped_column(Float, default=0.0)
    scope: Mapped[str] = mapped_column(String(300), default="")
    status: Mapped[str] = mapped_column(String(20), default="watch", index=True)
    # watch | bid | no_bid | submitted | won | lost
    reasons: Mapped[str] = mapped_column(Text, default="[]")             # bid/no-bid sheet [{factor, note}]
    ref: Mapped[str] = mapped_column(String(120), default="")
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CTendPack(Base):
    """Pre-qualification dossier (#55) / bid price pack (#54): rows she feeds, each with its source."""
    __tablename__ = "ctend_packs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ctp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    tender_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    kind: Mapped[str] = mapped_column(String(20), default="prequal")     # prequal | price
    rows: Mapped[str] = mapped_column(Text, default="[]")                # [{item, value, source}]
    prepared_on: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(20), default="draft")     # draft | ready
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CTendVendor(Base):
    """Vendor developer (#58): the register with HER ratings - Hoola keeps the score, never makes it."""
    __tablename__ = "ctend_vendors"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ctv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    vendor: Mapped[str] = mapped_column(String(160), index=True, default="")
    scope: Mapped[str] = mapped_column(String(200), default="")
    rating: Mapped[str] = mapped_column(String(20), default="watch")     # preferred | ok | watch | blocked
    last_work: Mapped[str] = mapped_column(String(200), default="")
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# --------------------------------------------------------- #9,16,73 Drawing QA (C10)
class CDraw(Base):
    """Drawing register: dwg no, revision, scale-as-noted, source - PDF/DWG-first, document-level."""
    __tablename__ = "cdraw_drawings"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cdw"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    dwg_no: Mapped[str] = mapped_column(String(80), default="")
    rev: Mapped[str] = mapped_column(String(20), default="")
    kind: Mapped[str] = mapped_column(String(60), default="")            # plan / section / structural / services
    scale_as_noted: Mapped[str] = mapped_column(String(60), default="")
    source: Mapped[str] = mapped_column(String(120), default="")         # file / sheet reference
    status: Mapped[str] = mapped_column(String(20), default="received")  # received | under_check | returned | ok_drafted
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CDrawRule(Base):
    """Bye-law rules as DATA: her sourced rows (clause + source required), project-specific limits
    alongside the state pack's determined rows. A rule without its clause refuses to save."""
    __tablename__ = "cdraw_rules"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cdr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    rule_id: Mapped[str] = mapped_column(String(60), index=True, default="")
    text: Mapped[str] = mapped_column(String(300), default="")
    limit_value: Mapped[float] = mapped_column(Float, default=0.0)
    direction: Mapped[str] = mapped_column(String(10), default="max")   # min (setbacks) | max (FAR, height)
    unit: Mapped[str] = mapped_column(String(20), default="")
    clause: Mapped[str] = mapped_column(String(160), default="")
    source: Mapped[str] = mapped_column(String(200), default="")
    checked_on: Mapped[str] = mapped_column(String(10), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CDrawCheck(Base):
    """Declared value vs rule limit: the verdict is ARITHMETIC (value > limit = breach), never an
    approval - the Drawing QA Reviewer (the project architect) owns the outcome (tier B)."""
    __tablename__ = "cdraw_checks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cdc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    drawing_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    rule_id: Mapped[str] = mapped_column(String(60), index=True, default="")
    declared: Mapped[float] = mapped_column(Float, default=0.0)
    limit_value: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(20), default="")
    verdict: Mapped[str] = mapped_column(String(20), default="pending")  # pending | ok | breach
    checked_on: Mapped[str] = mapped_column(String(10), default="")
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# --------------------------------------------------------- #81 EHS permits & toolbox (C10, rides quality)
class CQualPermit(Base):
    """Permit-to-work DRAFT: hazard + controls as data; ISSUED only on the safety officer's named
    word (tier C - the permit is hers; Hoola prepares the paper and keeps the record)."""
    __tablename__ = "cqual_permits"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cqp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site: Mapped[str] = mapped_column(String(160), index=True, default="")
    kind: Mapped[str] = mapped_column(String(40), default="")            # height | confined space | hot work | excavation
    hazard: Mapped[str] = mapped_column(String(300), default="")
    controls: Mapped[str] = mapped_column(Text, default="[]")            # [{control, done}]
    valid_from: Mapped[str] = mapped_column(String(10), default="")
    valid_till: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(20), default="draft")     # draft | issued | closed
    issued_by: Mapped[str] = mapped_column(String(120), default="")      # the safety officer's name
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CQualToolbox(Base):
    """Toolbox-talk record: topic, day, gang, headcount - the talk happened, recorded."""
    __tablename__ = "cqual_toolbox"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cqt"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site: Mapped[str] = mapped_column(String(160), index=True, default="")
    topic: Mapped[str] = mapped_column(String(200), default="")
    day: Mapped[str] = mapped_column(String(10), index=True, default="")
    gang: Mapped[str] = mapped_column(String(120), default="")
    attendees: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
