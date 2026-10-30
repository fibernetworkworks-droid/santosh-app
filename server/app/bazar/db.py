"""Bazar models. Own metadata, tables prefixed bz_, stored in Santosh's main database (same engine)."""
from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship



def _id() -> str:
    return uuid.uuid4().hex[:16]


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSON, list[Any]: JSON}


class User(Base):
    __tablename__ = "bz_users"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_id)  # = Santosh tenant id
    phone: Mapped[str] = mapped_column(String(20), default="")
    name: Mapped[str] = mapped_column(String(120), default="")
    language: Mapped[str] = mapped_column(String(8), default="hi")
    city: Mapped[str] = mapped_column(String(80), default="")
    pincode: Mapped[str] = mapped_column(String(10), default="")
    cap_per_order_paise: Mapped[int] = mapped_column(Integer, default=0)
    cap_per_day_paise: Mapped[int] = mapped_column(Integer, default=0)
    profile: Mapped[dict[str, Any]] = mapped_column(default=dict)  # addresses, family, diet, favourites
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class InstalledPack(Base):
    __tablename__ = "bz_installed_packs"
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("bz_users.id"), index=True)
    pack_id: Mapped[str] = mapped_column(String(80), index=True)
    settings: Mapped[dict[str, Any]] = mapped_column(default=dict)  # e.g. saved consumer number
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class Connection(Base):
    """A linked provider account (OAuth/OTP token). Tokens are stored encrypted."""
    __tablename__ = "bz_connections"
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("bz_users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40))
    token_enc: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="active")
    expires_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)


class Contact(Base):
    __tablename__ = "bz_contacts"
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("bz_users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20), default="")
    upi_id: Mapped[str] = mapped_column(String(120), default="")
    relation: Mapped[str] = mapped_column(String(40), default="")
    birthday: Mapped[str] = mapped_column(String(10), default="")      # MM-DD
    anniversary: Mapped[str] = mapped_column(String(10), default="")   # MM-DD


class Task(Base):
    __tablename__ = "bz_tasks"
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("bz_users.id"), index=True)
    conversation_id: Mapped[str] = mapped_column(String(40), default="")
    text: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(8), default="")
    status: Mapped[str] = mapped_column(String(24), default="running")  # running|awaiting_approval|awaiting_payment|done|failed|cancelled
    engine: Mapped[str] = mapped_column(String(12), default="rules")   # rules|claude
    pack_id: Mapped[str] = mapped_column(String(80), default="")
    reply: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[dict[str, Any]] = mapped_column(default=dict)
    conversation: Mapped[list[Any]] = mapped_column(default=list)  # Claude message history while paused
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now, onupdate=now)
    steps: Mapped[list["TaskStep"]] = relationship(back_populates="task", order_by="TaskStep.seq",
                                                   cascade="all, delete-orphan")


class TaskStep(Base):
    __tablename__ = "bz_task_steps"
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_id)
    task_id: Mapped[str] = mapped_column(ForeignKey("bz_tasks.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    tool: Mapped[str] = mapped_column(String(120))
    input: Mapped[dict[str, Any]] = mapped_column(default=dict)
    output: Mapped[dict[str, Any]] = mapped_column(default=dict)
    note: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)
    task: Mapped[Task] = relationship(back_populates="steps")


class Approval(Base):
    """What the user saw and approved. Amount, payee and items come from the server-side action, never from model text."""
    __tablename__ = "bz_approvals"
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_id)
    task_id: Mapped[str] = mapped_column(ForeignKey("bz_tasks.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("bz_users.id"), index=True)
    tier: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    payee: Mapped[str] = mapped_column(String(200), default="")
    amount_paise: Mapped[int] = mapped_column(Integer, default=0)
    items: Mapped[list[Any]] = mapped_column(default=list)
    pay_method: Mapped[str] = mapped_column(String(120), default="")
    action: Mapped[dict[str, Any]] = mapped_column(default=dict)  # {"executor":..., "name":..., "args":...}
    tool_use_id: Mapped[str] = mapped_column(String(80), default="")
    conversation_id: Mapped[str] = mapped_column(String(40), default="")
    result: Mapped[dict[str, Any]] = mapped_column(default=dict)
    decision: Mapped[str] = mapped_column(String(12), default="pending")  # pending|approved|rejected|auto
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)
    decided_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)


