"""Background worker: waits for Meta approval, sends within rate and daily limits,
collects delivery statuses and posts the final report into the chat."""
from __future__ import annotations

import asyncio
import time
import logging
from datetime import timedelta

from sqlalchemy import func, select

from . import campaigns as camp
from .config import get_settings
from .db import Campaign, OutboundMessage, Template, as_utc, now, session
from .events import bus
from .whatsapp import WhatsAppError, get_whatsapp

log = logging.getLogger("santosh.worker")

# Meta error codes that mean "this number will never work" (no retry).
PERMANENT_CODES = {131026, 131021, 131009, 131008, 132000, 132001, 132012, 133010}
# Codes that mean the template itself is unusable right now.
TEMPLATE_CODES = {132001, 132007, 132015, 132016}


def _sent_last_24h(s, tenant_id: str) -> int:
    since = now() - timedelta(hours=24)
    return s.scalar(select(func.count()).select_from(OutboundMessage).join(Campaign, Campaign.id == OutboundMessage.campaign_id)
                    .where(Campaign.tenant_id == tenant_id, OutboundMessage.sent_at.is_not(None),
                           OutboundMessage.sent_at >= since)) or 0


async def check_approvals(force: bool = False) -> None:
    st = get_settings()
    wa = get_whatsapp()
    with session() as s:
        waiting = s.scalars(select(Campaign).where(Campaign.status == "awaiting_approval")).all()
        jobs = []
        for c in waiting:
            last = as_utc(c.last_template_poll)
            interval = 3 if wa.dry_run else st.template_poll_seconds
            if force or last is None or (now() - last).total_seconds() >= interval:
                t = s.get(Template, c.template_id)
                c.last_template_poll = now()
                jobs.append((c.id, t.id, t.meta_id, t.created_at, t.status))
    for cid, tid, meta_id, created, known in jobs:
        status, reason = known, None
        if known not in ("APPROVED", "REJECTED"):   # webhook may already have told us
            try:
                r = await wa.get_template_status(meta_id, as_utc(created))
                status, reason = r["status"].upper(), r.get("reason")
            except WhatsAppError as e:
                log.warning("template status check failed: %s", e)
                continue
            with session() as s:
                t = s.get(Template, tid)
                t.status, t.rejection_reason, t.updated_at = status, reason, now()
        with session() as s:
            c = s.get(Campaign, cid)
            t = s.get(Template, tid)
            reason = reason or t.rejection_reason
            auto = c.auto_send
            title = c.title
        if status == "APPROVED":
            if auto:
                camp.set_campaign_status(cid, "sending")
                camp.notify_campaign(cid, f"Meta ne template approve kar diya. {title} bhejna shuru kar diya hai.")
            else:
                camp.set_campaign_status(cid, "ready")
                camp.notify_campaign(cid, f"Meta ne template approve kar diya. {title} taiyaar hai; aap haan bolein to bhej doon.")
        elif status in ("REJECTED", "DISABLED"):
            camp.set_campaign_status(cid, "failed", f"Template {status.lower()}: {reason or 'no reason given'}")
            camp.notify_campaign(cid, f"Meta ne template reject kar diya ({reason or 'kaaran nahi bataya'}). "
                                      f"Boliye to main naya template likhkar dobara bhej doon.")


