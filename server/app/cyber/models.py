"""Tables of the Cyber Suraksha Sahayak (all prefixed cyber_)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class CyberSettings(Base):
    __tablename__ = "cyber_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    own_ips: Mapped[str] = mapped_column(Text, default="[]")              # her office / server IPs (never blocked, logins from them are normal)
    vip_names: Mapped[str] = mapped_column(Text, default="[]")            # names fraudsters pretend to be (owner, accountant ...)
    crown_hosts: Mapped[str] = mapped_column(Text, default="[]")          # servers / PCs that matter most (Tally server, website)
    work_emails: Mapped[str] = mapped_column(Text, default="[]")          # for the breach check (HIBP, her key)
    link_provider: Mapped[str] = mapped_column(String(16), default="webrisk")   # webrisk (commercial) | safebrowsing (non-commercial)
    morning_time: Mapped[str] = mapped_column(String(5), default="09:15")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    last_intel: Mapped[str] = mapped_column(String(10), default="")        # day advisories were last refreshed
    last_posture: Mapped[str] = mapped_column(String(10), default="")      # day domains were last re-checked
    alert_seq: Mapped[int] = mapped_column(Integer, default=0)
    action_seq: Mapped[int] = mapped_column(Integer, default=0)
    incident_seq: Mapped[int] = mapped_column(Integer, default=0)
    rules: Mapped[str] = mapped_column(Text, default="")


class CyberKey(Base):
    """Her own API keys (typed only in the app, sealed with the bazar vault, never shown to the model)."""
    __tablename__ = "cyber_keys"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ck"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    provider: Mapped[str] = mapped_column(String(16))                    # webrisk | safebrowsing | virustotal | hibp | nvd | cloudflare
    sealed: Mapped[str] = mapped_column(Text, default="")
    extra: Mapped[str] = mapped_column(String(120), default="")          # cloudflare zone id
    label: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CyberAlert(Base):
    """One normalised security alert (many raw lines with the same fingerprint are counted, not repeated)."""
    __tablename__ = "cyber_alerts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ca"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")          # AL-0001
    fp: Mapped[str] = mapped_column(String(64), index=True, default="")
    source: Mapped[str] = mapped_column(String(20), default="other")     # rules.SOURCES
    kind: Mapped[str] = mapped_column(String(24), default="other")       # rules.KINDS
    title: Mapped[str] = mapped_column(String(240), default="")
    host: Mapped[str] = mapped_column(String(120), default="")
    user: Mapped[str] = mapped_column(String(120), default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    detail: Mapped[str] = mapped_column(Text, default="")               # masked sample line (data, never instructions)
    count: Mapped[int] = mapped_column(Integer, default=1)
    score: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[str] = mapped_column(String(10), default="noise")     # matters | watch | noise
    why: Mapped[str] = mapped_column(Text, default="[]")
    rule_id: Mapped[str] = mapped_column(String(40), default="")         # her known-benign rule that matched
    group_key: Mapped[str] = mapped_column(String(160), default="")
    status: Mapped[str] = mapped_column(String(10), default="open")     # open | ack | dismissed | incident
    incident_id: Mapped[str] = mapped_column(String(40), default="")
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    batch: Mapped[str] = mapped_column(String(40), default="")


class CyberRule(Base):
    """Something she taught: 'this is normal' (known benign) for matching alerts."""
    __tablename__ = "cyber_rules"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(20), default="")
    kind: Mapped[str] = mapped_column(String(24), default="")
    host: Mapped[str] = mapped_column(String(120), default="")
    user: Mapped[str] = mapped_column(String(120), default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    words: Mapped[str] = mapped_column(String(160), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    hits: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CyberCheck(Base):
    """A suspicious email / link / file check (links never opened, files never uploaded)."""
    __tablename__ = "cyber_checks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cx"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(8), default="email")       # email | link | file
    subject: Mapped[str] = mapped_column(String(300), default="")      # sender / url / file name + hash
    verdict: Mapped[str] = mapped_column(String(14), default="unclear")
    result: Mapped[str] = mapped_column(Text, default="{}")
    helpdesk_incident: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


class CyberDomain(Base):
    """Her own domain: checked passively (DNS, TLS, headers); deeper own-site checks only once she proved it is hers."""
    __tablename__ = "cyber_domains"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cd"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    domain: Mapped[str] = mapped_column(String(253), default="")
    token: Mapped[str] = mapped_column(String(64), default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_by: Mapped[str] = mapped_column(String(16), default="")     # dns | hoola_site
    posture: Mapped[str] = mapped_column(Text, default="{}")
    breach: Mapped[str] = mapped_column(Text, default="{}")
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    told: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CyberSoftware(Base):
    """What runs in her office (for CVE / KEV / CERT-In advisory matching)."""
    __tablename__ = "cyber_software"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cs"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    vendor: Mapped[str] = mapped_column(String(80), default="")
    product: Mapped[str] = mapped_column(String(120), default="")
    version: Mapped[str] = mapped_column(String(40), default="")
    cpe: Mapped[str] = mapped_column(String(200), default="")
    where: Mapped[str] = mapped_column(String(120), default="")          # which PC / server / router
    from_asset: Mapped[str] = mapped_column(String(40), default="")      # helpdesk asset id when synced
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class CyberAdvisory(Base):
    __tablename__ = "cyber_advisories"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    ref: Mapped[str] = mapped_column(String(120), default="", index=True)   # CVE id or advisory link
    source: Mapped[str] = mapped_column(String(10), default="nvd")      # nvd | kev | certin
    title: Mapped[str] = mapped_column(String(300), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    score: Mapped[float] = mapped_column(Float, default=0.0)
    severity: Mapped[str] = mapped_column(String(12), default="")
    exploited: Mapped[bool] = mapped_column(Boolean, default=False)
    software_id: Mapped[str] = mapped_column(String(40), default="")
    url: Mapped[str] = mapped_column(String(400), default="")
    published: Mapped[str] = mapped_column(String(25), default="")
    status: Mapped[str] = mapped_column(String(10), default="new")      # new | patched | not_ours | ignored
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CyberIncident(Base):
    """The incident note: timeline, what happened, impact, what was done, CERT-In / DPDP (via the helpdesk incident), lessons."""
    __tablename__ = "cyber_incidents"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ci"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")         # IN-0001
    kind: Mapped[str] = mapped_column(String(14), default="other")      # helpdesk rules.PHISH_KIND keys
    title: Mapped[str] = mapped_column(String(240), default="")
    what: Mapped[str] = mapped_column(Text, default="")
    impact: Mapped[str] = mapped_column(Text, default="")
    done: Mapped[str] = mapped_column(Text, default="")
    lessons: Mapped[str] = mapped_column(Text, default="")
    timeline: Mapped[str] = mapped_column(Text, default="[]")
    alert_ids: Mapped[str] = mapped_column(Text, default="[]")
    check_ids: Mapped[str] = mapped_column(Text, default="[]")
    personal_data: Mapped[bool] = mapped_column(Boolean, default=False)
    systems: Mapped[str] = mapped_column(String(240), default="")
    helpdesk_incident: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(10), default="open")     # open | closed
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    conv: Mapped[str] = mapped_column(String(40), default="")


class CyberAction(Base):
    """Blocking / disabling / quarantining / wiping: a card that waits for HER tap (only the app API can decide it)."""
    __tablename__ = "cyber_actions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cy"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")         # CA-0001
    kind: Mapped[str] = mapped_column(String(16), default="block_ip")    # rules.ACTIONS
    target: Mapped[str] = mapped_column(String(200), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    via: Mapped[str] = mapped_column(String(16), default="steps")       # cloudflare (her key, API) | steps (she does it in the console)
    steps: Mapped[str] = mapped_column(Text, default="[]")
    risk: Mapped[str] = mapped_column(Text, default="")
    undo: Mapped[str] = mapped_column(Text, default="")
    incident_id: Mapped[str] = mapped_column(String(40), default="")
    alert_id: Mapped[str] = mapped_column(String(40), default="")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(10), default="waiting")  # waiting | done | approved | rejected | failed | stale | undone
    result: Mapped[str] = mapped_column(Text, default="{}")
    asked_by: Mapped[str] = mapped_column(String(80), default="Hoola")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    conv: Mapped[str] = mapped_column(String(40), default="")