class Transaction(Base):
    __tablename__ = "bz_transactions"
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("bz_users.id"), index=True)
    task_id: Mapped[str] = mapped_column(String(16), default="")
    kind: Mapped[str] = mapped_column(String(24))  # order|bill|upi|shop_order|recharge
    provider: Mapped[str] = mapped_column(String(80))
    txn_ref: Mapped[str] = mapped_column(String(40), unique=True, default=lambda: "SNT" + uuid.uuid4().hex[:17].upper())
    amount_paise: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(24), default="created")  # created|awaiting_payment|paid|completed|failed
    provider_ref: Mapped[str] = mapped_column(String(80), default="")
    meta: Mapped[dict[str, Any]] = mapped_column(default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now, onupdate=now)


class Reminder(Base):
    __tablename__ = "bz_reminders"
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("bz_users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="reminder")  # reminder|alarm|bill|medicine|birthday|event
    text: Mapped[str] = mapped_column(Text)
    due_at: Mapped[dt.datetime] = mapped_column(DateTime, index=True)
    repeat: Mapped[str] = mapped_column(String(20), default="")  # ""|daily|weekly|monthly|yearly
    channel: Mapped[str] = mapped_column(String(20), default="push")
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    meta: Mapped[dict[str, Any]] = mapped_column(default=dict)


class Memory(Base):
    __tablename__ = "bz_memories"
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("bz_users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="note")  # note|fact|family
    text: Mapped[str] = mapped_column(Text)
    tags: Mapped[list[Any]] = mapped_column(default=list)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class ListItem(Base):
    __tablename__ = "bz_list_items"
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("bz_users.id"), index=True)
    list_name: Mapped[str] = mapped_column(String(60), default="shopping")
    text: Mapped[str] = mapped_column(String(200))
    done: Mapped[bool] = mapped_column(Boolean, default=False)


class SpendEntry(Base):
    __tablename__ = "bz_spend_entries"
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("bz_users.id"), index=True)
    amount_paise: Mapped[int] = mapped_column(Integer)
    direction: Mapped[str] = mapped_column(String(8))  # debit|credit
    merchant: Mapped[str] = mapped_column(String(160), default="")
    category: Mapped[str] = mapped_column(String(40), default="other")
    bank: Mapped[str] = mapped_column(String(60), default="")
    occurred_on: Mapped[dt.date] = mapped_column(index=True)
    raw: Mapped[str] = mapped_column(Text, default="")


# ---------------- Bazar shops (own rails) ----------------

class Shop(Base):
    __tablename__ = "bz_shops"
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_id)
    template_id: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(160))
    owner_phone: Mapped[str] = mapped_column(String(20))
    city: Mapped[str] = mapped_column(String(80), default="")
    pincodes: Mapped[list[Any]] = mapped_column(default=list)
    upi_id: Mapped[str] = mapped_column(String(120))
    languages: Mapped[list[Any]] = mapped_column(default=lambda: ["mr", "hi", "en"])
    aliases: Mapped[list[Any]] = mapped_column(default=list)  # "Ramesh bhau", "Ramesh kirana"
    min_order_paise: Mapped[int] = mapped_column(Integer, default=0)
    delivery_fee_paise: Mapped[int] = mapped_column(Integer, default=0)
    slots: Mapped[list[Any]] = mapped_column(default=list)  # ["09:00-10:00", ...]
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    plan: Mapped[str] = mapped_column(String(20), default="listing_199")
    owner_tenant: Mapped[str] = mapped_column(String(64), default="")      # Santosh user who onboarded it
    merchant_token_hash: Mapped[str] = mapped_column(String(64), default="")  # only the shop can manage orders
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)
    items: Mapped[list["ShopItem"]] = relationship(back_populates="shop", cascade="all, delete-orphan")


