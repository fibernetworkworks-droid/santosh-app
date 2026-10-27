"""Tables of the Notary Sahayak, all prefixed notary_. The register and receipts are append-only (corrections = new rows)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class NotarySettings(Base):
    __tablename__ = "notary_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mode: Mapped[str] = mapped_column(String(10), default="notary")          # notary | desk (typing / documentation centre)
    office: Mapped[str] = mapped_column(String(160), default="")
    notary_name: Mapped[str] = mapped_column(String(120), default="")
    reg_no: Mapped[str] = mapped_column(String(60), default="")                # registration no. on her seal
    area: Mapped[str] = mapped_column(String(160), default="")                 # area of practice
    appointed_by: Mapped[str] = mapped_column(String(80), default="")          # Central Govt / State Govt of ...
    cop_valid_to: Mapped[str] = mapped_column(String(10), default="")          # certificate of practice valid till (Rule 8(4))
    address: Mapped[str] = mapped_column(Text, default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    state: Mapped[str] = mapped_column(String(4), default="MH")
    default_lang: Mapped[str] = mapped_column(String(4), default="en")
    stamp_rates: Mapped[str] = mapped_column(Text, default="{}")              # HER table {state: {stamp_key: amount | {amount, mode}}}
    fees: Mapped[str] = mapped_column(Text, default="{}")                     # HER notarial fee per act {act: amount}
    fee_caps: Mapped[str] = mapped_column(Text, default="{}")                 # her update of Rule 10 caps after a new notification
    charges: Mapped[str] = mapped_column(Text, default="{}")                  # desk charges {typing, print, xerox, drafting} (hers)
    rules: Mapped[str] = mapped_column(Text, default="")
    morning_time: Mapped[str] = mapped_column(String(5), default="09:30")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    receipt_prefix: Mapped[str] = mapped_column(String(10), default="NR")
    seq: Mapped[str] = mapped_column(Text, default="{}")


class NotaryDoc(Base):
    __tablename__ = "notary_docs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("nd"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")               # ND-0001
    kind: Mapped[str] = mapped_column(String(24), default="aff_general")
    lang: Mapped[str] = mapped_column(String(4), default="en")
    title: Mapped[str] = mapped_column(String(200), default="")
    parties: Mapped[str] = mapped_column(Text, default="[]")                  # [{name, relation, relative, age, occupation, address, gender, phone, id_ref, id_kind, id_masked}]
    facts: Mapped[str] = mapped_column(Text, default="{}")
    text: Mapped[str] = mapped_column(Text, default="")
    blanks: Mapped[str] = mapped_column(Text, default="[]")
    checks: Mapped[str] = mapped_column(Text, default="[]")
    stamp: Mapped[str] = mapped_column(Text, default="{}")                    # {state, key, amount|None, mode, ref (UIN / e-SBTR no.)}
    status: Mapped[str] = mapped_column(String(12), default="draft")         # draft | waiting | final | rejected | executed
    card_hash: Mapped[str] = mapped_column(String(64), default="")
    files: Mapped[str] = mapped_column(Text, default="{}")                    # {draft_pdf, draft_docx, final_pdf, final_docx}
    source: Mapped[str] = mapped_column(String(60), default="")               # rentdesk:T-0001 | words | translation
    versions: Mapped[str] = mapped_column(Text, default="[]")
    edited: Mapped[bool] = mapped_column(Boolean, default=False)             # her own text replaced the template
    entry_id: Mapped[str] = mapped_column(String(40), default="")            # register entry when notarised
    forgotten: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class NotaryEntry(Base):
    """Form XV notarial register line (Rule 11(2)). Never edited or deleted: a correction is a new line pointing at the old one."""
    __tablename__ = "notary_entries"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ne"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    serial: Mapped[str] = mapped_column(String(16), default="")               # 2026/0001
    year: Mapped[int] = mapped_column(Integer, default=0)
    on: Mapped[str] = mapped_column(String(10), default="")
    at: Mapped[str] = mapped_column(String(5), default="")
    act: Mapped[str] = mapped_column(String(20), default="affidavit")
    act_label: Mapped[str] = mapped_column(String(120), default="")
    executants: Mapped[str] = mapped_column(Text, default="[]")               # [{name, address, id_kind, id_masked, id_ref}]
    contents: Mapped[str] = mapped_column(Text, default="")
    stamp_text: Mapped[str] = mapped_column(String(160), default="")
    fee: Mapped[float] = mapped_column(Float, default=0.0)
    receipt_no: Mapped[str] = mapped_column(String(24), default="")
    doc_id: Mapped[str] = mapped_column(String(40), default="")
    corrects: Mapped[str] = mapped_column(String(16), default="")
    remarks: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class NotaryReceipt(Base):
    __tablename__ = "notary_receipts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("nr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(24), default="")               # NR/2627/0001
    on: Mapped[str] = mapped_column(String(10), default="")
    payer: Mapped[str] = mapped_column(String(120), default="")
    lines: Mapped[str] = mapped_column(Text, default="[]")                    # [{label, amount, kind notarial|desk}]
    total: Mapped[float] = mapped_column(Float, default=0.0)
    mode: Mapped[str] = mapped_column(String(10), default="cash")
    ref: Mapped[str] = mapped_column(String(60), default="")
    entry_id: Mapped[str] = mapped_column(String(40), default="")
    doc_id: Mapped[str] = mapped_column(String(40), default="")
    file_id: Mapped[str] = mapped_column(String(80), default="")
    void: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class NotaryApostille(Base):
    __tablename__ = "notary_apostilles"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("na"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")               # A-001
    party: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    doc_title: Mapped[str] = mapped_column(String(200), default="")
    doc_type: Mapped[str] = mapped_column(String(16), default="personal")
    country: Mapped[str] = mapped_column(String(80), default="")
    hague: Mapped[str] = mapped_column(String(8), default="")                 # yes | no | "" (not known yet)
    steps: Mapped[str] = mapped_column(Text, default="[]")
    doc_id: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(10), default="open")          # open | done | dropped
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class NotaryOnce(Base):
    __tablename__ = "notary_once"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