async def send_batches(max_seconds: float = 5.0) -> None:
    st = get_settings()
    wa = get_whatsapp()
    with session() as s:
        active = s.scalars(select(Campaign).where(Campaign.status.in_(("sending", "waiting_limit")))).all()
        active = [(c.id, c.tenant_id, c.status, c.template_id) for c in active]
    for cid, tenant, status, tid in active:
        with session() as s:
            remaining_today = st.max_daily_sends - _sent_last_24h(s, tenant)
            t = s.get(Template, tid)
            tname, tlang = t.name, t.language
        if remaining_today <= 0:
            if status != "waiting_limit":
                camp.set_campaign_status(cid, "waiting_limit", "Daily WhatsApp limit reached")
                camp.notify_campaign(cid, f"Aaj ki WhatsApp limit ({st.max_daily_sends} messages) poori ho gayi. "
                                          "Baaki messages 24 ghante ke andar apne aap chale jayenge.")
            continue
        if status == "waiting_limit":
            camp.set_campaign_status(cid, "sending")
        budget = int(min(remaining_today, max(1, st.send_rate_per_sec * max_seconds)))
        with session() as s:
            batch = s.scalars(select(OutboundMessage).where(OutboundMessage.campaign_id == cid,
                                                            OutboundMessage.status == "queued",
                                                            OutboundMessage.wa_message_id.is_(None))
                              .order_by(OutboundMessage.id).limit(budget)).all()
            batch = [(m.id, m.phone, m.params, m.attempts) for m in batch]
        if not batch:
            continue   # everything is with Meta; finish_campaigns() closes it once statuses settle
        gap = 1.0 / max(st.send_rate_per_sec, 0.1)
        for mid, phone, params, attempts in batch:
            with session() as s:
                if s.get(Campaign, cid).status != "sending":
                    break   # paused or cancelled mid-batch
            template_problem = None
            try:
                wamid = await wa.send_template(phone, tname, tlang, params)
                with session() as s:
                    m = s.get(OutboundMessage, mid)
                    m.wa_message_id, m.status, m.sent_at, m.attempts = wamid, "sent", now(), attempts + 1
            except WhatsAppError as e:
                with session() as s:
                    m = s.get(OutboundMessage, mid)
                    m.attempts = attempts + 1
                    m.error = f"{e.code or ''} {e}".strip()
                    m.updated_at = now()
                    if e.code in TEMPLATE_CODES:
                        template_problem = e
                    elif e.code in PERMANENT_CODES or not e.retryable or m.attempts >= 3:
                        m.status = "failed"
            if template_problem:
                camp.set_campaign_status(cid, "paused", f"Template problem from Meta: {template_problem}")
                camp.notify_campaign(cid, f"Meta template ke saath problem bata raha hai ({template_problem}). "
                                          "Maine campaign rok diya hai.")
                break
            await asyncio.sleep(gap)
        camp.publish_campaign(cid)


async def finish_campaigns() -> None:
    """A campaign is complete when nothing is queued; the report goes out once statuses settle."""
    with session() as s:
        rows = s.scalars(select(Campaign).where(Campaign.status == "sending")).all()
        ids = [c.id for c in rows]
    for cid in ids:
        with session() as s:
            queued = s.scalar(select(func.count()).where(OutboundMessage.campaign_id == cid,
                                                         OutboundMessage.status == "queued")) or 0
            last_sent = s.scalar(select(func.max(OutboundMessage.sent_at)).where(OutboundMessage.campaign_id == cid))
        if queued:
            continue
        settle = 10 if get_whatsapp().dry_run else 120
        last_sent = as_utc(last_sent)
        if last_sent and (now() - last_sent).total_seconds() < settle:
            continue
        v = camp.set_campaign_status(cid, "completed")
        with session() as s:
            c = s.get(Campaign, cid)
            already = c.report_sent
            c.report_sent = True
        if not already:
            camp.notify_campaign(cid, camp.report_text(v) + "\nJaise-jaise log padhenge, report apne aap update hoti rahegi.")


async def pump_simulated_statuses() -> None:
    events = await get_whatsapp().poll_simulated_events()
    if events:
        for cid in camp.apply_message_status(events):
            camp.publish_campaign(cid)


async def fire_reminders() -> None:
    from . import life
    from .db import Reminder
    from .events import notify
    with session() as s:
        due = s.scalars(select(Reminder).where(Reminder.status == "active", Reminder.due_at <= now())
                        .order_by(Reminder.due_at).limit(100)).all()
        due = [(r.id, r.tenant_id, r.conversation_id, r.text) for r in due]
    touched: dict[str, str] = {}
    for rid, tenant, conv, text in due:
        notify(conv, f"Yaad dila raha hoon: {text}")
        bus.publish(conv, "reminder", {"id": rid, "text": text})
        tz = life.tz_of(tenant)
        with session() as s:
            r = s.get(Reminder, rid)
            r.fired_count += 1
            nxt = life.next_due(r.due_at, r.repeat, tz)
            while nxt is not None and nxt <= now():      # catch up after downtime without spamming
                nxt = life.next_due(nxt, r.repeat, tz)
            if nxt is None:
                r.status = "done"
            else:
                r.due_at = nxt
        touched[conv] = tenant
    for conv, tenant in touched.items():
        bus.publish(conv, "reminders", {"reminders": life.upcoming_reminders(tenant)})