class ShopItem(Base):
    __tablename__ = "bz_shop_items"
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_id)
    shop_id: Mapped[str] = mapped_column(ForeignKey("bz_shops.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    aliases: Mapped[list[Any]] = mapped_column(default=list)  # "atta", "gehu ka atta", "कणीक"
    unit: Mapped[str] = mapped_column(String(20), default="pc")  # kg|g|l|ml|pc|pack|session|month|visit
    unit_qty: Mapped[float] = mapped_column(default=1.0)
    price_paise: Mapped[int] = mapped_column(Integer)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    kind: Mapped[str] = mapped_column(String(20), default="product")  # product|service|subscription
    shop: Mapped[Shop] = relationship(back_populates="items")


class ShopOrder(Base):
    __tablename__ = "bz_shop_orders"
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_id)
    shop_id: Mapped[str] = mapped_column(ForeignKey("bz_shops.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("bz_users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="order")  # order|booking|subscription|due_payment
    lines: Mapped[list[Any]] = mapped_column(default=list)
    total_paise: Mapped[int] = mapped_column(Integer, default=0)
    slot: Mapped[str] = mapped_column(String(60), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(24), default="cart")  # cart|placed|accepted|ready|delivered|cancelled
    payment_status: Mapped[str] = mapped_column(String(24), default="unpaid")
    txn_ref: Mapped[str] = mapped_column(String(40), default="")
    notify_status: Mapped[str] = mapped_column(String(200), default="")  # WhatsApp alert to the shop: sent / why not
    conversation_id: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class ShopDue(Base):
    """For bill-collection shops (local ISP, cable LCO, tuition, gym): what each customer owes."""
    __tablename__ = "bz_shop_dues"
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_id)
    shop_id: Mapped[str] = mapped_column(ForeignKey("bz_shops.id"), index=True)
    customer_ref: Mapped[str] = mapped_column(String(60), index=True)  # account id / phone
    customer_phone: Mapped[str] = mapped_column(String(20), default="")
    description: Mapped[str] = mapped_column(String(200), default="")
    amount_paise: Mapped[int] = mapped_column(Integer)
    due_on: Mapped[dt.date | None] = mapped_column(nullable=True)
    paid: Mapped[bool] = mapped_column(Boolean, default=False)


class CustomMcp(Base):
    """A remote MCP server the user added to Santosh (from the MCP directory or by URL)."""
    __tablename__ = "bz_custom_mcp"
    id: Mapped[str] = mapped_column(String(24), primary_key=True)          # "mcp-<hex>", also the pack id
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("bz_users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    url: Mapped[str] = mapped_column(String(500))                          # v0.286 secrets masked (see url_enc)
    url_enc: Mapped[str | None] = mapped_column(Text, nullable=True)       # v0.286 the full address, sealed, when it carries a key
    directory_ref: Mapped[str] = mapped_column(String(160), default="")   # owner/repo from the directory
    description: Mapped[str] = mapped_column(Text, default="")
    caution: Mapped[bool] = mapped_column(Boolean, default=False)
    auth: Mapped[str] = mapped_column(String(10), default="none")         # none | oauth | key
    key_header: Mapped[str] = mapped_column(String(60), default="Authorization")
    status: Mapped[str] = mapped_column(String(20), default="active")     # active | removed
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class KVState(Base):
    """Small server-side state: OAuth client registrations, sign-in states."""
    __tablename__ = "bz_kv"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


# ---------------- wave 2 (P1) skill data ----------------

class Staff(Base):
    __tablename__ = "bz_staff"
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("bz_users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20), default="")
    monthly_salary_paise: Mapped[int] = mapped_column(Integer, default=0)
    paid_leaves_per_month: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Attendance(Base):
    __tablename__ = "bz_attendance"
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_id)
    staff_id: Mapped[str] = mapped_column(ForeignKey("bz_staff.id"), index=True)
    day: Mapped[dt.date] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(String(10))  # present|absent|half


class UdharEntry(Base):
    __tablename__ = "bz_udhar"
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("bz_users.id"), index=True)
    customer: Mapped[str] = mapped_column(String(120), index=True)
    phone: Mapped[str] = mapped_column(String(20), default="")
    amount_paise: Mapped[int] = mapped_column(Integer)  # + given on credit, - received
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class GeneratedDoc(Base):
    __tablename__ = "bz_generated_docs"
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("bz_users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30))  # invoice|quotation|salary_slip|rent_receipt|resume
    number: Mapped[str] = mapped_column(String(40), default="")
    data: Mapped[dict[str, Any]] = mapped_column(default=dict)
    file_name: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


# ---------------- home devices (v0.3) ----------------

class Device(Base):
    """A home device Santosh can reach.

    channel: phone_media (Bluetooth speaker via the phone's media session) | bt_hid (TV paired with the phone as a
    Bluetooth remote, plus DIAL on Wi-Fi) | ir (AC via the phone's IR blaster) | cloud (SmartThings / LG ThinQ /
    Home Connect).
    """
    __tablename__ = "bz_devices"
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("bz_users.id"), index=True)
    pack_id: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(80))
    room: Mapped[str] = mapped_column(String(40), default="")
    kind: Mapped[str] = mapped_column(String(20))            # speaker|tv|ac|fridge|washer|other
    channel: Mapped[str] = mapped_column(String(20))         # phone_media|bt_hid|ir|cloud
    brand: Mapped[str] = mapped_column(String(40), default="")
    protocol: Mapped[str] = mapped_column(String(30), default="")       # IR protocol once confirmed
    provider: Mapped[str] = mapped_column(String(20), default="")       # cloud provider
    external_id: Mapped[str] = mapped_column(String(120), default="")   # cloud device id
    target: Mapped[dict[str, Any]] = mapped_column(default=dict)        # bt address, tv ip, …
    state: Mapped[dict[str, Any]] = mapped_column(default=dict)         # last confirmed state (IR AC) / last alert keys
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class DeviceCommand(Base):
    """A command the phone must carry out (IR, Bluetooth, DIAL). The phone reports back; IR AC state is saved only
    after the phone confirms the signal was sent."""
    __tablename__ = "bz_device_commands"
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("bz_users.id"), index=True)
    device_id: Mapped[str] = mapped_column(String(16), index=True)
    task_id: Mapped[str] = mapped_column(String(16), default="")
    channel: Mapped[str] = mapped_column(String(20))
    payload: Mapped[dict[str, Any]] = mapped_column(default=dict)
    new_state: Mapped[dict[str, Any]] = mapped_column(default=dict)
    status: Mapped[str] = mapped_column(String(12), default="sent")  # sent|done|failed
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


