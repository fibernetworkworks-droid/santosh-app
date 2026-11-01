"""v0.366 SOCIAL MEDIA MANAGER Phase 4 of docs/SOCIAL_EMPLOYEE_PLAN.md - 24/7 + reports:
- Posting by trust (plan section 6): a post approved only as part of the monthly plan ("seen" = 0) goes out on its own only
  for Saathi (told the same day) / Bharosa (weekly summary), within the daily cap (0 / 6 / 15) and outside quiet hours
  (23:00-07:00 unless she sets them). Seekh: such a post waits for her OK on the day (the morning note lists it). A post she
  approved herself or tapped Publish now on goes at its time, as in Phase 2.
- Pause all posting (also stops automatic replies) and an emergency Stop that also sends every queued post back to draft.
- Morning note (9 am, only when something needs her): posts waiting for her OK today, complaints waiting, a festival in 7 days.
- Weekly pulse (Monday): two lines in her chat - this week vs last week, the best post, leads.
- Monthly PDF (1st of the month): key takeaways, numbers against the baseline, top / bottom posts, work done, next month.
- Best-time engine: her own weekday x hour results, smoothed, with how sure it is; fed to the planner.
- Boost-worthy flags: a recent post doing 2x her normal gets a written boost plan for HER to run in Meta (Hoola never pays
  for or creates ads)."""
from __future__ import annotations

import json
import logging
import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select

from ..db import as_utc, now, session
from .desk import (KEY, SocialAccount, SocialDesk, SocialEvent, SocialMedia, SocialPost, SocialError, _desk, _eng, _hired, _j,
                   _local, ensure_tables, kpis, measure)

log = logging.getLogger("santosh.social.pulse")
POST_CAP = {"seekh": 0, "saathi": 6, "bharosa": 15}
QUIET_DEFAULT = [23, 7]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
BOOST_X = 2.0


# ---------------------------------------------------------------- her switches
def trust_of(tenant: str) -> str:
    from ..employee import hire
    return next((c.get("trust") for c in hire.catalog(tenant) if c["key"] == KEY), "seekh") or "seekh"


def settings(tenant: str) -> dict[str, Any]:
    ensure_tables()
    with session() as s:
        d = s.get(SocialDesk, tenant)
        st = _j(d.settings, {}) if d is not None and d.settings else {}
    q = st.get("quiet") if isinstance(st.get("quiet"), list) and len(st.get("quiet")) == 2 else QUIET_DEFAULT
    return {"paused": bool(st.get("paused")), "pause_reason": str(st.get("pause_reason") or ""), "paused_at": st.get("paused_at", ""),
            "quiet": [int(q[0]) % 24, int(q[1]) % 24]}


def set_settings(tenant: str, paused: bool | None = None, quiet: list[int] | None = None, stop: bool = False,
                 reason: str = "") -> dict[str, Any]:
    """Pause / resume all posting (+ automatic replies); Stop = pause + every queued post back to draft."""
    _hired(tenant)
    cur = settings(tenant)
    if stop:
        paused = True
    if paused is not None:
        cur["paused"] = bool(paused)
        cur["pause_reason"] = str(reason or ("Emergency stop" if stop else ""))[:200] if paused else ""
        cur["paused_at"] = now().isoformat(timespec="seconds") if paused else ""
    if quiet is not None:
        try:
            a, b = int(quiet[0]), int(quiet[1])
        except (TypeError, ValueError, IndexError):
            raise SocialError("quiet: [shuru ghanta, khatam ghanta], jaise [23, 7]")
        if not (0 <= a <= 23 and 0 <= b <= 23):
            raise SocialError("Ghanta 0 se 23 ke beech.")
        cur["quiet"] = [a, b]
    back = 0
    with session() as s:
        d = _desk(s, tenant)
        d.settings = json.dumps(cur)
        if stop:
            for p in s.scalars(select(SocialPost).where(SocialPost.tenant_id == tenant, SocialPost.status.in_(("approved", "failed")))).all():
                p.status, p.approved_hash = "draft", ""
                back += 1
        if paused is not None:
            s.add(SocialEvent(tenant_id=tenant, kind="note", level="warn" if cur["paused"] else "ok", text=(
                f"Emergency stop: all posting and automatic replies stopped; {back} queued post(s) are drafts again."
                if stop else "Posting and automatic replies paused. Nothing goes out until you resume."
                if cur["paused"] else "Resumed: approved posts go out at their time again.")))
    return {**cur, "back_to_draft": back}


