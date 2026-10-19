"""The Guard decides whether a Tier 2/3 action can run without a tap.

Tier 0 read · Tier 1 reversible  -> run
Tier 2 spend                       -> auto only if the user raised their caps AND the payee was approved before AND
                                      the amount fits the per-order and per-day caps; else a confirm card
Tier 3 high risk (money to people) -> always a confirm card + UPI PIN
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..connectors.base import NeedsApproval
from ..db import Approval, User


def spent_today(session: Session, user_id: str) -> int:
    start = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) - dt.timedelta(hours=24)
    total = session.scalar(select(func.coalesce(func.sum(Approval.amount_paise), 0)).where(
        Approval.user_id == user_id, Approval.decision.in_(["approved", "auto"]), Approval.decided_at >= start))
    return int(total or 0)


def can_auto_approve(session: Session, user: User, na: NeedsApproval) -> bool:
    if na.tier >= 3 or na.tier < 2:
        return False
    if (na.action or {}).get("executor") == "commerce":
        return False  # shopping orders always show the all-in quote card (E-Commerce Rules: explicit consent)
    if na.amount_paise <= 0:
        return False  # messages to other people (greetings, campaigns) always need a look
    if user.cap_per_order_paise <= 0 or na.amount_paise > user.cap_per_order_paise:
        return False
    if user.cap_per_day_paise and spent_today(session, user.id) + na.amount_paise > user.cap_per_day_paise:
        return False
    seen = session.scalar(select(func.count(Approval.id)).where(Approval.user_id == user.id, Approval.payee == na.payee,
                                                               Approval.decision == "approved"))
    return bool(seen)