async def morning_briefings() -> None:
    from datetime import datetime as _dt
    from . import life
    from .db import Conversation, Profile
    from .events import notify
    with session() as s:
        rows = s.scalars(select(Profile).where(Profile.briefing_time.is_not(None))).all()
        rows = [(p.tenant_id, p.briefing_time, p.briefing_conversation_id, p.last_briefing_date) for p in rows]
    for tenant, at, conv, last in rows:
        tz = life.tz_of(tenant)
        local = _dt.now(tz)
        today = local.date().isoformat()
        hh, mm = [int(x) for x in at.split(":")]
        minutes_late = (local.hour * 60 + local.minute) - (hh * 60 + mm)
        if last == today or not (0 <= minutes_late <= 180):
            continue
        with session() as s:
            if not conv or not s.get(Conversation, conv):
                continue
            p = s.get(Profile, tenant)
            p.last_briefing_date = today   # mark first, so a slow weather call never sends it twice
        text = await life.compose_briefing(tenant)
        notify(conv, text)
        bus.publish(conv, "briefing", {"text": text, "date": today})


_routine_tasks: set = set()


async def run_routines() -> None:
    """Jobs Santosh gave himself: run each due one as an agent turn; the reply reaches the phone
    through the event stream (the app's background service turns it into a notification)."""
    from . import life
    from .agent import run_turn
    from .db import Conversation, Routine
    with session() as s:
        due = s.scalars(select(Routine).where(Routine.status == "active", Routine.next_run <= now())
                        .order_by(Routine.next_run).limit(10)).all()
        jobs = []
        for r in due:
            tz = life.tz_of(r.tenant_id)
            nxt = life.next_due(r.next_run, r.repeat, tz)
            while nxt is not None and nxt <= now():   # after downtime run once, not once per missed slot
                nxt = life.next_due(nxt, r.repeat, tz)
            r.run_count += 1
            r.last_run = now()
            if nxt is None:
                r.status = "done"
            else:
                r.next_run = nxt
            if s.get(Conversation, r.conversation_id):
                jobs.append((r.id, r.tenant_id, r.conversation_id, r.title, r.instruction))
    for rid, tenant, conv, title, instruction in jobs:
        prompt = (f'[Automatic job "{title}" is running now at its scheduled time. The user is not in the chat and '
                  f"will read your reply as a phone notification. Do the task with your tools, then reply with the result "
                  f"in 1-3 short sentences. Do not ask questions and do not create new automatic jobs.]\n{instruction}")

        async def _go(rid=rid, tenant=tenant, conv=conv, prompt=prompt):
            try:
                out = await run_turn(conv, prompt, tenant_id=tenant, actor="routine")
            except Exception as e:   # never let one job kill the worker
                log.exception("routine %s failed", rid)
                out = f"failed: {e}"
            with session() as s:
                r = s.get(Routine, rid)
                if r:
                    r.last_result = (out or "")[:2000]
            bus.publish(conv, "routines", {"routines": life.active_routines(tenant)})

        t = asyncio.create_task(_go())
        _routine_tasks.add(t)
        t.add_done_callback(_routine_tasks.discard)


def expire_device_actions() -> None:
    from .db import DeviceAction
    with session() as s:
        old = s.scalars(select(DeviceAction).where(DeviceAction.status == "pending",
                                                   DeviceAction.created_at < now() - timedelta(minutes=15))).all()
        for a in old:
            a.status = "expired"
        expired = [(a.conversation_id, a.type) for a in old]
    from .events import notify
    for conv, typ in expired:
        notify(conv, f"Yeh kaam phone par nahi pahuncha ({typ.replace('_', ' ')}). Phone par Santosh app mein "
                     "Profile > 'Background mein kaam' on rakhiye aur internet chalu rakhiye.")


async def tick() -> None:
    await check_approvals()
    await send_batches()
    await pump_simulated_statuses()
    await finish_campaigns()
    await fire_reminders()
    await morning_briefings()
    await run_routines()
    expire_device_actions()
    await bazar_reminders()
    await offline_digests()
    await pc_cleanup()
    await home_device_alerts()
    await mail_jobs()
    await employee_jobs()
    kaam_jobs()