def is_paused(tenant: str) -> bool:
    return settings(tenant)["paused"]


def in_quiet(hour: int, quiet: list[int]) -> bool:
    a, b = quiet
    if a == b:
        return False
    return a <= hour < b if a < b else (hour >= a or hour < b)


def auto_posts_today(tenant: str, local: datetime) -> int:
    """Plan posts that went out on their own for this local day (counted by the post's day, or sent today)."""
    from sqlalchemy import or_
    day = local.replace(hour=0, minute=0, second=0, microsecond=0)
    with session() as s:
        return s.scalar(select(func.count()).select_from(SocialPost).where(
            SocialPost.tenant_id == tenant, SocialPost.seen == 0, SocialPost.status.in_(("published", "publishing")),
            or_(SocialPost.slot.like(local.date().isoformat() + "%"), SocialPost.published_at >= day))) or 0


def may_go(tenant: str, p: SocialPost, local: datetime, trust: str, quiet: list[int], used: int) -> str:
    """'' = may go now; else why it waits. A post she OK'd herself (seen 1 / old rows None) is never held by trust."""
    if p.seen is None or p.seen == 1:
        return ""
    if trust not in ("saathi", "bharosa"):
        return "her_ok"
    if in_quiet(local.hour, quiet):
        return "quiet"
    if used >= POST_CAP.get(trust, 0):
        return "cap"
    return ""


def waiting_ok(tenant: str, day: str | None = None) -> list[dict[str, Any]]:
    """Seekh: plan-approved posts (not OK'd one by one) due today or overdue - they wait for her OK."""
    if trust_of(tenant) in ("saathi", "bharosa"):
        return []
    day = day or _local(tenant).date().isoformat()
    with session() as s:
        rows = s.scalars(select(SocialPost).where(SocialPost.tenant_id == tenant, SocialPost.status == "approved",
                                                  SocialPost.seen == 0)).all()
        return [{"id": p.id, "slot": p.slot, "hook": p.hook} for p in rows if (p.slot or "")[:10] <= day]


