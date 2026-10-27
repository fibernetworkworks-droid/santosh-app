"""Tables of the Podcast Sahayak (all prefixed podcast_). JSON kept in Text columns (pattern of banquet / interior)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now


class PodcastSettings(Base):
    __tablename__ = "podcast_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    show: Mapped[str] = mapped_column(String(160), default="")
    host: Mapped[str] = mapped_column(String(120), default="")           # her name as the host (podcast:person role host)
    author: Mapped[str] = mapped_column(String(160), default="")         # itunes:author (show / company name)
    description: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(10), default="hi")      # RSS <language>
    category: Mapped[str] = mapped_column(String(80), default="")        # Apple category, e.g. "Business"
    subcategory: Mapped[str] = mapped_column(String(80), default="")
    explicit: Mapped[bool] = mapped_column(Boolean, default=False)
    show_type: Mapped[str] = mapped_column(String(10), default="episodic")   # episodic | serial
    owner_email: Mapped[str] = mapped_column(String(160), default="")    # itunes:owner (PUBLIC in the feed: her choice)
    website: Mapped[str] = mapped_column(String(300), default="")
    copyright: Mapped[str] = mapped_column(String(200), default="")
    artwork: Mapped[str] = mapped_column(Text, default="")               # {path, w, h, fmt, sha}
    feed_on: Mapped[bool] = mapped_column(Boolean, default=False)
    feed_token: Mapped[str] = mapped_column(String(64), default="")
    feed_url: Mapped[str] = mapped_column(String(400), default="")       # her host's feed URL if she hosts elsewhere (for podcast:guid)
    host_platform: Mapped[str] = mapped_column(String(40), default="")   # spotify_creators | buzzsprout | hubhopper | ... | hoola
    gstin: Mapped[str] = mapped_column(String(15), default="")
    upi_id: Mapped[str] = mapped_column(String(80), default="")
    business: Mapped[str] = mapped_column(String(160), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    target_lufs: Mapped[float] = mapped_column(Float, default=-16.0)
    record_minutes: Mapped[int] = mapped_column(Integer, default=60)     # usual length of a recording slot
    gap_minutes: Mapped[int] = mapped_column(Integer, default=30)        # free time she wants between two recordings
    release_terms: Mapped[str] = mapped_column(Text, default="")         # her own release wording (blank = starter text)
    morning_time: Mapped[str] = mapped_column(String(5), default="09:00")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    rules: Mapped[str] = mapped_column(Text, default="")
    ep_seq: Mapped[int] = mapped_column(Integer, default=0)
    guest_seq: Mapped[int] = mapped_column(Integer, default=0)
    sp_seq: Mapped[int] = mapped_column(Integer, default=0)
    mu_seq: Mapped[int] = mapped_column(Integer, default=0)
    inv_seq: Mapped[int] = mapped_column(Integer, default=0)


class PodcastGuest(Base):
    __tablename__ = "podcast_guests"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pg"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    name: Mapped[str] = mapped_column(String(160), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(160), default="")
    bio: Mapped[str] = mapped_column(Text, default="")                   # her words / the guest's own bio (data)
    links: Mapped[str] = mapped_column(Text, default="[]")
    topics: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(12), default="idea")      # idea | invited | confirmed | recorded | declined
    release: Mapped[str] = mapped_column(Text, default="{}")             # {status none|requested|signed|refused|revoked, how, at, ...}
    no_messages: Mapped[bool] = mapped_column(Boolean, default=False)
    forgotten: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PodcastEpisode(Base):
    __tablename__ = "podcast_episodes"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pe"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")          # EP-001
    title: Mapped[str] = mapped_column(String(300), default="")
    season: Mapped[int | None] = mapped_column(Integer, nullable=True)
    episode_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kind: Mapped[str] = mapped_column(String(10), default="full")        # full | trailer | bonus
    status: Mapped[str] = mapped_column(String(12), default="idea")      # idea | booked | recorded | edited | ready | published
    topics: Mapped[str] = mapped_column(Text, default="[]")
    guests: Mapped[str] = mapped_column(Text, default="[]")              # guest ids
    record_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    record_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    record_place: Mapped[str] = mapped_column(String(200), default="")   # studio / online link (her words)
    publish_on: Mapped[str] = mapped_column(String(10), default="")      # her planned date YYYY-MM-DD
    run_sheet: Mapped[str] = mapped_column(Text, default="[]")
    audio: Mapped[str] = mapped_column(Text, default="{}")               # {path, name, mime, size, duration, sha, normalized_of}
    loudness: Mapped[str] = mapped_column(Text, default="{}")
    transcript: Mapped[str] = mapped_column(Text, default="[]")          # [{start, end, text, speaker}]
    transcript_source: Mapped[str] = mapped_column(String(16), default="")   # whisper | gemini | lekhak | her_file
    notes: Mapped[str] = mapped_column(Text, default="{}")               # show notes {summary, points, links, chapters, quotes, ...}
    music: Mapped[str] = mapped_column(Text, default="[]")               # licence ids used in this episode
    ai_parts: Mapped[str] = mapped_column(Text, default="[]")            # AI-made parts (voice, music, artwork, intro ...) -> label
    explicit: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    news: Mapped[bool] = mapped_column(Boolean, default=False)           # news & current affairs content (IT Rules 2021 Part III note)
    published: Mapped[str] = mapped_column(Text, default="{}")           # {at, feed, platforms {name: url}}
    pub_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    log: Mapped[str] = mapped_column(Text, default="[]")
    conv: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PodcastMusic(Base):
    """The music / sound licence register: every track in an episode must be cleared here."""
    __tablename__ = "podcast_music"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    artist: Mapped[str] = mapped_column(String(200), default="")
    source: Mapped[str] = mapped_column(String(300), default="")         # where it came from (library / site / composer)
    licence: Mapped[str] = mapped_column(String(20), default="unknown")  # own | commissioned | cc0 | cc_by | royalty_free | paid | unknown
    proof: Mapped[str] = mapped_column(Text, default="")                 # licence text / receipt file name (her words)
    attribution: Mapped[str] = mapped_column(Text, default="")
    valid_until: Mapped[str] = mapped_column(String(10), default="")
    commercial_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")


class PodcastSponsor(Base):
    __tablename__ = "podcast_sponsors"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ps"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    brand: Mapped[str] = mapped_column(String(160), default="")
    contact: Mapped[str] = mapped_column(String(160), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(160), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)   # HER agreed fee before GST (never guessed)
    deliverables: Mapped[str] = mapped_column(Text, default="")          # her words: "2 mid-roll + 1 post-roll"
    status: Mapped[str] = mapped_column(String(12), default="lead")      # lead | agreed | live | done | lost
    paid: Mapped[str] = mapped_column(Text, default="[]")                # [{amount, at, ref, tds}]
    invoices: Mapped[str] = mapped_column(Text, default="[]")
    notes: Mapped[str] = mapped_column(Text, default="")


class PodcastRead(Base):
    """One sponsor read in one episode (pre / mid / post roll) with its script."""
    __tablename__ = "podcast_reads"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    episode_id: Mapped[str] = mapped_column(String(40), index=True)
    sponsor_id: Mapped[str] = mapped_column(String(40), default="")
    slot: Mapped[str] = mapped_column(String(6), default="mid")          # pre | mid | post
    script: Mapped[str] = mapped_column(Text, default="")
    brand_ok: Mapped[bool] = mapped_column(Boolean, default=False)       # the brand approved this script (her word)


class PodcastStat(Base):
    """Numbers she pasted / exported from Spotify for Creators, Apple Podcasts Connect, YouTube Studio ... (never scraped)."""
    __tablename__ = "podcast_stats"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pt"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    episode_id: Mapped[str] = mapped_column(String(40), default="")
    label: Mapped[str] = mapped_column(String(300), default="")         # episode title as it was in her export
    platform: Mapped[str] = mapped_column(String(20), default="")
    day: Mapped[str] = mapped_column(String(10), default="")
    plays: Mapped[int | None] = mapped_column(Integer, nullable=True)
    listeners: Mapped[int | None] = mapped_column(Integer, nullable=True)
    followers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    consumption: Mapped[float | None] = mapped_column(Float, nullable=True)  # average % listened
    key: Mapped[str] = mapped_column(String(64), index=True, default="")


class PodcastCard(Base):
    __tablename__ = "podcast_cards"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(16), default="")            # publish | invite | release | sponsor | invoice | message
    ref: Mapped[str] = mapped_column(String(40), default="")             # episode / guest / sponsor id
    show: Mapped[str] = mapped_column(Text, default="{}")
    hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(10), default="waiting")   # waiting | approved | rejected | stale
    asked_by: Mapped[str] = mapped_column(String(80), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(Text, default="{}")
    conv: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PodcastAlert(Base):
    __tablename__ = "podcast_alerts"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