_kaam_last = 0.0


def kaam_jobs() -> None:
    """v0.136 jobs that say 'working' but stopped moving -> told once; old rows dropped daily."""
    global _kaam_last
    try:
        from . import kaamwatch
        kaamwatch.tick()
        if time.time() - _kaam_last > 86400:
            _kaam_last = time.time()
            kaamwatch.forget_old(30)
    except Exception:
        log.exception("kaam watch tick failed")


_home_last = 0.0


async def home_device_alerts() -> None:
    """Linked fridge / washer alerts (door open, fridge warm, washing done), every 5 minutes, each alert once.
    Skipped with the offline sandbox clouds so demo appliances don't message real chats."""
    global _home_last
    if time.time() - _home_last < 300:
        return
    _home_last = time.time()
    from .bazar.config import get_settings as bz_settings
    if bz_settings().device_cloud_mode == "sandbox":
        return
    try:
        from .bazar import devices as home
        await asyncio.to_thread(home.alerts_tick)
    except Exception:
        log.exception("home device alerts failed")


_pc_last = 0.0


async def pc_cleanup() -> None:
    """Delete PC<->phone relay files after their time is up."""
    global _pc_last
    if time.time() - _pc_last < 1800:
        return
    _pc_last = time.time()
    try:
        from .pc import service as pcs
        await asyncio.to_thread(pcs.cleanup_files)
    except Exception:
        log.exception("pc cleanup failed")


_offline_last = 0.0


async def offline_digests() -> None:
    """Phone silent for a while: email Santosh's updates (every 2 min check)."""
    global _offline_last
    import time
    if time.time() - _offline_last < 120:
        return
    _offline_last = time.time()
    from . import offline
    try:
        await offline.send_due()
    except Exception:
        log.exception("offline digest failed")


_bazar_last = 0.0


async def bazar_reminders() -> None:
    """Bill / birthday / medicine reminders from Bazar packs (checked every 30 s)."""
    global _bazar_last
    import time
    if time.time() - _bazar_last < 30:
        return
    _bazar_last = time.time()
    from .bazar import service as bazar
    try:
        await asyncio.to_thread(bazar.fire_due_reminders)
    except Exception:
        log.exception("bazar reminders failed")


_mail_last = {"bulk": 0.0, "scheduled": 0.0, "watch": 0.0, "cal": 0.0, "forms": 0.0, "photos": 0.0, "hoola": 0.0}


async def mail_jobs() -> None:
    """Email: bulk mail at its pace (every few seconds), scheduled sends (every minute), follow-ups (every 10 min)."""
    from .mailbox import service as ms
    t = time.time()
    jobs = []
    if t - _mail_last["bulk"] >= 3:
        _mail_last["bulk"] = t
        jobs.append(ms.bulk_tick)
    if t - _mail_last["scheduled"] >= 60:
        _mail_last["scheduled"] = t
        jobs.append(ms.send_due_scheduled)
    if t - _mail_last["watch"] >= 600:
        _mail_last["watch"] = t
        jobs.append(ms.check_watches)
    if t - _mail_last["cal"] >= 120:            # Google Calendar: "10 minute mein meeting" nudges
        _mail_last["cal"] = t
        from .cal import service as cs
        jobs.append(cs.alerts_tick)
    if t - _mail_last["forms"] >= 600:          # Google Forms: "N naye jawab" alerts
        _mail_last["forms"] = t
        from .forms import service as fsv
        jobs.append(fsv.alerts_tick)
    if t - _mail_last["photos"] >= 15:          # Google Photos: did the user finish picking?
        _mail_last["photos"] = t
        from .photos import service as phs
        jobs.append(phs.poll_tick)
    if t - _mail_last.get("dosti", 0) >= 10:    # v0.160 Dosti: friends' avatars get their reply within seconds
        _mail_last["dosti"] = t
        from .net import dosti as hdosti
        jobs.append(hdosti.tick)
    if t - _mail_last["hoola"] >= 60:           # Hoola Network: snoozed requests, quiet hours over
        _mail_last["hoola"] = t
        from .net import service as hns
        jobs.append(hns.tick)
        from .net import deal as hdeal
        jobs.append(hdeal.tick)                 # v0.102 quotes past their time -> expired
        from .net import dealpay as hdealpay, khata as hkhata
        jobs.append(hdealpay.tick)              # v0.106 unaccepted orders, unpaid cards, cancel requests, disputes, auto-close
        jobs.append(hkhata.tick)                # v0.106 khata due-date reminders
        from .net import mandate as hmandate, rfq as hrfq
        jobs.append(hrfq.tick)                  # v0.112 compare windows that ended -> the table
        jobs.append(hmandate.tick)              # v0.112 standing orders: runs, holds that are over
        from .net import booking as hbooking
        jobs.append(hbooking.tick)              # v0.113 booking reminders (1 day / 2 h before, her morning)
        from .net import a2a as ha2a
        jobs.append(ha2a.tick)                  # v0.116 outside agents: poll her sent tasks, close idle ones
        from .handoff import aa as hoaa, abdm as hoabdm
        jobs.append(hoaa.tick)                  # v0.116 AA consent revoke reminders / expiry
        jobs.append(hoabdm.tick)                # v0.116 ABDM consent revoke reminders / expiry
        if int(t) // 60 % 60 == 0:              # hourly: old quarantined files and shares
            from .net import share as hsh
            jobs.append(hsh.cleanup)
    for job in jobs:
        try:
            await asyncio.to_thread(job)
        except Exception:
            log.exception("mail/calendar job %s failed", job.__name__)


