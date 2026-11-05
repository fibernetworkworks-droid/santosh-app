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


# --------------------------------------------------------- #18-21 BIM / Information desk (C11, Wave 3)
class CBimModel(Base):
    """One parsed IFC model (STEP text in, honest counts out). The parse keeps WHAT IT READ - schema,
    entity classes, spaces, storeys - and says which things it did not read (rotation, exact geometry)."""
    __tablename__ = "cbim_models"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cbm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    name: Mapped[str] = mapped_column(String(200), default="")
    schema_: Mapped[str] = mapped_column(String(20), default="")          # IFC4 / IFC2X3 / ""
    entities: Mapped[int] = mapped_column(Integer, default=0)
    stats: Mapped[str] = mapped_column(Text, default="{}")                # counts by class, spaces, storeys
    health: Mapped[str] = mapped_column(Text, default="{}")               # the model-health gaps
    elements: Mapped[int] = mapped_column(Integer, default=0)             # rows stored in cbim_elements
    file_ref: Mapped[str] = mapped_column(String(160), default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CBimElement(Base):
    """One spatial element as READ from the model: guid, IFC class, name, storey chain, its own
    declared quantities (IfcElementQuantity - the model's numbers, never Hoola's), and the world
    placement point where the file carries one (axis-aligned; rotation is ignored, said out loud)."""
    __tablename__ = "cbim_elements"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cbel"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    model_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    guid: Mapped[str] = mapped_column(String(40), index=True, default="")
    ifc_class: Mapped[str] = mapped_column(String(60), index=True, default="")
    name: Mapped[str] = mapped_column(String(200), default="")
    storey: Mapped[str] = mapped_column(String(120), default="")
    qty: Mapped[str] = mapped_column(Text, default="{}")                  # {Length/Width/Height/Volume/Area: value}
    world: Mapped[str] = mapped_column(Text, default="{}")                # {x,y,z} or {} when absent
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CBimCde(Base):
    """CDE & document controller (#19): one file's life in the common data environment - ISO 19650
    status codes (wip / shared / published / archived are HER states), revisions, superseded copies."""
    __tablename__ = "cbim_cde"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cbc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    code: Mapped[str] = mapped_column(String(80), index=True, default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    rev: Mapped[str] = mapped_column(String(20), default="")
    status: Mapped[str] = mapped_column(String(16), default="wip", index=True)   # wip | shared | published | archived
    superseded_by: Mapped[str] = mapped_column(String(40), default="")
    file_ref: Mapped[str] = mapped_column(String(160), default="")
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CBimTransmit(Base):
    """Transmittal: what went to whom, which codes, which day - the audit trail of the CDE."""
    __tablename__ = "cbim_transmittals"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cbt"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    to_whom: Mapped[str] = mapped_column(String(160), default="")
    codes: Mapped[str] = mapped_column(Text, default="[]")                # [code, ...]
    day: Mapped[str] = mapped_column(String(10), default="")
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CBimClash(Base):
    """Clash candidate (#20): two elements whose read boxes overlap with the clearance margin - the
    verdict (accept / rework / ignore) is the BIM coordinator's word, recorded; BCF export rides out."""
    __tablename__ = "cbim_clashes"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cbcl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    model_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    a_guid: Mapped[str] = mapped_column(String(40), default="")
    b_guid: Mapped[str] = mapped_column(String(40), default="")
    trade_a: Mapped[str] = mapped_column(String(60), default="")
    trade_b: Mapped[str] = mapped_column(String(60), default="")
    group_key: Mapped[str] = mapped_column(String(120), default="")       # "wall x duct" style pair label
    overlap: Mapped[str] = mapped_column(Text, default="{}")              # the overlap box dims
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)  # open | assigned | resolved | accepted
    by: Mapped[str] = mapped_column(String(120), default="")
    bcf_ref: Mapped[str] = mapped_column(String(160), default="")
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CBimLink4d(Base):
    """4D mapping (#21): her activity mapped to a class / storey slice of the model, with dates -
    Hoola keeps the mapping and reports the model quantities per activity; it never builds the CPM."""
    __tablename__ = "cbim_links4d"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cbl4"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    model_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    activity: Mapped[str] = mapped_column(String(160), default="")
    match_kind: Mapped[str] = mapped_column(String(16), default="class")  # class | storey | name
    match_value: Mapped[str] = mapped_column(String(120), default="")
    start: Mapped[str] = mapped_column(String(10), default="")
    finish: Mapped[str] = mapped_column(String(10), default="")
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CBimTakeoff(Base):
    """5D take-off rows (#21): the model's OWN quantity (IfcQuantity*) with its GUID as the trail -
    the only arithmetic is qty x rate when she feeds a rate with its source; recompute re-reads."""
    __tablename__ = "cbim_takeoffs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cbto"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    model_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    guid: Mapped[str] = mapped_column(String(40), default="")
    ifc_class: Mapped[str] = mapped_column(String(60), default="")
    name: Mapped[str] = mapped_column(String(200), default="")
    qty: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(12), default="")
    source_ref: Mapped[str] = mapped_column(String(160), default="")      # 'IFC IfcQuantityVolume of <guid>'
    rate: Mapped[float] = mapped_column(Float, default=0.0)
    rate_source: Mapped[str] = mapped_column(String(160), default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# ---------------------------------- #25 as-built set + #109 digital twin (C11, Wave 3.5, v0.565.0)
class CBimAsbuilt(Base):
    """The as-built SET register (#25): one handover set with its required document codes as SHE
    listed them - completeness is arithmetic on HER list; the set's approval is the site architect's
    (tier C)."""
    __tablename__ = "cbim_asbuilts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cba"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    name: Mapped[str] = mapped_column(String(200), default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CBimAsbuiltDoc(Base):
    """One document of the as-built set: the required code, HER status word (pending | received | na),
    and the NAME of whoever said it (a received/na without a name is nobody's word)."""
    __tablename__ = "cbim_asbuilt_docs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cbad"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    set_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    code: Mapped[str] = mapped_column(String(80), default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)  # pending | received | na
    by: Mapped[str] = mapped_column(String(120), default="")
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CTwinAsset(Base):
    """Digital-twin asset row (#109): the DATA LINK asset_id -> IFC GUID (+ model), the name and the
    space as fed - the twin is a register Hoola keeps, never a live 3D view."""
    __tablename__ = "ctwin_assets"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cta"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    asset_id: Mapped[str] = mapped_column(String(80), index=True, default="")
    guid: Mapped[str] = mapped_column(String(40), default="")             # the IFC GlobalId it maps to
    model_id: Mapped[str] = mapped_column(String(40), default="")
    name: Mapped[str] = mapped_column(String(200), default="")
    kind: Mapped[str] = mapped_column(String(60), default="")             # chiller / lift / pump / ...
    space: Mapped[str] = mapped_column(String(120), default="")
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CTwinReading(Base):
    """One sensor feed row (#109): HER export as fed (asset, sensor, value, unit); when she feeds a
    band with its source, out-of-band is flagged - the flag is arithmetic, the act is the FM's."""
    __tablename__ = "ctwin_readings"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ctr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    asset_id: Mapped[str] = mapped_column(String(80), index=True, default="")
    sensor: Mapped[str] = mapped_column(String(80), default="")
    value: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(20), default="")
    band_min: Mapped[float] = mapped_column(Float, default=0.0)
    band_max: Mapped[float] = mapped_column(Float, default=0.0)
    band_source: Mapped[str] = mapped_column(String(160), default="")
    out_band: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# --------------------------------------------------------- #10-12 Pre-design desk (C12, Wave 3)
class CpdRule(Base):
    """Pre-design rule rows as DATA: her sourced limits (clause + source REQUIRED) beside the national
    pack rows - fire travel distances, MEP norms, anything the desk must check against."""
    __tablename__ = "cpd_rules"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cpdr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    family: Mapped[str] = mapped_column(String(20), index=True, default="")   # ll | unit | span | fire | mep | other
    rule_id: Mapped[str] = mapped_column(String(60), index=True, default="")
    text: Mapped[str] = mapped_column(String(300), default="")
    value: Mapped[float] = mapped_column(Float, default=0.0)
    direction: Mapped[str] = mapped_column(String(10), default="max")     # min | max
    unit: Mapped[str] = mapped_column(String(20), default="")
    clause: Mapped[str] = mapped_column(String(160), default="")
    source: Mapped[str] = mapped_column(String(200), default="")
    checked_on: Mapped[str] = mapped_column(String(10), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CpdCalc(Base):
    """One pre-design computation, inputs and trail together - load take-down, column size, beam
    depth, MEP estimates, fire demand. Every row says PRELIMINARY; the design sign is the engineer's."""
    __tablename__ = "cpd_calcs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cpdc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    kind: Mapped[str] = mapped_column(String(30), index=True, default="")   # slab_load | column_load | column_size |
                                                            # beam_depth | elec | water | hvac | fire_demand
    name: Mapped[str] = mapped_column(String(160), default="")
    inputs: Mapped[str] = mapped_column(Text, default="{}")
    result: Mapped[str] = mapped_column(Text, default="{}")
    is_ref: Mapped[str] = mapped_column(String(200), default="")
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# --------------------------------------------------------- #74 scaffold tags (C12, Wave 3.5)
class CpdScaffold(Base):
    """Scaffold inspection TAG register (#74): the competent person's word (name required), the tag
    state and the next check date - Hoola keeps the register, never the tag itself."""
    __tablename__ = "cpd_scaffolds"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cpsc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    scaffold_id: Mapped[str] = mapped_column(String(80), index=True, default="")
    status: Mapped[str] = mapped_column(String(16), default="ok")          # ok | defective | altered
    checked_by: Mapped[str] = mapped_column(String(120), default="")      # the competent person's NAME
    next_check: Mapped[str] = mapped_column(String(10), default="")
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# --------------------------------------------------------- #22-24,26 Survey & measurement desk (C13, Wave 3)
class CsurJob(Base):
    """One survey job: a set of points from coordinates pasted or LandXML read - what came in is said
    on the tin; the certification is the licensed surveyor's."""
    __tablename__ = "csur_jobs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("csj"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    name: Mapped[str] = mapped_column(String(160), default="")
    source_kind: Mapped[str] = mapped_column(String(16), default="coords")  # coords | landxml
    points: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CsurPoint(Base):
    """One survey point: id, E/N/Z as fed (metres)."""
    __tablename__ = "csur_points"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("csp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    job_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    pid: Mapped[str] = mapped_column(String(40), index=True, default="")
    x: Mapped[float] = mapped_column(Float, default=0.0)
    y: Mapped[float] = mapped_column(Float, default=0.0)
    z: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CsurCalc(Base):
    """One survey computation with its trail: traverse closure, shoelace area, boundary vs record,
    grid volumes, scan deviations - arithmetic for the survey lead, never the certificate."""
    __tablename__ = "csur_calcs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("csc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    kind: Mapped[str] = mapped_column(String(20), index=True, default="")   # traverse | area | boundary | volume | deviation
    name: Mapped[str] = mapped_column(String(160), default="")
    inputs: Mapped[str] = mapped_column(Text, default="{}")
    result: Mapped[str] = mapped_column(Text, default="{}")
    is_ref: Mapped[str] = mapped_column(String(200), default="")
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CsurCarpet(Base):
    """RERA carpet-area statement (#26): the unit, HER wall policy (recorded, not assumed), the
    declared area with its source; the certificate stays with the project architect / CE."""
    __tablename__ = "csur_carpets"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("csca"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    unit_no: Mapped[str] = mapped_column(String(60), index=True, default="")
    wall_policy: Mapped[str] = mapped_column(String(200), default="")      # her word on internal walls
    declared_m2: Mapped[float] = mapped_column(Float, default=0.0)
    declared_source: Mapped[str] = mapped_column(String(160), default="")
    computed_m2: Mapped[float] = mapped_column(Float, default=0.0)
    diff_pct: Mapped[float] = mapped_column(Float, default=0.0)
    verdict: Mapped[str] = mapped_column(String(20), default="pending")    # pending | within | exceeds
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CsurCarpetRoom(Base):
    """One room of the carpet statement: length x breadth as read off the plan by a human."""
    __tablename__ = "csur_carpet_rooms"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cscr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    carpet_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    room: Mapped[str] = mapped_column(String(80), default="")
    length_m: Mapped[float] = mapped_column(Float, default=0.0)
    breadth_m: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# -------------------------------------------- #27 GIS layers + overlays (C13, Wave 3.5, v0.565.0)
class CGisLayer(Base):
    """One GIS layer (#27): GeoJSON read as TEXT for its Polygon/MultiPolygon rings - the CRS is
    recorded AS FED; areas are computed ONLY in projected metres (a degree has no square metres,
    and the desk refuses to pretend otherwise)."""
    __tablename__ = "cgis_layers"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cgl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    name: Mapped[str] = mapped_column(String(160), default="")
    crs: Mapped[str] = mapped_column(String(80), default="")              # as fed (RFC 7946 default: WGS84)
    units: Mapped[str] = mapped_column(String(8), default="")             # m | deg - area only when m
    polygons: Mapped[str] = mapped_column(Text, default="[]")             # [[[x,y],...], ...] outer rings
    holes: Mapped[int] = mapped_column(Integer, default=0)                # inner rings read, NOT subtracted
    vertices: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CGisOverlay(Base):
    """One map-layer reading (#27): the flood / seismic / zoning value as READ OFF THE MAP BY A
    HUMAN, with its source - the map is never interpreted here, the row records her reading."""
    __tablename__ = "cgis_overlays"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cgo"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    layer_id: Mapped[str] = mapped_column(String(40), default="")
    hazard: Mapped[str] = mapped_column(String(40), default="")           # flood | seismic | zoning | other
    zone_value: Mapped[str] = mapped_column(String(160), default="")     # her reading, as text
    source: Mapped[str] = mapped_column(String(200), default="")
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# --------------------------------------------------------- #47 Delay analysis desk (C13, Wave 3)
class CdelProg(Base):
    """Programme rows as DATA: baseline (with HER criticality marks - Hoola never computes the CPM)
    or as-built actuals; the working paper compares, the entitlement stays with counsel."""
    __tablename__ = "cdel_progs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cdp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    kind: Mapped[str] = mapped_column(String(16), index=True, default="")   # baseline | asbuilt
    rows: Mapped[str] = mapped_column(Text, default="[]")                  # [{activity, start, finish, critical?}]
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CdelWindow(Base):
    """Analysis window: her date range (delay windows are chosen by the analyst, not code)."""
    __tablename__ = "cdel_windows"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cdw"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    label: Mapped[str] = mapped_column(String(80), default="")
    start: Mapped[str] = mapped_column(String(10), default="")
    finish: Mapped[str] = mapped_column(String(10), default="")
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CdelNotice(Base):
    """Notice-compliance arithmetic: event date, notice date, the contract's window - in/late, cited."""
    __tablename__ = "cdel_notices"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cdn"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    event: Mapped[str] = mapped_column(String(200), default="")
    event_date: Mapped[str] = mapped_column(String(10), default="")
    notice_date: Mapped[str] = mapped_column(String(10), default="")
    notice_days: Mapped[int] = mapped_column(Integer, default=0)
    contract_ref: Mapped[str] = mapped_column(String(160), default="")
    taken_days: Mapped[int] = mapped_column(Integer, default=0)
    verdict: Mapped[str] = mapped_column(String(12), default="")           # in-window | late
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# --------------------------------------------------------- #104,110-118 Green & performance desk (C15, Wave 3)
class CgrMeter(Base):
    """Meter reading (#104): one row per reading, as fed."""
    __tablename__ = "cgr_meters"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cgm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site: Mapped[str] = mapped_column(String(160), index=True, default="")
    meter: Mapped[str] = mapped_column(String(60), default="")
    day: Mapped[str] = mapped_column(String(10), index=True, default="")
    kwh: Mapped[float] = mapped_column(Float, default=0.0)
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CgrTariff(Base):
    """Her tariff as DATA: slab rows from HER bill (source required), not a remembered rate."""
    __tablename__ = "cgr_tariffs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cgt"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(80), index=True, default="")
    rows: Mapped[str] = mapped_column(Text, default="[]")                  # [{from_kwh, to_kwh, rate, fixed_rs}]
    source: Mapped[str] = mapped_column(String(160), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CgrEcbcRule(Base):
    """ECBC / daylight / performance rule rows as DATA: clause + source REQUIRED (like drawqa's
    bye-law rows); the check verdict is arithmetic, the assessor decides."""
    __tablename__ = "cgr_ecbc_rules"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cger"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    family: Mapped[str] = mapped_column(String(20), index=True, default="")   # ecbc | daylight | benchmark | other
    rule_id: Mapped[str] = mapped_column(String(60), index=True, default="")
    text: Mapped[str] = mapped_column(String(300), default="")
    value: Mapped[float] = mapped_column(Float, default=0.0)
    direction: Mapped[str] = mapped_column(String(10), default="max")      # min | max
    unit: Mapped[str] = mapped_column(String(20), default="")
    clause: Mapped[str] = mapped_column(String(160), default="")
    source: Mapped[str] = mapped_column(String(200), default="")
    checked_on: Mapped[str] = mapped_column(String(10), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CgrCheck(Base):
    """Declared vs limit on the performance desk: the verdict is ARITHMETIC; ECBC assessor / physicist
    own the outcome (tier B)."""
    __tablename__ = "cgr_checks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cgck"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    rule_id: Mapped[str] = mapped_column(String(60), index=True, default="")
    declared: Mapped[float] = mapped_column(Float, default=0.0)
    limit_value: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(20), default="")
    verdict: Mapped[str] = mapped_column(String(16), default="pending")    # pending | ok | breach
    checked_on: Mapped[str] = mapped_column(String(10), default="")
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CgrCarbon(Base):
    """Embodied carbon row (#114): quantity x EPD factor - the factor's source is REQUIRED (an EPD or
    an LCA database, named); the hot-spot list is a working paper, the assessor decides."""
    __tablename__ = "cgr_carbon"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cgcb"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    material: Mapped[str] = mapped_column(String(120), index=True, default="")
    qty: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(12), default="")
    factor_kgco2e: Mapped[float] = mapped_column(Float, default=0.0)
    factor_source: Mapped[str] = mapped_column(String(200), default="")
    kgco2e: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CgrCredit(Base):
    """Green-rating credit tracker (#110): IGBC / GRIHA / LEED rows with HER points claimed and the
    evidence reference; the score is a sum, the rating belongs to the assessor."""
    __tablename__ = "cgr_credits"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cgcr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    rating: Mapped[str] = mapped_column(String(20), index=True, default="")   # IGBC | GRIHA | LEED
    credit: Mapped[str] = mapped_column(String(80), default="")
    points_available: Mapped[float] = mapped_column(Float, default=0.0)
    points_claimed: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_ref: Mapped[str] = mapped_column(String(160), default="")
    status: Mapped[str] = mapped_column(String(16), default="claimed")     # planned | claimed | denied
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CgrCx(Base):
    """Commissioning item (#116): system, test, the functional test SCRIPT steps, the season it
    belongs to; the sign-off is the Cx authority's (tier C refusal rides the gate)."""
    __tablename__ = "cgr_cx"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cgcx"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    system: Mapped[str] = mapped_column(String(120), index=True, default="")
    test: Mapped[str] = mapped_column(String(200), default="")
    steps: Mapped[str] = mapped_column(Text, default="[]")
    season: Mapped[str] = mapped_column(String(20), default="")            # first | seasonal
    status: Mapped[str] = mapped_column(String(16), default="planned")     # planned | done | failed
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CgrCxIssue(Base):
    """One issue off a commissioning test: severity, note, status - the log the Cx authority reviews."""
    __tablename__ = "cgr_cx_issues"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cgcxi"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    cx_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    severity: Mapped[str] = mapped_column(String(12), default="minor")     # minor | major | critical
    note: Mapped[str] = mapped_column(String(300), default="")
    status: Mapped[str] = mapped_column(String(16), default="open")        # open | closed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CgrTc(Base):
    """T&C record (#117): the certificate as the agency reported it, as-installed vs design value
    with the tolerance arithmetic - ok / exceeds is a number, acceptance is the T&C engineer's."""
    __tablename__ = "cgr_tc"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cgtc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    system: Mapped[str] = mapped_column(String(120), index=True, default="")
    cert_no: Mapped[str] = mapped_column(String(80), default="")
    agency: Mapped[str] = mapped_column(String(160), default="")
    tested_on: Mapped[str] = mapped_column(String(10), default="")
    as_installed: Mapped[float] = mapped_column(Float, default=0.0)
    design: Mapped[float] = mapped_column(Float, default=0.0)
    tolerance_pct: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(20), default="")
    dev_pct: Mapped[float] = mapped_column(Float, default=0.0)
    verdict: Mapped[str] = mapped_column(String(12), default="pending")    # pending | ok | exceeds
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CgrMv(Base):
    """M&V job (#118): baseline and reporting-period rows (driver + kwh as fed), the IPMVP option
    SHE names; the baseline model is the least-squares line with its r2 - savings are the identity."""
    __tablename__ = "cgr_mv"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cgmv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(160), index=True, default="")
    option: Mapped[str] = mapped_column(String(20), default="")            # her IPMVP option letter
    baseline: Mapped[str] = mapped_column(Text, default="[]")              # [{driver, kwh}]
    report: Mapped[str] = mapped_column(Text, default="[]")                # [{driver, kwh}]
    result: Mapped[str] = mapped_column(Text, default="{}")
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# --------------------------------------------------------- #82 Incident investigation (C13, rides quality)
class CQualIncident(Base):
    """Incident investigation (#82): the record of what happened, the timeline and the whys as DATA;
    the ROOT CAUSE and findings are the safety head's word, recorded with the name."""
    __tablename__ = "cqual_incidents"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cqi"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site: Mapped[str] = mapped_column(String(160), index=True, default="")
    day: Mapped[str] = mapped_column(String(10), index=True, default="")
    kind: Mapped[str] = mapped_column(String(20), default="")              # near_miss | injury | property | environmental
    severity: Mapped[str] = mapped_column(String(12), default="minor")     # minor | major | critical
    description: Mapped[str] = mapped_column(String(500), default="")
    reported_by: Mapped[str] = mapped_column(String(120), default="")
    root_cause: Mapped[str] = mapped_column(String(300), default="")
    findings_by: Mapped[str] = mapped_column(String(120), default="")      # the safety head's name
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)  # open | closed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CQualIncRow(Base):
    """One row of the investigation: timeline event, witness note, a 5-why step, or a corrective
    action with its owner and due date."""
    __tablename__ = "cqual_inc_rows"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cqir"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    incident_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    kind: Mapped[str] = mapped_column(String(12), index=True, default="")  # timeline | witness | why | action
    at: Mapped[str] = mapped_column(String(10), default="")
    text: Mapped[str] = mapped_column(String(300), default="")
    answer: Mapped[str] = mapped_column(String(300), default="")
    owner: Mapped[str] = mapped_column(String(120), default="")
    due: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(16), default="")            # actions: open | done
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
