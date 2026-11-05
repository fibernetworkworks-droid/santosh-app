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
