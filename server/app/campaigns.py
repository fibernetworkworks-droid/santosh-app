"""Campaign logic shared by Santosh's tools, the worker and the webhook."""
from __future__ import annotations

from sqlalchemy import func, select

from .db import Campaign, Lead, LeadList, OutboundMessage, Template, now, session
from .events import bus, notify
from .leads import SAMPLE_PREFIX

STATUS_RANK = {"queued": 0, "sent": 1, "delivered": 2, "read": 3}


class CampaignError(Exception):
    pass


def build_params(mapping: list[dict], lead: Lead) -> list[str]:
    out = []
    for m in mapping:
        src = m.get("source", "static")
        if src == "lead_name":
            first = (lead.name or "").strip().split(" ")[0] if lead.name else ""
            out.append(first or m.get("fallback") or "ji")
        elif src == "lead_column":
            v = (lead.extra or {}).get(m.get("value", ""))
            out.append(str(v).strip() if v not in (None, "") else (m.get("fallback") or "-"))
        else:
            out.append(str(m.get("value", "")).strip() or (m.get("fallback") or "-"))
    return out


def counts(s, campaign_id: str) -> dict:
    rows = s.execute(select(OutboundMessage.status, func.count()).where(OutboundMessage.campaign_id == campaign_id)
                     .group_by(OutboundMessage.status)).all()
    c = {k: 0 for k in ("queued", "sent", "delivered", "read", "failed")}
    for st, n in rows:
        c[st] = n
    total = sum(c.values())
    replied = s.scalar(select(func.count()).where(OutboundMessage.campaign_id == campaign_id,
                                                  OutboundMessage.replied.is_(True))) or 0
    reached = c["sent"] + c["delivered"] + c["read"]
    return {"total": total, "queued": c["queued"], "failed": c["failed"],
            "sent": reached, "delivered": c["delivered"] + c["read"], "read": c["read"], "replied": replied}


def campaign_view(campaign_id: str) -> dict:
    with session() as s:
        c = s.get(Campaign, campaign_id)
        if not c:
            raise CampaignError(f"No campaign with id {campaign_id}")
        t = s.get(Template, c.template_id)
        ll = s.get(LeadList, c.lead_list_id)
        n = counts(s, c.id)
        total = n["total"] or 1
        done = n["total"] - n["queued"]
        first = s.scalars(select(OutboundMessage.params).where(OutboundMessage.campaign_id == c.id)
                          .order_by(OutboundMessage.id).limit(1)).first()
        from .whatsapp.templates import render_body
        preview = render_body(t.body, first or list(t.example_values or []))
        if t.footer:
            preview += "\n\n" + t.footer
        return {"id": c.id, "title": c.title, "status": c.status, "status_reason": c.status_reason,
                "auto_send": c.auto_send, "template": {"id": t.id, "name": t.name, "status": t.status,
                                                       "body": t.body, "preview": preview,
                                                       "rejection_reason": t.rejection_reason},
                "lead_list": {"id": ll.id, "name": ll.name}, "counts": n,
                "progress": round(100 * done / total) if n["total"] else 0,
                "created_at": c.created_at.isoformat(),
                "started_at": c.started_at.isoformat() if c.started_at else None,
                "finished_at": c.finished_at.isoformat() if c.finished_at else None}


def publish_campaign(campaign_id: str) -> None:
    v = campaign_view(campaign_id)
    with session() as s:
        conv = s.get(Campaign, campaign_id).conversation_id
    bus.publish(conv, "campaign", v, campaign_id=campaign_id)