# ---------------------------------------------------------------- best-time engine
def best_times(tenant: str) -> dict[str, Any]:
    """Her own posts' results by weekday x 3-hour band, each post relative to that account's median (so the Page and the
    Instagram account can be mixed), shrunk toward 1.0 with k = 3 posts (few posts -> little trust)."""
    from ..life import tz_of
    tz = tz_of(tenant)
    with session() as s:
        media = s.scalars(select(SocialMedia).where(SocialMedia.tenant_id == tenant)).all()
        rows = [(m.account, _eng(m), as_utc(m.posted_at)) for m in media if m.posted_at]
    if len(rows) < 6:
        return {"slots": [], "by_day": {}, "posts": len(rows), "sure": "low",
                "note": "Not enough of your posts yet; using common Indian evening and lunch hours."}
    med = {a: max(1.0, statistics.median([e for aa, e, _ in rows if aa == a])) for a in {r[0] for r in rows}}
    cell: dict[tuple[int, int], list[float]] = defaultdict(list)
    for acc, e, at in rows:
        loc = at.astimezone(tz)
        cell[(loc.weekday(), loc.hour // 3)].append(e / med[acc])
    k = 3.0
    scored = []
    for (d, band), xs in cell.items():
        score = (sum(xs) + k * 1.0) / (len(xs) + k)
        scored.append({"day": DAYS[d], "hour": band * 3 + 1, "band": f"{band * 3:02d}:00-{band * 3 + 3:02d}:00",
                       "lift": round(score, 2), "posts": len(xs)})
    scored.sort(key=lambda x: (-x["lift"], -x["posts"]))
    by_day: dict[str, int] = {}
    for x in scored:
        by_day.setdefault(x["day"], x["hour"])
    n = len(rows)
    return {"slots": scored[:5], "by_day": by_day, "posts": n, "sure": "high" if n >= 40 else "medium" if n >= 15 else "low",
            "note": ""}


# ---------------------------------------------------------------- boost-worthy
def boost_flags(tenant: str, days: int = 14) -> list[dict[str, Any]]:
    """Recent posts doing BOOST_X x her normal (median interactions of that account, >= 8 posts read, >= 20 interactions).
    Each gets a boost plan for her to run in Meta herself; Hoola never creates or pays for an ad."""
    with session() as s:
        media = s.scalars(select(SocialMedia).where(SocialMedia.tenant_id == tenant)).all()
        d = s.get(SocialDesk, tenant)
        prof = _j(d.profile, {}) if d else {}
        rows = [{"id": m.media_id, "account": m.account, "platform": m.platform, "fmt": m.fmt, "eng": _eng(m),
                 "caption": (m.caption or "")[:120], "permalink": m.permalink, "at": as_utc(m.posted_at) if m.posted_at else None}
                for m in media]
    by_acc: dict[str, list[int]] = defaultdict(list)
    for r in rows:
        by_acc[r["account"]].append(r["eng"])
    cut = now() - timedelta(days=days)
    out = []
    city = prof.get("city") or "your city"
    for r in rows:
        base = by_acc[r["account"]]
        if len(base) < 8 or not r["at"] or r["at"] < cut:
            continue
        med = statistics.median(base)
        if r["eng"] >= 20 and r["eng"] >= BOOST_X * max(med, 1):
            out.append({**{k: v for k, v in r.items() if k != "at"}, "date": r["at"].date().isoformat(), "times": round(r["eng"] / max(med, 1), 1),
                        "plan": (f"Boost this in Meta (Ads Manager or the Boost button): people within 15 km of {city}"
                                 f"{', interested in ' + prof['sells'][:60] if prof.get('sells') else ''}, Rs 300 a day for 3 days, "
                                 "goal = messages / profile visits. Stop after 3 days and compare the leads with the money spent.")})
    out.sort(key=lambda x: -x["times"])
    return out[:5]


def flag_boosts(tenant: str) -> int:
    """Daily: tell her once per post."""
    flags = boost_flags(tenant)
    new = 0
    with session() as s:
        d = _desk(s, tenant)
        st = _j(d.stamps, {})
        seen = set(st.get("boosted") or [])
        for f in flags:
            if f["id"] in seen:
                continue
            seen.add(f["id"])
            new += 1
            s.add(SocialEvent(tenant_id=tenant, kind="note", level="ok", text=(
                f"Boost-worthy: your {f['fmt']} from {f['date']} has {f['eng']} interactions, {f['times']}x your normal. {f['plan']}")))
        st["boosted"] = sorted(seen)[-200:]
        d.stamps = json.dumps(st)
    return new


# ---------------------------------------------------------------- telling her
def _say(tenant: str, kind: str, text: str, conv: str = "") -> None:
    try:
        from ..seo.service import _publish
        _publish(tenant, kind, {"text": text[:600]}, conv)
    except Exception:            # noqa: BLE001
        pass


def morning(tenant: str) -> dict[str, Any]:
    """9 am - only when something needs her today."""
    from .desk import _occasions
    from .inbox import counts
    local = _local(tenant)
    bits = []
    w = waiting_ok(tenant)
    if w:
        bits.append(f"{len(w)} planned post(s) for today wait for your OK ({w[0]['hook'][:50]}).")
    c = counts(tenant)
    if c.get("complaints"):
        bits.append(f"{c['complaints']} complaint(s) on Instagram / Facebook wait for your reply.")
    elif c.get("needs"):
        bits.append(f"{c['needs']} comment(s) / DM(s) wait for you.")
    occ = _occasions(tenant, local.date(), 8)
    soon = [(d, n) for d, n in sorted(occ.items()) if d == (local.date() + timedelta(days=7)).isoformat()]
    if soon:
        bits.append(f"{soon[0][1]} is in 7 days - tell me if you want a special post.")
    if settings(tenant)["paused"]:
        bits.append("Posting is paused.")
    if not bits:
        return {"sent": False}
    text = "Social Desk: " + " ".join(bits)
    with session() as s:
        s.add(SocialEvent(tenant_id=tenant, kind="note", level="info", text=text[:600]))
    _say(tenant, "social_day", text)
    return {"sent": True, "text": text}


def _week(tenant: str, start: datetime, end: datetime) -> dict[str, Any]:
    with session() as s:
        media = s.scalars(select(SocialMedia).where(SocialMedia.tenant_id == tenant)).all()
        posts = [(m.fmt, _eng(m), m.reach, (m.caption or "")[:60]) for m in media
                 if m.posted_at and start <= as_utc(m.posted_at) < end]
        hoola = s.scalar(select(func.count()).select_from(SocialPost).where(
            SocialPost.tenant_id == tenant, SocialPost.status == "published", SocialPost.published_at >= start,
            SocialPost.published_at < end)) or 0
        auto = s.scalar(select(func.count()).select_from(SocialPost).where(
            SocialPost.tenant_id == tenant, SocialPost.status == "published", SocialPost.seen == 0,
            SocialPost.published_at >= start, SocialPost.published_at < end)) or 0
    leads = replied = 0
    try:
        from .inbox import SocialInbox, ensure_inbox
        ensure_inbox()
        with session() as s:
            leads = s.scalar(select(func.count()).select_from(SocialInbox).where(
                SocialInbox.tenant_id == tenant, SocialInbox.cls == "lead", SocialInbox.created_at >= start,
                SocialInbox.created_at < end)) or 0
            replied = s.scalar(select(func.count()).select_from(SocialInbox).where(
                SocialInbox.tenant_id == tenant, SocialInbox.status == "replied", SocialInbox.replied_at >= start,
                SocialInbox.replied_at < end)) or 0
    except Exception:            # noqa: BLE001
        pass
    best = max(posts, key=lambda x: x[1]) if posts else None
    return {"posts": len(posts), "eng": sum(p[1] for p in posts), "reach": sum(p[2] or 0 for p in posts),
            "best": best, "hoola_posts": hoola, "auto_posts": auto, "leads": leads, "replied": replied}


def weekly_pulse(tenant: str) -> dict[str, Any]:
    """Monday: two lines in her chat - this week against last week."""
    from .desk import daily
    try:
        daily(tenant)                       # fresh numbers first
    except Exception as e:                  # noqa: BLE001
        log.info("weekly refresh failed: %s", e)
    end = now()
    a = _week(tenant, end - timedelta(days=7), end)
    b = _week(tenant, end - timedelta(days=14), end - timedelta(days=7))

    def ch(x, y):
        return "" if not y else f" ({'+' if x >= y else ''}{round((x - y) * 100 / y)}% vs last week)"
    line1 = (f"This week {a['posts']} post(s) got {a['eng']:,} interactions{ch(a['eng'], b['eng'])}"
             + (f" and reached {a['reach']:,} people" if a["reach"] else "") + ".")
    tail = []
    if a["best"]:
        tail.append(f"the best post was a {a['best'][0]} ({a['best'][1]} interactions)")
    if a["leads"]:
        tail.append(f"{a['leads']} lead(s) came in, {a['replied']} replies sent")
    if a["auto_posts"] and trust_of(tenant) == "bharosa":
        tail.append(f"{a['auto_posts']} planned post(s) went out on their own")
    line2 = ("Next: " + "; ".join(tail) + ".") if tail else "Next: keep the approved calendar going; I will flag anything worth a boost."
    text = line1 + "\n" + line2[0].upper() + line2[1:]
    with session() as s:
        s.add(SocialEvent(tenant_id=tenant, kind="note", level="info", text=text.replace("\n", " ")[:600]))
    _say(tenant, "social_week", text)
    return {"this": a, "last": b, "text": text}


# ---------------------------------------------------------------- monthly PDF
def report_markdown(tenant: str) -> tuple[str, str]:
    with session() as s:
        d = s.get(SocialDesk, tenant)
        prof = _j(d.profile, {}) if d else {}
        base = _j(d.baseline, {}) if d else {}
        media = s.scalars(select(SocialMedia).where(SocialMedia.tenant_id == tenant)).all()
        cut = now() - timedelta(days=30)
        recent = sorted([(_eng(m), m.fmt, m.platform, (m.caption or "")[:80].replace("|", "/"), m.permalink,
                          as_utc(m.posted_at).date().isoformat()) for m in media if m.posted_at and as_utc(m.posted_at) >= cut],
                        key=lambda x: -x[0])
    latest = measure(tenant)
    k = kpis(base, latest)
    m = _week(tenant, now() - timedelta(days=30), now())
    bt = best_times(tenant)
    boosts = boost_flags(tenant, 30)
    month = _local(tenant).strftime("%B %Y")
    name = prof.get("business") or "Your business"
    title = f"{name} - social media report, {month}"

    def fmt(v):
        return "–" if v is None else (f"{v:,.1f}" if isinstance(v, float) else f"{v:,}" if isinstance(v, int) else str(v))
    take = [f"{x['name']}: {fmt(x['now'])} ({'+' if x['change_pct'] >= 0 else ''}{x['change_pct']}% since the baseline)"
            for x in k if x["change_pct"] is not None]
    take.append(f"{m['hoola_posts']} post(s) published through Hoola, {m['replied']} replies sent, {m['leads']} lead(s) from "
                "comments and DMs in the last 30 days.")
    lines = ["# Summary", "> [!KEY] " + take[0]] + ["> " + t for t in take[1:5]] + [""]
    for x in [x for x in k if x["now"] is not None][:4]:
        lines.append(f"[stat: {fmt(x['now'])} | {x['name']}]")
    lines += ["", "# Numbers against the baseline", "| Measure | Baseline | Now | Change |", "|---|---|---|---|"]
    for x in k:
        lines.append(f"| {x['name']} | {fmt(x['baseline'])} | {fmt(x['now'])} | "
                     f"{'–' if x['change_pct'] is None else ('+' if x['change_pct'] >= 0 else '') + str(x['change_pct']) + '%'} |")
    lines += ["", "# Best posts this month"]
    if recent:
        lines += ["| Date | Where | Format | Interactions | Post |", "|---|---|---|---|---|"]
        for e, f, p, c, _l, dt in recent[:5]:
            lines.append(f"| {dt} | {p.title()} | {f} | {e:,} | {c or '–'} |")
        if len(recent) > 7:
            lines += ["", "# Posts that did least", "| Date | Format | Interactions | Post |", "|---|---|---|---|"]
            for e, f, p, c, _l, dt in recent[-5:]:
                lines.append(f"| {dt} | {f} | {e:,} | {c or '–'} |")
    else:
        lines.append("No posts were read in the last 30 days.")
    lines += ["", "# Work done", f"- Posts published through Hoola: {m['hoola_posts']} ({m['auto_posts']} from the approved plan on their own).",
              f"- Comments and DMs answered: {m['replied']}; leads found: {m['leads']}."]
    if boosts:
        lines.append(f"- Boost-worthy posts flagged: {len(boosts)} (best {boosts[0]['times']}x your normal).")
    lines += ["", "# Next month"]
    fm = (latest.get("formats") or [{}])[0]
    if fm.get("fmt"):
        lines.append(f"1. More {fm['fmt']}s - they average {fmt(fm.get('avg_eng'))} interactions for you. "
                     "Early sign: interactions per post up within 2 weeks. Not working if: no change after 8 posts.")
    if bt["slots"]:
        s0 = bt["slots"][0]
        lines.append(f"1. Post on {s0['day']} {s0['band']} - your posts there do {s0['lift']}x your normal ({bt['sure']} certainty, "
                     f"{s0['posts']} posts). Early sign: reach per post up. Not working if: same reach after 4 posts there.")
    lines.append("1. Answer every comment within the day - replies bring the next enquiry. Early sign: more DMs. "
                 "Not working if: leads stay flat for the month.")
    return title, "\n".join(lines)


def monthly_report(tenant: str, conv: str = "", make: Any = None) -> dict[str, Any]:
    from .. import chatfiles
    title, text = report_markdown(tenant)
    if make is None:
        from ..agent.docstudio_tools import make_pdf as make
    res = make(title, text, {"style": "auto", "subject": "Monthly social media report", "cover": "auto", "toc": "auto"},
               "Hoola Social Media Manager", title.split(" - ")[0])
    f = chatfiles.store(tenant, f"Social_report_{_local(tenant).strftime('%Y_%m')}.pdf", res["data"], "application/pdf")
    try:
        from ..seo.service import _publish
        _publish(tenant, "pc_file", {**f, "source": "social", "title": title}, conv)
    except Exception:            # noqa: BLE001
        pass
    with session() as s:
        s.add(SocialEvent(tenant_id=tenant, kind="report", level="ok", text=f"Monthly report ready: {title}"))
    return {"file": f, "title": title, "pages": res.get("pages")}


def view(tenant: str) -> dict[str, Any]:
    st = settings(tenant)
    return {"settings": st, "trust": trust_of(tenant), "post_cap": POST_CAP.get(trust_of(tenant), 0),
            "auto_today": auto_posts_today(tenant, _local(tenant)), "waiting_ok": waiting_ok(tenant),
            "best_times": best_times(tenant), "boosts": boost_flags(tenant)}