# ---------------- e-commerce (v0.4) ----------------

class CommerceOffer(Base):
    """A product offer returned by search, kept so later calls can refer to it by id (price is re-checked at quote)."""
    __tablename__ = "bz_commerce_offers"
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(20))           # bazar|ondc|shopify|flipkart
    data: Mapped[dict[str, Any]] = mapped_column(default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class CommerceCart(Base):
    __tablename__ = "bz_commerce_carts"
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(20))
    seller_key: Mapped[str] = mapped_column(String(200))      # one seller per cart
    seller_name: Mapped[str] = mapped_column(String(200), default="")
    lines: Mapped[list[Any]] = mapped_column(default=list)    # [{offer_id, ref, name, qty, unit_price_paise}]
    meta: Mapped[dict[str, Any]] = mapped_column(default=dict)
    status: Mapped[str] = mapped_column(String(16), default="open")   # open|quoted|ordered|abandoned
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class CommerceQuote(Base):
    """All-in price the user approves. Short-lived; the order is placed only against an unexpired quote."""
    __tablename__ = "bz_commerce_quotes"
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    cart_id: Mapped[str] = mapped_column(String(16), index=True)
    total_paise: Mapped[int] = mapped_column(Integer)
    breakup: Mapped[list[Any]] = mapped_column(default=list)  # [{title, kind, amount_paise}]
    disclosures: Mapped[dict[str, Any]] = mapped_column(default=dict)  # seller, returns, delivery, origin…
    address: Mapped[dict[str, Any]] = mapped_column(default=dict)
    payment_mode: Mapped[str] = mapped_column(String(20), default="upi_intent")  # upi_intent|handoff
    quote_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(16), default="open")   # open|confirmed|expired|superseded
    meta: Mapped[dict[str, Any]] = mapped_column(default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class CommerceOrder(Base):
    __tablename__ = "bz_commerce_orders"
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(20))
    seller_name: Mapped[str] = mapped_column(String(200), default="")
    cart_id: Mapped[str] = mapped_column(String(16), default="")
    quote_id: Mapped[str] = mapped_column(String(16), default="")
    external_id: Mapped[str] = mapped_column(String(120), default="")
    lines: Mapped[list[Any]] = mapped_column(default=list)
    total_paise: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(24), default="payment_pending")
    # payment_pending|placed|accepted|packed|shipped|out_for_delivery|delivered|cancelled|return_requested|returned|failed
    payment_status: Mapped[str] = mapped_column(String(16), default="unpaid")
    txn_ref: Mapped[str] = mapped_column(String(40), default="")
    idempotency_key: Mapped[str] = mapped_column(String(80), default="", index=True)
    history: Mapped[list[Any]] = mapped_column(default=list)  # [{at, status, note}]
    meta: Mapped[dict[str, Any]] = mapped_column(default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class ConsentRecord(Base):
    """Who approved what, for how much, through which surface (AP2-style cart mandate, audit trail)."""
    __tablename__ = "bz_consent_records"
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    quote_id: Mapped[str] = mapped_column(String(16))
    order_id: Mapped[str] = mapped_column(String(16), default="")
    surface: Mapped[str] = mapped_column(String(30))          # santosh_card|mcp_elicitation|mcp_confirm_code
    client_id: Mapped[str] = mapped_column(String(80), default="")
    statement: Mapped[str] = mapped_column(Text)
    amount_paise: Mapped[int] = mapped_column(Integer)
    payee: Mapped[str] = mapped_column(String(200))
    quote_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class OndcMessage(Base):
    """Async ONDC callbacks (on_search, on_select, …) received from seller apps."""
    __tablename__ = "bz_ondc_messages"
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_id)
    transaction_id: Mapped[str] = mapped_column(String(64), index=True)
    message_id: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(20))
    bpp_id: Mapped[str] = mapped_column(String(200), default="")
    payload: Mapped[dict[str, Any]] = mapped_column(default=dict)
    received_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class McpToken(Base):
    """Per-user bearer tokens for the Santosh Commerce MCP server (stored as SHA-256)."""
    __tablename__ = "bz_mcp_tokens"
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    label: Mapped[str] = mapped_column(String(80), default="")
    scopes: Mapped[list[Any]] = mapped_column(default=lambda: ["commerce:read", "commerce:order"])
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class RunnerSpec(Base):
    """v0.154 a directory MCP server Hoola runs on the MCP runner box for this user (one-tap connect)."""
    __tablename__ = "bz_runner_specs"
    id: Mapped[str] = mapped_column(String(24), primary_key=True)          # the CustomMcp row id
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    iid: Mapped[str] = mapped_column(String(24), unique=True)               # instance id on the runner
    kind: Mapped[str] = mapped_column(String(10))                           # npm | pypi | docker
    package: Mapped[str] = mapped_column(String(220))
    version: Mapped[str] = mapped_column(String(40), default="")
    env_enc: Mapped[str] = mapped_column(Text, default="")                  # her keys for it, sealed (vault)
    token_enc: Mapped[str] = mapped_column(Text, default="")                # the instance bearer token, sealed
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class PackageCheck(Base):
    """v0.154 safety check of a package before its first run on the runner (shared by every user; 7 days)."""
    __tablename__ = "bz_package_checks"
    key: Mapped[str] = mapped_column(String(240), primary_key=True)        # kind:package
    verdict: Mapped[str] = mapped_column(String(10))                        # ok | caution | block
    reasons: Mapped[list[Any]] = mapped_column(default=list)
    facts: Mapped[dict[str, Any]] = mapped_column(default=dict)
    checked_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


# ---------------- engine / session (shared with Santosh core) ----------------

def init_tables(engine) -> None:
    Base.metadata.create_all(engine)


def session_factory() -> Session:
    from .. import db as core
    if core._Session is None:
        core.init_db()
    return core._Session()


def get_session():
    """FastAPI dependency: one bazar session per request, committed on success."""
    s = session_factory()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def init_engine(url: str | None = None):  # compatibility with MVP code paths
    from .. import db as core
    if core._Session is None:
        core.init_db()
    return core._engine if hasattr(core, "_engine") else None


__all__ = [n for n in dir() if not n.startswith("_")] + ["select"]