_emp_tasks: set = set()
_inbox_tasks: set = set()


_gyaan_at = 0.0


async def employee_jobs() -> None:
    """Hoola Employee: team tasks, old asks expire, the daily report at the owner's time."""
    from .employee import network as emp_net
    from .employee import service as emp
    try:
        emp.expire_asks()
        for tenant in emp.due_reports():
            emp.send_report(tenant)
    except Exception:
        log.exception("employee report failed")
    try:                                   # v0.82 Darzi: the morning list of trials / deliveries / late orders
        from .darzi import service as darzi
        for tenant in darzi.due_mornings():
            darzi.send_morning(tenant)
    except Exception:
        log.exception("darzi morning failed")
    try:                                   # v0.84 Chai: today's galla + tomorrow's milk / sugar plan at her time
        from .chai import service as chai
        for tenant in chai.due_plans():
            await chai.evening(tenant)
    except Exception:
        log.exception("chai evening failed")
    try:                                   # v0.98 Bima: premiums due / grace / lapsed, birthdays, stuck claims
        from .insure import service as insure
        for tenant in insure.due_mornings():
            insure.send_morning(tenant)
    except Exception:
        log.exception("insure morning failed")
    try:                                   # v0.95 Paisa: MSME payment deadlines, late customers, advance tax
        from .analyst import service as analyst
        for tenant in analyst.due_mornings():
            analyst.send_morning(tenant)
    except Exception:
        log.exception("analyst morning failed")
    try:                                   # v0.94 Payroll: salary / PF / ESIC / TDS due and late at her time
        from .payroll import service as payroll
        for tenant in payroll.due_mornings():
            payroll.send_morning(tenant)
    except Exception:
        log.exception("payroll morning failed")
    try:                                   # v0.93 GST: due today / late / notices for every client at her time
        from .gstp import service as gstp
        for tenant in gstp.due_mornings():
            gstp.send_morning(tenant)
    except Exception:
        log.exception("gst morning failed")
    try:                                   # v0.99 Telecaller: today's call list, each with a reason
        from .theka import service as theka
        for tenant in theka.due_mornings():
            theka.send_morning(tenant)
    except Exception:
        log.exception("theka morning failed")
    try:
        from .franchise import service as franchise
        for tenant in franchise.due_mornings():
            franchise.send_morning(tenant)
    except Exception:
        log.exception("franchise morning failed")
    try:
        from .niryat import service as niryat
        for tenant in niryat.due_mornings():
            niryat.send_morning(tenant)
    except Exception:
        log.exception("niryat morning failed")
    try:
        from .thok import service as thok
        for tenant in thok.due_mornings():
            thok.send_morning(tenant)
    except Exception:
        log.exception("thok morning failed")
    try:                                   # v0.111 Ads: daily leak check (Meta joined) + weekly report at her time
        from .ads import service as ads
        for tenant, kind in ads.due_checks():
            ads.send_check(tenant, kind)
    except Exception:
        log.exception("ads check failed")
    try:                                   # v0.118 Brand: offer a festival poster set a week before (once per festival)
        from .brand import service as brand
        for tenant, fest in brand.due_nudges():
            brand.send_nudge(tenant, fest)
    except Exception:
        log.exception("brand nudge failed")
    try:                                   # v0.134 Gyaan: Drive folders daily, mail every 30 min (only owners who turned it on)
        global _gyaan_at
        if time.time() - _gyaan_at > 600:
            _gyaan_at = time.time()
            from .gyaan import ingest as _gy
            for _t in await asyncio.to_thread(_gy.tenants_with_gyaan):
                await asyncio.to_thread(_gy.daily, _t)
    except Exception:
        log.exception("gyaan sync failed")
    # v0.133 Seva suite: SLA timers, reminders, morning notes, imports (each throttles itself)
    try:
        from .seva import service as _seva_svc
        await asyncio.to_thread(_seva_svc.tick)
    except Exception:
        log.exception("seva tick failed")
    try:
        from .helpdesk import service as _helpdesk_svc
        await asyncio.to_thread(_helpdesk_svc.tick)
    except Exception:
        log.exception("helpdesk tick failed")
    try:
        from .shikayat import service as _shikayat_svc
        await asyncio.to_thread(_shikayat_svc.tick)
    except Exception:
        log.exception("shikayat tick failed")
    try:
        from .aftersales import service as _aftersales_svc
        await asyncio.to_thread(_aftersales_svc.tick)
    except Exception:
        log.exception("aftersales tick failed")
    try:
        from .feedback import service as _feedback_svc
        await asyncio.to_thread(_feedback_svc.tick)
    except Exception:
        log.exception("feedback tick failed")
    try:
        from .wapsi import service as _wapsi_svc
        await asyncio.to_thread(_wapsi_svc.tick)
    except Exception:
        log.exception("wapsi tick failed")
    try:
        from .samudaay import service as _samudaay_svc
        await asyncio.to_thread(_samudaay_svc.tick)
    except Exception:
        log.exception("samudaay tick failed")
    try:
        from .callcentre import service as _callcentre_svc
        await asyncio.to_thread(_callcentre_svc.tick)
    except Exception:
        log.exception("callcentre tick failed")
    # v0.137 Tech suite: CI / deploy polling, renewals, alerts, morning notes, scheduled test runs (each throttles itself)
    for _mod in ("devsahayak", "qa", "itadmin", "ispnoc", "cyber", "devops", "docwriter", "appreview", "product"):
        try:
            import importlib
            _svc = importlib.import_module(f".{_mod}.service", __package__)
            await asyncio.to_thread(_svc.tick)
        except Exception:
            log.exception("%s tick failed", _mod)
    # v0.139 Safar suite: shipments / e-way bills, fleet papers, godown notes, courier tracking, travel reminders, driver duties,
    # import clocks (each throttles itself)
    for _mod in ("customs", "travel", "warehouse", "fleet", "courier", "drivers", "logistics"):
        try:
            import importlib
            _svc = importlib.import_module(f".{_mod}.service", __package__)
            await asyncio.to_thread(_svc.tick)
        except Exception:
            log.exception("%s tick failed", _mod)
    # v0.144 Makaan suite: visit / RERA reminders, rent billing + reminder drafts, cube tests / Form XI clocks / DPR reminder,
    # interior tasks + stages, architect RFIs / approvals / invoices, society calendar (each throttles itself)
    for _mod in ("propagent", "rentdesk", "sitesup", "interior", "archassist", "society"):
        try:
            import importlib
            _svc = importlib.import_module(f".{_mod}.service", __package__)
            await asyncio.to_thread(_svc.tick)
        except Exception:
            log.exception("%s tick failed", _mod)
    # v0.150 Kanoon suite: court diary / limitation, compliance calendar, contract renewals, MCA calendar, notary renewals,
    # PI desk reminders, DPDP breach / request clocks (each throttles itself; legalres.tick does nothing)
    for _mod in ("vakil", "legalres", "compliance", "contracts", "cosec", "notary", "pidesk", "dpo"):
        try:
            import importlib
            _svc = importlib.import_module(f".{_mod}.service", __package__)
            await asyncio.to_thread(_svc.tick)
        except Exception:
            log.exception("%s tick failed", _mod)
    # v0.152 Mehmaan suite: holds / Form C / no-shows, event + wedding + tour reminders, homestay holds / calendar, banquet holds /
    # final counts, morning notes (each throttles itself with once-keys)
    for _mod in ("frontoffice", "eventplan", "shaadi", "tourguide", "homestay", "banquet"):
        try:
            import importlib
            _svc = importlib.import_module(f".{_mod}.service", __package__)
            await asyncio.to_thread(_svc.tick)
        except Exception:
            log.exception("%s tick failed", _mod)
    # v0.156 Kala suite: edit / motion / film desks, journalist, photo, graphic, artist, kitab, podcast, influencer (engine sync,
    # deadlines, holds, unpaid bills, licences, morning notes; each throttles itself with once-keys)
    for _mod in ("editdesk", "motiondesk", "filmdesk", "patrakar", "photoassist", "graphic", "artistmgr", "kitab", "podcast", "influencer"):
        try:
            import importlib
            _svc = importlib.import_module(f".{_mod}.service", __package__)
            await asyncio.to_thread(_svc.tick)
        except Exception:
            log.exception("%s tick failed", _mod)
    try:                                   # v0.122 Website: her domain's DNS / SSL coming up, uptime of live sites
        from .site import hosting as site_hosting
        await asyncio.to_thread(site_hosting.watch)
    except Exception:
        log.exception("site hosting watch failed")
    try:                                   # v0.123 domains: registry result, .in KYC + renewal reminders
        from .site import domains as site_domains
        await asyncio.to_thread(site_domains.tick)
    except Exception:
        log.exception("site domains tick failed")
    try:                                   # v0.124 care: visit counters to the DB, monthly care note on the 1st
        from .site import care as site_care
        await asyncio.to_thread(site_care.flush)
        await asyncio.to_thread(site_care.monthly)
    except Exception:
        log.exception("site care failed")
    try:
        from .seo import service as seo
        for tenant in seo.due_mornings():
            seo.send_morning(tenant)
    except Exception:
        log.exception("seo weekly failed")
    try:
        from .telecall import service as telecall
        for tenant in telecall.due_mornings():
            telecall.send_morning(tenant)
    except Exception:
        log.exception("telecall morning failed")
    try:                                   # v0.88 Mobile dukaan: the morning list (jobs, bills, recharges ending)
        from .mshop import service as mshop
        for tenant in mshop.due_mornings():
            mshop.send_morning(tenant)
    except Exception:
        log.exception("mshop morning failed")
    try:                                   # v0.85 Daftar: morning office list + the weekly office note
        from .office import service as office
        for tenant in office.due_mornings():
            office.send_morning(tenant)
        for tenant in office.due_notes():
            office.send_note(tenant)
    except Exception:
        log.exception("office morning / note failed")
    if not _emp_tasks:                    # one batch at a time; the next tick picks up the rest
        t = asyncio.create_task(emp_net.run_pending())
        _emp_tasks.add(t)
        t.add_done_callback(_emp_tasks.discard)
    if not _inbox_tasks:                  # WhatsApp customers: queued notices, then replies
        from .employee import inbox as biz_inbox

        async def _inbox():
            await biz_inbox.flush_queued()
            await biz_inbox.answer_pending()
        t2 = asyncio.create_task(_inbox())
        _inbox_tasks.add(t2)
        t2.add_done_callback(_inbox_tasks.discard)


async def run_forever(stop: asyncio.Event) -> None:
    st = get_settings()
    log.info("worker started (dry_run=%s)", st.wa_dry_run)
    while not stop.is_set():
        try:
            await tick()
        except Exception:
            log.exception("worker tick failed")
        try:   # v0.98 counted model calls reach the database even when nothing else is happening
            from . import usage
            await asyncio.to_thread(usage.flush)
        except Exception:
            log.exception("usage flush failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=st.worker_tick_seconds)
        except asyncio.TimeoutError:
            pass