def create_campaign(*, tenant_id: str, conversation_id: str, title: str, lead_list_id: str, template_id: str,
                    param_mapping: list[dict], consent_confirmed: bool, auto_send: bool,
                    only_opted_in: bool = True, live_mode: bool = False) -> dict:
    with session() as s:
        ll = s.get(LeadList, lead_list_id)
        t = s.get(Template, template_id)
        if not ll or ll.tenant_id != tenant_id:
            raise CampaignError(f"No lead list with id {lead_list_id}")
        if not t or t.tenant_id != tenant_id:
            raise CampaignError(f"No template with id {template_id}")
        if t.status in ("REJECTED", "DISABLED"):
            raise CampaignError(f"Template {t.name} is {t.status}; draft and submit a new one first.")
        from .whatsapp.templates import VAR_RE
        nvars = len(set(VAR_RE.findall(t.body)))
        if len(param_mapping) != nvars:
            raise CampaignError(f"The template has {nvars} variables but {len(param_mapping)} values were mapped.")

        q = select(Lead).where(Lead.list_id == lead_list_id)
        leads = s.scalars(q).all()
        if ll.has_consent_column and only_opted_in:
            leads = [l for l in leads if l.opted_in]
            if not leads:
                raise CampaignError("Nobody in this list has opted in (the consent column is 'no' for everyone).")
        elif not consent_confirmed:
            raise CampaignError("CONSENT_REQUIRED: this list has no opt-in column. Ask the user to confirm these "
                                "people agreed to get WhatsApp messages from the business, then call again with "
                                "consent_confirmed=true.")
        if live_mode:
            leads = [l for l in leads if not l.phone.startswith(SAMPLE_PREFIX)]
            if not leads:
                raise CampaignError("These are the sample numbers from the demo file; they are never messaged in live mode.")

        c = Campaign(tenant_id=tenant_id, conversation_id=conversation_id, title=title[:200],
                     lead_list_id=lead_list_id, template_id=template_id, param_mapping=param_mapping,
                     auto_send=auto_send,
                     status="ready" if t.status == "APPROVED" else "awaiting_approval")
        if c.status == "ready" and auto_send:
            c.status = "sending"
            c.started_at = now()
        s.add(c)
        s.flush()
        s.add_all([OutboundMessage(campaign_id=c.id, lead_id=l.id, phone=l.phone, params=build_params(param_mapping, l))
                   for l in leads])
        cid = c.id
    publish_campaign(cid)
    return campaign_view(cid)


def set_campaign_status(campaign_id: str, status: str, reason: str | None = None) -> dict:
    with session() as s:
        c = s.get(Campaign, campaign_id)
        if not c:
            raise CampaignError(f"No campaign with id {campaign_id}")
        c.status = status
        c.status_reason = reason
        if status == "sending" and not c.started_at:
            c.started_at = now()
        if status in ("completed", "failed", "cancelled"):
            c.finished_at = now()
    publish_campaign(campaign_id)
    return campaign_view(campaign_id)


def confirm_send(campaign_id: str) -> dict:
    with session() as s:
        c = s.get(Campaign, campaign_id)
        if not c:
            raise CampaignError(f"No campaign with id {campaign_id}")
        c.auto_send = True
        status = c.status
    if status in ("ready", "paused"):
        return set_campaign_status(campaign_id, "sending")
    return campaign_view(campaign_id)


def apply_message_status(updates: list[dict]) -> set[str]:
    """Statuses from Meta's webhook (or the simulator). Returns touched campaign ids."""
    touched: set[str] = set()
    with session() as s:
        for u in updates:
            if "reply_from" in u:
                om = s.scalars(select(OutboundMessage).where(OutboundMessage.phone == u["reply_from"])
                               .order_by(OutboundMessage.id.desc()).limit(1)).first()
                if om and not om.replied:
                    om.replied = True
                    touched.add(om.campaign_id)
                continue
            om = s.scalars(select(OutboundMessage).where(OutboundMessage.wa_message_id == u.get("id"))).first()
            if not om:
                continue
            new = u.get("status")
            if new == "failed":
                if om.status not in ("delivered", "read"):
                    om.status = "failed"
                    errs = u.get("errors") or [{}]
                    om.error = f"{errs[0].get('code', '')} {errs[0].get('title', '')}".strip()
            elif new in STATUS_RANK and STATUS_RANK[new] > STATUS_RANK.get(om.status, -1):
                om.status = new
            om.updated_at = now()
            touched.add(om.campaign_id)
    return touched


def apply_template_status(meta_id: str, status: str, reason: str | None = None) -> None:
    with session() as s:
        t = s.scalars(select(Template).where(Template.meta_id == meta_id)).first()
        if t:
            t.status = status.upper()
            t.rejection_reason = reason if status.upper() == "REJECTED" else None
            t.updated_at = now()


def report_text(v: dict) -> str:
    n = v["counts"]
    sent = n["sent"]
    pct = lambda a: f"{round(100 * a / sent)}%" if sent else "0%"
    lines = [f"{v['title']} poora ho gaya.",
             f"Bheje: {sent} · Pahunche: {n['delivered']} ({pct(n['delivered'])}) · Padhe: {n['read']} ({pct(n['read'])})"
             f" · Jawab: {n['replied']}"]
    if n["failed"]:
        lines.append(f"{n['failed']} number par message nahi gaya (WhatsApp par nahi hain ya band hain).")
    return "\n".join(lines)


def notify_campaign(campaign_id: str, text: str) -> None:
    with session() as s:
        conv = s.get(Campaign, campaign_id).conversation_id
    notify(conv, text, campaign_id=campaign_id)
